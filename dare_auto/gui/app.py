"""Janela principal: barra lateral, páginas, barra de status e comunicação com o motor."""

import logging
import os
import queue
import socket
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .. import __data_versao__, __version__, armazenamento, config, limpeza, logger, motor, navegador, preferencias
from ..modelos import DadosDare
from . import tema as T
from .widgets import Toast

log = logging.getLogger("dare.app")

TITULO = "DARE Automação"
PORTA_INSTANCIA = 47391  # impede abrir o programa duas vezes (as duas cópias brigariam pelo navegador)


class FilaLog(logging.Handler):
    """Leva as mensagens de log (de qualquer thread) para a janela, sem tocar no Tk fora da thread principal."""

    def __init__(self, fila: queue.Queue):
        super().__init__(level=logging.INFO)
        self.fila = fila

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.fila.put_nowait(("log", record))
        except Exception:  # noqa: BLE001
            pass


class Pagina(ttk.Frame):
    titulo = ""
    icone = ""

    def __init__(self, app: "Aplicacao"):
        super().__init__(app.conteudo, padding=(24, 20, 24, 14))
        self.app = app

    def ao_mostrar(self) -> None:
        """Chamado sempre que a página fica visível (atualize os dados aqui)."""


class ItemNavegacao(tk.Frame):
    def __init__(self, master, icone: str, texto: str, comando):
        super().__init__(master, bg=T.LATERAL, cursor="hand2")
        self.comando, self.ativo = comando, False
        self.barra = tk.Frame(self, bg=T.LATERAL, width=4)
        self.barra.pack(side="left", fill="y")
        self.icone = tk.Label(self, text=icone, bg=T.LATERAL, fg=T.LATERAL_TEXTO, font=T.F["icone"], width=2)
        self.icone.pack(side="left", padx=(14, 6), pady=9)
        self.texto = tk.Label(self, text=texto, bg=T.LATERAL, fg=T.LATERAL_TEXTO, font=T.F["nav"], anchor="w")
        self.texto.pack(side="left", fill="x", expand=True)
        self.contador = tk.Label(self, text="", bg=T.LATERAL, fg="#FFFFFF", font=T.F["pequena"], padx=7)
        self.contador.pack(side="right", padx=12)
        for w in (self, self.icone, self.texto, self.contador):
            w.bind("<Button-1>", lambda e: self.comando())
            w.bind("<Enter>", lambda e: self._pintar(hover=True))
            w.bind("<Leave>", lambda e: self._pintar())

    def definir_ativo(self, ativo: bool) -> None:
        self.ativo = ativo
        self._pintar()

    def definir_contador(self, texto: str, cor: str = T.PRIMARIA) -> None:
        self.contador.configure(text=texto, bg=cor if texto else self.cget("bg"))

    def _pintar(self, hover: bool = False) -> None:
        fundo = T.LATERAL_ITEM_ATIVO if (self.ativo or hover) else T.LATERAL
        frente = "#FFFFFF" if self.ativo else T.LATERAL_TEXTO
        for w in (self, self.icone, self.texto):
            w.configure(bg=fundo)
        self.icone.configure(fg=T.LATERAL_DESTAQUE if self.ativo else frente)
        self.texto.configure(fg=frente, font=T.F["negrito"] if self.ativo else T.F["nav"])
        self.barra.configure(bg=T.LATERAL_DESTAQUE if self.ativo else fundo)
        if not self.contador.cget("text"):
            self.contador.configure(bg=fundo)


class Aplicacao(tk.Tk):
    def __init__(self):
        super().__init__()
        T.aplicar(self)
        self.title(f"{TITULO} — versão {__version__}")
        self.minsize(1040, 660)
        self._posicionar()
        self._definir_icone()

        self.pref = preferencias.carregar()
        preferencias.aplicar(self.pref)
        self.lotes: list[DadosDare] = []
        self.executando = False
        self.controle = motor.Controle()
        self.fila: queue.Queue = queue.Queue()
        self.ouvintes_log: list = []  # funções(record) que querem ver o log (página Execução)
        self.navegador_aberto = False
        self.toast = Toast(self)

        self._handler_log = FilaLog(self.fila)
        logging.getLogger("dare").addHandler(self._handler_log)

        self._montar()
        from .paginas import PAGINAS  # import aqui: as páginas usam a classe Pagina deste módulo
        self.paginas: dict[str, Pagina] = {}
        for chave, classe in PAGINAS:
            self.paginas[chave] = classe(self)
            item = ItemNavegacao(self.lateral_itens, classe.icone, classe.titulo,
                                 lambda c=chave: self.mostrar(c))
            item.pack(fill="x")
            self.itens_nav[chave] = item
        self.pagina_atual = ""
        self.mostrar("inicio")

        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.bind_all("<Control-n>", lambda e: self.ir_para_novo_lancamento())
        self.bind_all("<Control-i>", lambda e: self.paginas["lancamentos"].importar_planilha())
        self.bind_all("<F5>", lambda e: self.atualizar_pagina())
        self.after(100, self._processar_fila)
        self.after(400, self._ao_iniciar)
        self.after(1500, self._atualizar_status_periodico)

    # ---- Estrutura ------------------------------------------------------------------------

    def _posicionar(self) -> None:
        largura = min(1320, int(self.winfo_screenwidth() * 0.9))
        altura = min(860, int(self.winfo_screenheight() * 0.88))
        x = (self.winfo_screenwidth() - largura) // 2
        y = max(0, (self.winfo_screenheight() - altura) // 2 - 20)
        self.geometry(f"{largura}x{altura}+{x}+{y}")

    def _definir_icone(self) -> None:
        pasta = Path(__file__).resolve().parent / "recursos"
        try:
            if os.name == "nt" and (pasta / "icone.ico").exists():
                self.iconbitmap(default=str(pasta / "icone.ico"))
            elif (pasta / "icone.png").exists():
                self._icone = tk.PhotoImage(file=str(pasta / "icone.png"))
                self.iconphoto(True, self._icone)
        except tk.TclError:
            pass

    def _montar(self) -> None:
        # Barra lateral
        self.lateral = tk.Frame(self, bg=T.LATERAL, width=226)
        self.lateral.pack(side="left", fill="y")
        self.lateral.pack_propagate(False)
        marca = tk.Frame(self.lateral, bg=T.LATERAL)
        marca.pack(fill="x", padx=14, pady=(20, 18))
        arq_logo = Path(__file__).resolve().parent / "recursos" / "icone_64.png"
        try:
            self._logo = tk.PhotoImage(file=str(arq_logo)).subsample(2)
            tk.Label(marca, image=self._logo, bg=T.LATERAL).pack(side="left")
        except tk.TclError:
            logo = tk.Canvas(marca, width=34, height=34, bg=T.LATERAL, highlightthickness=0)
            logo.create_rectangle(2, 2, 32, 32, fill=T.PRIMARIA, outline=T.PRIMARIA)
            logo.create_text(17, 17, text="D", fill="#FFFFFF", font=(T.FAMILIA, 15, "bold"))
            logo.pack(side="left")
        textos = tk.Frame(marca, bg=T.LATERAL)
        textos.pack(side="left", padx=(8, 0))
        tk.Label(textos, text="DARE Automação", bg=T.LATERAL, fg="#FFFFFF", font=T.F["marca"]).pack(anchor="w")
        tk.Label(textos, text="DARE → PDF → SEI", bg=T.LATERAL, fg=T.LATERAL_TEXTO_3,
                 font=T.F["pequena"]).pack(anchor="w")
        tk.Frame(self.lateral, bg="#22355A", height=1).pack(fill="x", padx=16, pady=(0, 10))
        self.lateral_itens = tk.Frame(self.lateral, bg=T.LATERAL)
        self.lateral_itens.pack(fill="x")
        self.itens_nav: dict[str, ItemNavegacao] = {}

        rodape = tk.Frame(self.lateral, bg=T.LATERAL)
        rodape.pack(side="bottom", fill="x", padx=18, pady=16)
        self.lbl_navegador = tk.Label(rodape, text="● Navegador fechado", bg=T.LATERAL, fg=T.LATERAL_TEXTO_3,
                                      font=T.F["pequena"], anchor="w", cursor="hand2")
        self.lbl_navegador.pack(fill="x", pady=(0, 8))
        self.lbl_navegador.bind("<Button-1>", lambda e: self.abrir_navegador())
        versao = tk.Label(rodape, text=f"Versão {__version__}", bg="#1C335E", fg="#FFFFFF",
                          font=T.F["pequena"], padx=8, pady=2)
        versao.pack(anchor="w")
        tk.Label(rodape, text=f"Atualizada em {__data_versao__}", bg=T.LATERAL, fg=T.LATERAL_TEXTO_3,
                 font=T.F["pequena"]).pack(anchor="w", pady=(4, 0))

        # Área principal
        direita = tk.Frame(self, bg=T.FUNDO)
        direita.pack(side="left", fill="both", expand=True)
        self.status = tk.Frame(direita, bg=T.SUPERFICIE, highlightthickness=1, highlightbackground=T.BORDA)
        self.status.pack(side="bottom", fill="x")
        self.status_esq = tk.Label(self.status, text="", bg=T.SUPERFICIE, fg=T.TEXTO_2, font=T.F["pequena"],
                                   anchor="w", padx=14, pady=5)
        self.status_esq.pack(side="left", fill="x", expand=True)
        self.status_dir = tk.Label(self.status, text=f"v{__version__}", bg=T.SUPERFICIE, fg=T.TEXTO_3,
                                   font=T.F["pequena"], padx=14)
        self.status_dir.pack(side="right")
        self.conteudo = tk.Frame(direita, bg=T.FUNDO)
        self.conteudo.pack(fill="both", expand=True)

    # ---- Navegação ------------------------------------------------------------------------

    def mostrar(self, chave: str) -> None:
        if self.pagina_atual == chave:
            self.paginas[chave].ao_mostrar()
            return
        if self.pagina_atual:
            self.paginas[self.pagina_atual].pack_forget()
            self.itens_nav[self.pagina_atual].definir_ativo(False)
        self.pagina_atual = chave
        self.itens_nav[chave].definir_ativo(True)
        pagina = self.paginas[chave]
        pagina.pack(fill="both", expand=True)
        pagina.ao_mostrar()

    def atualizar_pagina(self) -> None:
        self.paginas[self.pagina_atual].ao_mostrar()

    def ir_para_novo_lancamento(self) -> None:
        self.mostrar("lancamentos")
        self.paginas["lancamentos"].novo()

    def atualizar_navegacao(self) -> None:
        n = len(self.lotes)
        self.itens_nav["lancamentos"].definir_contador(str(n) if n else "")
        if self.executando:
            self.itens_nav["execucao"].definir_contador("em andamento", T.SUCESSO)
        else:
            self.itens_nav["execucao"].definir_contador("")

    # ---- Lançamentos (lista de trabalho) --------------------------------------------------

    def lotes_alterados(self) -> None:
        """Guarda a lista (não perde o que foi digitado) e atualiza contadores."""
        try:
            if self.lotes:
                armazenamento.salvar_lote(self.lotes)
            else:
                armazenamento.limpar_lote()
        except OSError:
            log.warning("Não consegui guardar a lista de lançamentos.", exc_info=True)
        self.atualizar_navegacao()

    def iniciar_execucao(self, lotes: list[DadosDare]) -> None:
        if self.executando or not lotes:
            return
        self.executando = True
        self.controle = motor.Controle()
        self.atualizar_navegacao()
        self.mostrar("execucao")
        self.paginas["execucao"].preparar(lotes)
        motor.iniciar_em_thread(list(lotes), self._emitir, self.controle)
        self._atualizar_status()

    def _emitir(self, tipo: str, dados: dict) -> None:
        """Chamado pela thread do motor: só enfileira (o Tk é atualizado na thread principal)."""
        self.fila.put((tipo, dados))

    def _processar_fila(self) -> None:
        registros = []
        try:
            for _ in range(400):
                tipo, dados = self.fila.get_nowait()
                if tipo == "log":
                    registros.append(dados)
                    continue
                if tipo == "fim":
                    self.executando = False
                    self.lotes = list(dados.get("pendentes") or [])
                    self.atualizar_navegacao()
                    self._atualizar_status()
                self.paginas["execucao"].evento(tipo, dados)
        except queue.Empty:
            pass
        if registros:
            for ouvinte in self.ouvintes_log:
                ouvinte(registros)
        self.after(80 if self.executando else 150, self._processar_fila)

    # ---- Navegador ------------------------------------------------------------------------

    def abrir_navegador(self) -> None:
        if navegador.chrome_debug_ativo():
            self.toast.mostrar("O navegador do programa já está aberto.", "info")
            return
        exe = navegador.localizar_chrome()
        if not exe:
            messagebox.showerror(
                TITULO, "Não encontrei o Google Chrome nem o Microsoft Edge neste computador.\n\n"
                        "Instale o Google Chrome (google.com/chrome) e tente de novo.", parent=self)
            return
        self.toast.mostrar(f"Abrindo o {navegador.nome_navegador(exe)} com o SEI e o DARE...", "info")
        self.lbl_navegador.configure(text="● Abrindo navegador...", fg="#FCD34D")
        motor.abrir_navegador_em_thread(lambda ok: self.after(0, self._navegador_aberto, ok))

    def _navegador_aberto(self, ok: bool) -> None:
        self._atualizar_status()
        if ok:
            self.toast.mostrar("Navegador aberto. Entre com a sua conta no DARE e no SEI.")
        else:
            messagebox.showwarning(
                TITULO, "Não consegui abrir o navegador em modo depuração.\n\n"
                        "Feche todas as janelas do navegador do programa e tente de novo. "
                        "Os detalhes estão no log.", parent=self)

    # ---- Status ---------------------------------------------------------------------------

    def _atualizar_status(self) -> None:
        self.navegador_aberto = navegador.chrome_debug_ativo(timeout=0.2)
        if self.navegador_aberto:
            self.lbl_navegador.configure(text="● Navegador aberto", fg="#4ADE80")
        else:
            self.lbl_navegador.configure(text="● Navegador fechado · abrir", fg=T.LATERAL_TEXTO_3)
        qtd, tam = limpeza.tamanho_pasta()
        estado = "processando lançamentos" if self.executando else "pronto"
        pasta = str(config.PASTA_PDF)
        if len(pasta) > 70:
            pasta = "…" + pasta[-68:]
        self.status_esq.configure(
            text=f"{estado.capitalize()}    ·    "
                 f"PDFs: {qtd} ({limpeza.formatar_bytes(tam)})    ·    Pasta: {pasta}")
        self.status_dir.configure(text=f"DARE Automação v{__version__}")

    def _atualizar_status_periodico(self) -> None:
        self._atualizar_status()
        self.after(5000, self._atualizar_status_periodico)

    # ---- Início e fim ---------------------------------------------------------------------

    def _ao_iniciar(self) -> None:
        pendentes = armazenamento.carregar_lote()
        if pendentes:
            self.lotes = pendentes
            self.atualizar_navegacao()
            self.paginas["inicio"].ao_mostrar()
            self.toast.mostrar(f"{len(pendentes)} lançamento(s) pendente(s) recuperado(s) da última vez.", "info", 5000)
        if self.pref.limpeza_automatica:
            threading.Thread(target=self._limpeza_automatica, daemon=True).start()
        if self.pref.abrir_navegador_ao_iniciar and not navegador.chrome_debug_ativo():
            if navegador.localizar_chrome():
                self.lbl_navegador.configure(text="● Abrindo navegador...", fg="#FCD34D")
                motor.abrir_navegador_em_thread(lambda ok: self.after(0, self._atualizar_status))
        self._atualizar_status()

    def _limpeza_automatica(self) -> None:
        try:
            r = limpeza.limpeza_automatica(self.pref.limpeza_dias, self.pref.usar_lixeira,
                                           self.pref.proteger_nao_anexados)
        except Exception:  # noqa: BLE001
            log.exception("Falha na limpeza automática")
            return
        if r.apagados:
            self.pref.ultima_limpeza = datetime.now().strftime("%d/%m/%Y %H:%M")
            preferencias.salvar(self.pref)
            texto = (f"Limpeza automática: {r.apagados} PDF(s) com mais de {self.pref.limpeza_dias} dias "
                     f"{'enviados para a Lixeira' if r.para_lixeira else 'apagados'} "
                     f"({limpeza.formatar_bytes(r.bytes_liberados)}).")
            self.after(0, lambda: (self.toast.mostrar(texto, "info", 6000), self._atualizar_status()))

    def fechar(self) -> None:
        if self.executando and not messagebox.askyesno(
            TITULO, "Há lançamentos sendo processados agora.\n\n"
                    "Se fechar, o lançamento atual pode ficar pela metade. Os que não foram concluídos "
                    "ficam guardados como pendentes.\n\nFechar mesmo assim?", icon="warning", parent=self):
            return
        logging.getLogger("dare").removeHandler(self._handler_log)
        log.info("Aplicativo encerrado.")
        self.destroy()


def _ja_aberto() -> socket.socket | None:
    """Reserva uma porta local; se não conseguir, outra cópia do programa já está aberta."""
    trava = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            trava.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", 0x4), 1)
        trava.bind(("127.0.0.1", PORTA_INSTANCIA))
        return trava
    except OSError:
        trava.close()
        return None


def _ajustar_dpi() -> None:
    """Textos nítidos em telas com escala (125%, 150%...) no Windows."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass
    try:  # agrupa as janelas no ícone do programa na barra de tarefas
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DARE.Automacao")
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    logger.configurar(console=False)
    log.info("Aplicativo iniciado (versão %s, Python %s%s).", __version__, sys.version.split()[0],
             ", executável" if config.EMPACOTADO else "")
    trava = _ja_aberto()
    if trava is None:
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showinfo(TITULO, "O DARE Automação já está aberto.\n\nProcure a janela na barra de tarefas.")
        raiz.destroy()
        return
    _ajustar_dpi()
    try:
        app = Aplicacao()
        app.mainloop()
    except Exception:  # noqa: BLE001 - erro inesperado: mostra algo útil em vez de sumir
        log.exception("Erro inesperado no aplicativo")
        try:
            messagebox.showerror(TITULO, "Ocorreu um erro inesperado e o programa precisa fechar.\n\n"
                                         f"Os detalhes estão em:\n{config.ARQ_LOG}")
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        trava.close()
