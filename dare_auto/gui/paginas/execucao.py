"""Página Execução: acompanha o processamento lote a lote, com etapas, tempos e registro."""

import logging
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ... import config, utils
from ...motor import ETAPAS
from .. import tema as T
from ..app import Pagina
from ..widgets import Banner, CabecalhoPagina, Card, Etapas, Tabela, abrir_no_sistema, formatar_duracao

ROTULOS_CURTOS = {
    "preparo": "Preparar", "dare_1": "Órgão", "dare_2": "Receita", "dare_3": "CPF", "dare_4": "Ref./valor",
    "dare_5": "PDF", "retorno": "Voltar", "sei_1": "Processo", "sei_2": "Incluir", "sei_3": "Doc. externo",
    "sei_4": "Anexar",
}


class PaginaExecucao(Pagina):
    titulo = "Execução"
    icone = "▶"

    def __init__(self, app):
        super().__init__(app)
        self.total = 0
        self.inicio = 0.0
        self.tempos: list[float] = []
        self.sucessos = self.erros = 0
        self.atual = 0
        self.rodou = False
        self.resultados_pdf: dict[str, str] = {}
        self._tique = None

        self.cab = CabecalhoPagina(self, "Execução", "Nenhum processamento em andamento.")
        self.cab.pack(fill="x")
        self.btn_parar = ttk.Button(self.cab.acoes, text="■  Parar após o lançamento atual",
                                    style="PerigoContorno.TButton", command=self.parar)
        self.btn_parar.pack(side="left", padx=(0, 8))
        ttk.Button(self.cab.acoes, text="Abrir pasta dos PDFs",
                   command=lambda: abrir_no_sistema(self._pasta_pdf())).pack(side="left")

        self.avisos = ttk.Frame(self)
        self.avisos.pack(fill="x")

        # Vazio
        self.vazio = Card(self, padding=28)
        tk.Label(self.vazio.corpo, text="▶", bg=T.SUPERFICIE, fg=T.PRIMARIA_CLARA, font=(T.FAMILIA, 40)).pack()
        ttk.Label(self.vazio.corpo, text="Nada sendo processado agora", style="H2.Card.TLabel").pack(pady=(4, 2))
        ttk.Label(self.vazio.corpo, text="Monte a lista em Lançamentos e clique em “Iniciar processamento”.\n"
                  "O andamento de cada DARE aparece aqui.", style="Muted.Card.TLabel", justify="center").pack()
        ttk.Button(self.vazio.corpo, text="Ir para Lançamentos", style="Primario.TButton",
                   command=lambda: app.mostrar("lancamentos")).pack(pady=(14, 0))

        # Andamento
        self.painel = ttk.Frame(self)
        prog = Card(self.painel)
        prog.pack(fill="x")
        topo = tk.Frame(prog.corpo, bg=T.SUPERFICIE)
        topo.pack(fill="x")
        esquerda = tk.Frame(topo, bg=T.SUPERFICIE)
        esquerda.pack(side="left", fill="x", expand=True)
        self.lbl_lote = tk.Label(esquerda, text="", bg=T.SUPERFICIE, fg=T.TEXTO, font=T.F["kpi"], anchor="w")
        self.lbl_lote.pack(anchor="w")
        self.lbl_detalhe = ttk.Label(esquerda, text="", style="Muted.Card.TLabel")
        self.lbl_detalhe.pack(anchor="w")
        numeros = tk.Frame(topo, bg=T.SUPERFICIE)
        numeros.pack(side="right")
        self.n_ok = self._numero(numeros, "Concluídos", T.SUCESSO)
        self.n_erro = self._numero(numeros, "Com erro", T.ERRO)
        self.n_decorrido = self._numero(numeros, "Decorrido", T.TEXTO)
        self.n_restante = self._numero(numeros, "Restante (estim.)", T.TEXTO)
        self.n_media = self._numero(numeros, "Média por lote", T.TEXTO)
        self.barra = ttk.Progressbar(prog.corpo, mode="determinate", maximum=100)
        self.barra.pack(fill="x", pady=(14, 4))
        self.lbl_etapa = ttk.Label(prog.corpo, text="", style="Dica.Card.TLabel")
        self.lbl_etapa.pack(anchor="w", pady=(6, 0))
        self.etapas = Etapas(prog.corpo, [(c, ROTULOS_CURTOS[c]) for c, _, _ in ETAPAS])
        self.etapas.pack(fill="x", pady=(4, 0))

        meio = ttk.Frame(self.painel)
        meio.pack(fill="both", expand=True, pady=(14, 0))
        meio.columnconfigure(0, weight=3, uniform="m")
        meio.columnconfigure(1, weight=2, uniform="m")
        meio.rowconfigure(0, weight=1)
        res = Card(meio, "Lançamentos", "Clique duas vezes num concluído para abrir o PDF.")
        res.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.tabela = Tabela(res.corpo, [
            ("n", "#", 32, "e"), ("situacao", "Situação", 112, "w"), ("processo", "Processo", 146, "w"),
            ("servidor", "Servidor / detalhe", 150, "w"), ("tempo", "Tempo", 60, "e"),
        ], altura=9, selecao="browse", ordenavel=False)
        self.tabela.pack(fill="both", expand=True)
        self.tabela.arvore.bind("<Double-1>", self._abrir_pdf)

        reg = Card(meio, "Registro", "Mensagens do programa (o log completo fica na pasta logs).")
        reg.grid(row=0, column=1, sticky="nsew")
        moldura = tk.Frame(reg.corpo, bg=T.SUPERFICIE, highlightthickness=1, highlightbackground=T.BORDA)
        moldura.pack(fill="both", expand=True)
        self.texto = tk.Text(moldura, height=12, wrap="word", font=T.F["mono"], bg="#FBFCFE", fg=T.TEXTO,
                             relief="flat", padx=10, pady=8, state="disabled", cursor="arrow")
        rolagem = ttk.Scrollbar(moldura, orient="vertical", command=self.texto.yview)
        self.texto.configure(yscrollcommand=rolagem.set)
        self.texto.pack(side="left", fill="both", expand=True)
        rolagem.pack(side="right", fill="y")
        self.texto.tag_configure("linha", lmargin2=74, spacing1=1)
        self.texto.tag_configure("hora", foreground=T.TEXTO_3)
        self.texto.tag_configure("aviso", foreground=T.AVISO)
        self.texto.tag_configure("erro", foreground=T.ERRO)
        self.texto.tag_configure("destaque", foreground=T.PRIMARIA_TEXTO, font=(T.FAMILIA_MONO, 9, "bold"))
        app.ouvintes_log.append(self._receber_log)

        self._mostrar_estado()

    def _numero(self, master, rotulo: str, cor: str) -> tk.Label:
        quadro = tk.Frame(master, bg=T.SUPERFICIE)
        quadro.pack(side="left", padx=(22, 0))
        valor = tk.Label(quadro, text="—", bg=T.SUPERFICIE, fg=cor, font=T.F["h2"])
        valor.pack(anchor="e")
        ttk.Label(quadro, text=rotulo, style="Dica.Card.TLabel").pack(anchor="e")
        return valor

    def _pasta_pdf(self) -> Path:
        config.PASTA_PDF.mkdir(parents=True, exist_ok=True)
        return config.PASTA_PDF

    def _mostrar_estado(self) -> None:
        if self.rodou or self.app.executando:
            self.vazio.pack_forget()
            self.painel.pack(fill="both", expand=True, pady=(14, 0))
        else:
            self.painel.pack_forget()
            self.vazio.pack(fill="x", pady=(14, 0))
        self.btn_parar.state(["!disabled"] if self.app.executando and not self.app.controle.cancelar.is_set()
                             else ["disabled"])

    def ao_mostrar(self) -> None:
        self._mostrar_estado()

    # ---- Início ---------------------------------------------------------------------------

    def preparar(self, lotes) -> None:
        self.rodou = True
        self.total = len(lotes)
        self.inicio = time.monotonic()
        self.tempos, self.sucessos, self.erros, self.atual = [], 0, 0, 0
        self.resultados_pdf.clear()
        for w in self.avisos.winfo_children():
            w.destroy()
        self.tabela.limpar()
        for i, d in enumerate(lotes, 1):
            self.tabela.inserir([i, "Aguardando", d.processo, utils.formatar_cpf(d.cpf), ""], iid=str(i))
        self.tabela.atualizar_vazio()
        self.barra.configure(value=0, style="Horizontal.TProgressbar")
        self.lbl_lote.configure(text=f"Preparando {self.total} lançamento(s)…")
        self.lbl_detalhe.configure(text="Abrindo e conectando ao navegador.")
        self.etapas.definir(None)
        self.lbl_etapa.configure(text="")
        self._limpar_log()
        self._log_local(f"Início do processamento de {self.total} lançamento(s).", "destaque")
        self.cab.subtitulo.configure(text="Processando… você pode usar outras partes do programa enquanto isso.")
        self._atualizar_numeros()
        self._mostrar_estado()
        self._agendar_tique()

    def _agendar_tique(self) -> None:
        if self._tique:
            self.after_cancel(self._tique)
        self._tique = self.after(1000, self._tique_relogio)

    def _tique_relogio(self) -> None:
        self._tique = None
        if self.app.executando:
            self._atualizar_numeros()
            self._agendar_tique()

    def _atualizar_numeros(self) -> None:
        decorrido = time.monotonic() - self.inicio if self.inicio else 0
        self.n_ok.configure(text=str(self.sucessos))
        self.n_erro.configure(text=str(self.erros))
        self.n_decorrido.configure(text=formatar_duracao(decorrido))
        if self.tempos:
            media = sum(self.tempos) / len(self.tempos)
            faltam = self.total - len(self.tempos)
            self.n_media.configure(text=f"{media:.1f} s".replace(".", ","))
            self.n_restante.configure(text=formatar_duracao(media * faltam) if self.app.executando and faltam else "—")
        else:
            self.n_media.configure(text="—")
            self.n_restante.configure(text="—")

    # ---- Eventos do motor -----------------------------------------------------------------

    def evento(self, tipo: str, d: dict) -> None:
        if tipo == "status":
            self.lbl_detalhe.configure(text=d["texto"])
        elif tipo == "conectado":
            self._log_local(f"Navegador conectado em {d['segundos']:.1f} s.".replace(".", ","), "destaque")
            self.lbl_detalhe.configure(text="Navegador conectado.")
        elif tipo == "aguardando_login":
            self._mostrar_login()
        elif tipo == "login_confirmado":
            for w in self.avisos.winfo_children():
                w.destroy()
        elif tipo == "lote_inicio":
            self._lote_inicio(d)
        elif tipo == "etapa":
            self.etapas.definir(d["etapa"])
            self.lbl_etapa.configure(text=f"Etapa atual: {d['rotulo']}")
        elif tipo == "lote_fim":
            self._lote_fim(d)
        elif tipo == "erro_geral":
            Banner(self.avisos, "erro", f"O processamento parou: {d['mensagem']}\n"
                   "Confira se o navegador do programa está aberto e tente de novo.").pack(fill="x", pady=(14, 0))
        elif tipo == "fim":
            self._fim(d)

    def _mostrar_login(self) -> None:
        for w in self.avisos.winfo_children():
            w.destroy()
        self.lbl_lote.configure(text="Aguardando o seu login")
        self.lbl_detalhe.configure(text="Entre com a sua conta nas abas do DARE e do SEI.")

        def confirmar():
            self.app.controle.login_ok.set()
            for w in self.avisos.winfo_children():
                w.destroy()
            self._log_local("Login confirmado. Começando os lançamentos.", "destaque")

        Banner(self.avisos, "aviso",
               "Primeiro acesso nesta sessão: no navegador que o programa abriu, entre com a sua conta no "
               "DARE e no SEI. Quando as duas abas estiverem logadas, clique no botão ao lado.",
               [("✔  Já entrei nos dois sistemas", confirmar, "Primario.TButton")]).pack(fill="x", pady=(14, 0))
        self.app.toast.mostrar("Faça o login no DARE e no SEI e confirme aqui.", "aviso", 6000)
        try:
            self.app.deiconify()
            self.app.lift()
        except tk.TclError:
            pass

    def _lote_inicio(self, d: dict) -> None:
        i, total, dados = d["indice"], d["total"], d["dados"]
        self.atual = i
        self.lbl_lote.configure(text=f"Lançamento {i} de {total}")
        origem = f" · {dados.origem}" if dados.origem else ""
        self.lbl_detalhe.configure(text=f"Processo {dados.processo} · CPF {utils.formatar_cpf(dados.cpf)} · "
                                        f"R$ {dados.valor}{origem}")
        self.etapas.definir("preparo")
        self.lbl_etapa.configure(text="Etapa atual: Preparar formulário")
        self.tabela.arvore.item(str(i), tags=("andamento",))
        self.tabela.arvore.set(str(i), "situacao", "▶ Processando")
        self.tabela.arvore.see(str(i))

    def _lote_fim(self, d: dict) -> None:
        i, r, segundos = d["indice"], d["resultado"], d["segundos"]
        self.tempos.append(segundos)
        if r.sucesso:
            self.sucessos += 1
            situacao, tag, detalhe = "✔ Concluído", "sucesso", r.servidor or "—"
            self.resultados_pdf[str(i)] = r.pdf
        else:
            self.erros += 1
            situacao, tag = "✖ Erro", "erro"
            detalhe = r.erro + (" · DARE gerado, não anexado" if r.pdf else "")
            if r.pdf:
                self.resultados_pdf[str(i)] = r.pdf
        self.tabela.arvore.item(str(i), tags=(tag,))
        self.tabela.arvore.set(str(i), "situacao", situacao)
        self.tabela.arvore.set(str(i), "servidor", detalhe)
        self.tabela.arvore.set(str(i), "tempo", f"{segundos:.1f} s".replace(".", ","))
        self.barra.configure(value=len(self.tempos) / max(1, self.total) * 100)
        self.etapas.definir(None, concluido=r.sucesso)
        self._atualizar_numeros()

    def _fim(self, d: dict) -> None:
        if self._tique:
            self.after_cancel(self._tique)
            self._tique = None
        resultados, pendentes = d.get("resultados", []), d.get("pendentes", [])
        total = d.get("total", self.total)
        ok = sum(1 for r in resultados if r.sucesso)
        decorrido = formatar_duracao(time.monotonic() - self.inicio)
        self._atualizar_numeros()
        self.n_restante.configure(text="—")
        self.lbl_etapa.configure(text="")
        self.etapas.definir(None, concluido=not pendentes)
        for w in self.avisos.winfo_children():
            if not isinstance(w, Banner) or w.icone.cget("text") != "✖":
                w.destroy()
        acoes = []
        if not pendentes:
            self.barra.configure(style="Sucesso.Horizontal.TProgressbar", value=100)
            self.lbl_lote.configure(text="Tudo pronto!")
            self.lbl_detalhe.configure(text=f"{ok} de {total} lançamento(s) concluído(s) em {decorrido}.")
            Banner(self.avisos, "sucesso", f"Concluído: {ok} de {total} DARE(s) gerado(s) e anexado(s) no SEI "
                   f"em {decorrido}.", acoes).pack(fill="x", pady=(14, 0))
            self.app.toast.mostrar(f"Processamento concluído: {ok} de {total} com sucesso.")
        else:
            interrompido = d.get("interrompido")
            nao_feitos = total - len(resultados)
            partes = [f"{ok} de {total} concluído(s)"]
            if self.erros:
                partes.append(f"{self.erros} com erro")
            if nao_feitos:
                partes.append(f"{nao_feitos} não processado(s)")
            self.lbl_lote.configure(text="Interrompido" if interrompido else "Terminou com pendências")
            self.lbl_detalhe.configure(text=" · ".join(partes) + f" · {decorrido}")
            rotulo = "↻  Processar o pendente" if len(pendentes) == 1 else f"↻  Processar os {len(pendentes)} pendentes"
            acoes.insert(0, (rotulo,
                             lambda: self.app.iniciar_execucao(self.app.lotes), "Primario.TButton"))
            acoes.append(("Ver lista", lambda: self.app.mostrar("lancamentos"), "TButton"))
            Banner(self.avisos, "aviso",
                   f"{' · '.join(partes)}. Os pendentes continuam na lista de Lançamentos. "
                   "Se um DARE foi gerado mas não anexado, confira o processo no SEI antes de repetir.",
                   acoes).pack(fill="x", pady=(14, 0))
            for i in range(len(resultados) + 1, total + 1):
                if str(i) in self.tabela.arvore.get_children():
                    self.tabela.arvore.set(str(i), "situacao", "■ Não processado")
                    self.tabela.arvore.item(str(i), tags=("aviso",))
        self.cab.subtitulo.configure(text="Último processamento: " + " · ".join(
            [f"{ok} de {total} concluído(s)", decorrido]))
        self._mostrar_estado()

    def parar(self) -> None:
        if not self.app.executando:
            return
        self.app.controle.cancelar.set()
        self.btn_parar.state(["disabled"])
        self.lbl_etapa.configure(text="Parando: o lançamento atual vai terminar e os demais ficam pendentes.")
        self._log_local("Parada solicitada: termina o lançamento atual e para.", "aviso")

    def _abrir_pdf(self, _evento) -> None:
        sel = self.tabela.selecionados()
        if sel and self.resultados_pdf.get(sel[0]):
            caminho = Path(self.resultados_pdf[sel[0]])
            if caminho.exists():
                abrir_no_sistema(caminho)
            else:
                self.app.toast.mostrar("O PDF não está mais na pasta.", "aviso")

    # ---- Registro -------------------------------------------------------------------------

    def _limpar_log(self) -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.configure(state="disabled")

    def _escrever(self, linhas: list[tuple[str, str, str]]) -> None:
        self.texto.configure(state="normal")
        for hora, msg, tag in linhas:
            self.texto.insert("end", hora + "  ", ("hora", "linha"))
            self.texto.insert("end", msg + "\n", (tag, "linha") if tag else ("linha",))
        excesso = int(self.texto.index("end-1c").split(".")[0]) - 3000
        if excesso > 0:
            self.texto.delete("1.0", f"{excesso + 1}.0")
        self.texto.configure(state="disabled")
        self.texto.see("end")

    def _log_local(self, msg: str, tag: str = "") -> None:
        self._escrever([(time.strftime("%H:%M:%S"), msg, tag)])

    def _receber_log(self, registros: list[logging.LogRecord]) -> None:
        linhas = []
        for r in registros:
            if r.name.startswith("dare.app") or r.name.startswith("dare.desempenho"):
                continue
            tag = "erro" if r.levelno >= logging.ERROR else "aviso" if r.levelno >= logging.WARNING else (
                "destaque" if r.getMessage().startswith("===") else "")
            msg = r.getMessage().splitlines()[0][:400]
            linhas.append((time.strftime("%H:%M:%S", time.localtime(r.created)), msg, tag))
        if linhas:
            self._escrever(linhas)
