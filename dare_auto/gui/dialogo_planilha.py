"""Janela "Importar planilha": escolher a planilha, a aba, as colunas e as linhas, e ler os lançamentos."""

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import config, excel_com, planilha, planilha_arquivo
from ..planilha import CAMPOS, OBRIGATORIOS, ROTULOS, Mapeamento, Origem
from . import tema as T
from .app import TITULO
from .widgets import Card, Rolavel, Tabela, abrir_no_sistema

log = logging.getLogger("dare.gui.planilha")

NENHUMA = "— não usar (valor padrão) —"
FIXO = "✎ Mesmo valor em todas as linhas…"


class DialogoPlanilha(tk.Toplevel):
    @classmethod
    def abrir(cls, app) -> list | None:
        dialogo = cls(app)
        app.wait_window(dialogo)
        return dialogo.resultado

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.resultado = None
        self.pasta = None
        self.tabela = None
        self.abertas = []
        self.cabecalhos: dict[int, str] = {}
        self.opcoes_coluna: list[tuple[str, int | None]] = []
        self.lidos = None
        self.title("Importar planilha — DARE Automação")
        self.configure(bg=T.FUNDO)
        largura, altura = 900, min(780, int(app.winfo_screenheight() * 0.88))
        x = app.winfo_rootx() + max(0, (app.winfo_width() - largura) // 2)
        y = app.winfo_rooty() + max(0, (app.winfo_height() - altura) // 2)
        self.geometry(f"{largura}x{altura}+{x}+{max(0, y)}")
        self.minsize(760, 560)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.cancelar)
        self.bind("<Escape>", lambda e: self.cancelar())

        topo = ttk.Frame(self, padding=(24, 18, 24, 6))
        topo.pack(fill="x")
        ttk.Label(topo, text="Importar planilha", style="Titulo.TLabel").pack(anchor="w")
        self.lbl_modo = ttk.Label(topo, text="", style="Subtitulo.TLabel")
        self.lbl_modo.pack(anchor="w")

        rodape = tk.Frame(self, bg=T.SUPERFICIE, highlightthickness=1, highlightbackground=T.BORDA)
        rodape.pack(side="bottom", fill="x")
        self.lbl_rodape = ttk.Label(rodape, text="O programa nunca altera a sua planilha.", style="Muted.Card.TLabel")
        self.lbl_rodape.pack(side="left", padx=20)
        self.btn_adicionar = ttk.Button(rodape, text="Adicionar à lista", style="Primario.TButton",
                                        command=self.confirmar)
        self.btn_adicionar.pack(side="right", padx=(8, 20), pady=12)
        ttk.Button(rodape, text="Cancelar", command=self.cancelar).pack(side="right", pady=12)

        rol = Rolavel(self)
        rol.pack(fill="both", expand=True, padx=(24, 8))
        area = rol.interno
        self._passo1(area)
        self._passo2(area)
        self._passo3(area)
        self._passo4(area)
        self._atualizar_estado()
        self.after(50, self._carregar_abertas)
        self.grab_set()
        self.focus_set()

    # ---- 1. Planilha ----------------------------------------------------------------------

    def _passo1(self, area) -> None:
        c = Card(area, "1 · Escolha a planilha", "Uma linha da planilha = um DARE.")
        c.pack(fill="x", pady=(6, 12), padx=(0, 12))
        self.excel = planilha_arquivo.excel_disponivel()
        self.quadro_abertas = tk.Frame(c.corpo, bg=T.SUPERFICIE)
        self.quadro_abertas.pack(fill="x")
        ttk.Label(self.quadro_abertas, text="Planilhas abertas no Excel agora:", style="Rotulo.Card.TLabel").pack(anchor="w")
        linha = tk.Frame(self.quadro_abertas, bg=T.SUPERFICIE)
        linha.pack(fill="x", pady=(4, 0))
        self.lista_abertas = tk.Listbox(linha, height=4, font=T.F["base"], activestyle="none",
                                        selectbackground=T.PRIMARIA_CLARA, selectforeground=T.TEXTO,
                                        highlightthickness=1, highlightbackground=T.BORDA, relief="flat",
                                        borderwidth=0)
        self.lista_abertas.pack(side="left", fill="x", expand=True)
        self.lista_abertas.bind("<<ListboxSelect>>", self._escolher_aberta)
        ttk.Button(linha, text="↻", width=3, command=self._carregar_abertas).pack(side="left", padx=(8, 0), anchor="n")
        botoes = tk.Frame(c.corpo, bg=T.SUPERFICIE)
        botoes.pack(fill="x", pady=(10, 0))
        ttk.Button(botoes, text="Procurar arquivo…", style="Primario.TButton", command=self._procurar).pack(side="left")
        ttk.Button(botoes, text="Criar planilha modelo", command=self._criar_modelo).pack(side="left", padx=8)
        self.lbl_arquivo = ttk.Label(c.corpo, text="Nenhuma planilha escolhida.", style="Muted.Card.TLabel",
                                     wraplength=760, justify="left")
        self.lbl_arquivo.pack(anchor="w", pady=(10, 0))
        if self.excel:
            self.lbl_modo.configure(text="Usando o Microsoft Excel. Planilhas em “Modo de Exibição Protegido” não "
                                         "aparecem na lista: clique em “Habilitar edição” no Excel.")
        else:
            self.quadro_abertas.pack_forget()
            self.lbl_modo.configure(text="Excel não encontrado neste computador: arquivos .xlsx e .xlsm são lidos "
                                         "diretamente, sem precisar dele.")

    def _carregar_abertas(self) -> None:
        if not self.excel:
            return
        self.lista_abertas.delete(0, "end")
        try:
            self.abertas = excel_com.listar_abertas()
        except excel_com.ExcelIndisponivel:
            self.excel = False
            self.quadro_abertas.pack_forget()
            self.lbl_modo.configure(text="Excel indisponível: arquivos .xlsx e .xlsm são lidos diretamente.")
            return
        except Exception:  # noqa: BLE001
            log.exception("Falha ao listar planilhas abertas")
            self.abertas = []
        for p in self.abertas:
            self.lista_abertas.insert("end", f"  {p.nome}    —    {p.caminho}")
        if not self.abertas:
            self.lista_abertas.insert("end", "  (nenhuma planilha aberta — use “Procurar arquivo…”)")
            self.lista_abertas.itemconfigure(0, foreground=T.TEXTO_3)

    def _escolher_aberta(self, _evento) -> None:
        sel = self.lista_abertas.curselection()
        if sel and sel[0] < len(self.abertas):
            self._usar_pasta(self.abertas[sel[0]])

    def _procurar(self) -> None:
        tipos = [("Planilhas do Excel", "*.xlsx *.xlsm *.xlsb *.xls")] if self.excel else \
            [("Planilhas do Excel", "*.xlsx *.xlsm")]
        caminho = filedialog.askopenfilename(parent=self, title="Escolha a planilha", filetypes=tipos + [("Todos", "*.*")])
        if not caminho:
            return
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            pasta = planilha_arquivo.abrir(caminho)
        except (FileNotFoundError, excel_com.ExcelIndisponivel) as exc:
            messagebox.showerror(TITULO, str(exc), parent=self)
            return
        finally:
            self.configure(cursor="")
        self._usar_pasta(pasta)

    def _criar_modelo(self) -> None:
        destino = config.PASTA_MODELOS / "modelo_dare.xlsx"
        if destino.exists() and not messagebox.askyesno(
                TITULO, "Já existe uma planilha modelo. Criar de novo (substitui o arquivo)?\n\n"
                        "Não = só abrir a que já existe.", parent=self):
            abrir_no_sistema(destino)
            return
        try:
            planilha_arquivo.criar_modelo_qualquer(destino)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(TITULO, f"Não consegui criar o modelo: {exc}", parent=self)
            return
        abrir_no_sistema(destino)
        messagebox.showinfo(TITULO, f"Modelo criado em:\n{destino}\n\nPreencha uma linha por DARE, salve e depois "
                                    "escolha o arquivo aqui (ou atualize a lista de abertas).", parent=self)
        self._carregar_abertas()

    def _usar_pasta(self, pasta) -> None:
        if self.pasta is not None and self.pasta is not pasta:
            self.pasta.fechar()
        self.pasta = pasta
        try:
            abas = pasta.abas()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(TITULO, f"Não consegui ler as abas: {exc}", parent=self)
            return
        self.lbl_arquivo.configure(text=f"✔  {pasta.nome}\n{pasta.caminho}", style="Card.TLabel")
        self.cmb_aba.configure(values=abas)
        if abas:
            self.cmb_aba.set(abas[0])
            self._usar_aba()

    # ---- 2. Aba e cabeçalho ---------------------------------------------------------------

    def _passo2(self, area) -> None:
        c = Card(area, "2 · Aba e cabeçalho", "O programa procura sozinho a linha com os títulos das colunas.")
        c.pack(fill="x", pady=(0, 12), padx=(0, 12))
        linha = tk.Frame(c.corpo, bg=T.SUPERFICIE)
        linha.pack(fill="x")
        ttk.Label(linha, text="Aba", style="Rotulo.Card.TLabel").pack(side="left")
        self.cmb_aba = ttk.Combobox(linha, state="readonly", width=28)
        self.cmb_aba.pack(side="left", padx=(8, 24))
        self.cmb_aba.bind("<<ComboboxSelected>>", lambda e: self._usar_aba())
        ttk.Label(linha, text="Linha do cabeçalho", style="Rotulo.Card.TLabel").pack(side="left")
        self.var_cab = tk.StringVar(value="1")
        self.spn_cab = ttk.Spinbox(linha, from_=0, to=500, width=6, textvariable=self.var_cab,
                                   command=self._mudar_cabecalho)
        self.spn_cab.pack(side="left", padx=8)
        self.spn_cab.bind("<FocusOut>", lambda e: self._mudar_cabecalho())
        self.spn_cab.bind("<Return>", lambda e: self._mudar_cabecalho())
        ttk.Label(linha, text="(0 = sem cabeçalho)", style="Dica.Card.TLabel").pack(side="left")
        self.lbl_colunas = ttk.Label(c.corpo, text="", style="Dica.Card.TLabel", wraplength=760, justify="left")
        self.lbl_colunas.pack(anchor="w", pady=(10, 0))

    def _usar_aba(self) -> None:
        if self.pasta is None or not self.cmb_aba.get():
            return
        try:
            self.tabela = self.pasta.tabela(self.cmb_aba.get())
        except ValueError as exc:
            messagebox.showerror(TITULO, str(exc), parent=self)
            return
        chave = planilha.chave_mapeamento(self.tabela.nome, self.tabela.aba)
        salvo = planilha.carregar_mapeamento(chave)
        if salvo and not salvo.faltando():
            mapa, origem = salvo, "Colunas salvas da última vez para esta planilha/aba."
        else:
            linha = planilha.detectar_linha_cabecalho(self.tabela)
            mapa = Mapeamento(planilha.sugerir_mapeamento(planilha.ler_cabecalhos(self.tabela, linha)), linha)
            origem = "Colunas sugeridas pelos títulos do cabeçalho. Confira."
        self.var_cab.set(str(mapa.linha_cabecalho))
        self._carregar_cabecalhos()
        self._aplicar_mapeamento(mapa)
        self.lbl_mapa.configure(text=origem)
        self._sugerir_linhas()
        self._invalidar_leitura()

    def _mudar_cabecalho(self) -> None:
        if self.tabela is None:
            return
        atual = self._mapeamento_da_tela(silencioso=True)
        self._carregar_cabecalhos()
        if atual is not None:
            self._aplicar_mapeamento(atual)
        self._sugerir_linhas()
        self._invalidar_leitura()

    def _linha_cabecalho(self) -> int:
        try:
            return max(0, int(self.var_cab.get()))
        except ValueError:
            return 0

    def _carregar_cabecalhos(self) -> None:
        self.cabecalhos = planilha.ler_cabecalhos(self.tabela, self._linha_cabecalho())
        ultima = max(list(self.cabecalhos) + [10])
        colunas = sorted(set(self.cabecalhos) | set(range(1, min(ultima + 3, 60) + 1)))
        self.opcoes_coluna = [(NENHUMA, None)]
        for col in colunas:
            nome = self.cabecalhos.get(col, "")
            letra = planilha.numero_para_letra(col)
            self.opcoes_coluna.append((f"{letra}  ·  {nome}" if nome else f"Coluna {letra}", col))
        self.opcoes_coluna.append((FIXO, -1))
        valores = [t for t, _ in self.opcoes_coluna]
        for cmb, _ in self.linhas_campo.values():
            cmb.configure(values=valores)
        if self.cabecalhos:
            itens = [f"{planilha.numero_para_letra(c)}: {t}" for c, t in sorted(self.cabecalhos.items())][:30]
            self.lbl_colunas.configure(text="Colunas encontradas — " + "   ·   ".join(itens))
        else:
            self.lbl_colunas.configure(text="Nenhum título nessa linha. Se a planilha não tem cabeçalho, use 0 e "
                                            "escolha as colunas pela letra.")

    # ---- 3. Colunas -----------------------------------------------------------------------

    def _passo3(self, area) -> None:
        c = Card(area, "3 · De onde vem cada informação",
                 "Escolha a coluna de cada campo. Use “mesmo valor em todas as linhas” para algo que nunca muda "
                 "(ex.: o CNPJ do órgão). * = obrigatório.")
        c.pack(fill="x", pady=(0, 12), padx=(0, 12))
        self.lbl_mapa = ttk.Label(c.corpo, text="", style="Dica.Card.TLabel")
        self.lbl_mapa.pack(anchor="w", pady=(0, 6))
        grade = tk.Frame(c.corpo, bg=T.SUPERFICIE)
        grade.pack(fill="x")
        grade.columnconfigure(1, weight=1)
        self.linhas_campo: dict[str, tuple[ttk.Combobox, ttk.Entry]] = {}
        self.vars_fixo: dict[str, tk.StringVar] = {}
        for i, campo in enumerate(CAMPOS):
            rotulo = ROTULOS[campo] + (" *" if campo in OBRIGATORIOS else "")
            ttk.Label(grade, text=rotulo, style="Rotulo.Card.TLabel").grid(row=i, column=0, sticky="w", pady=4, padx=(0, 12))
            cmb = ttk.Combobox(grade, state="readonly")
            cmb.grid(row=i, column=1, sticky="ew", pady=4)
            var = tk.StringVar()
            ent = ttk.Entry(grade, textvariable=var, width=22)
            ent.grid(row=i, column=2, sticky="ew", pady=4, padx=(8, 0))
            ent.state(["disabled"])
            cmb.bind("<<ComboboxSelected>>", lambda e, c=campo: self._mudou_campo(c))
            ent.bind("<KeyRelease>", lambda e: self._invalidar_leitura())
            self.linhas_campo[campo] = (cmb, ent)
            self.vars_fixo[campo] = var
        self.lbl_falta = ttk.Label(c.corpo, text="", style="Erro.Card.TLabel")
        self.lbl_falta.pack(anchor="w", pady=(6, 0))

    def _mudou_campo(self, campo: str) -> None:
        cmb, ent = self.linhas_campo[campo]
        if cmb.get() == FIXO:
            ent.state(["!disabled"])
            ent.focus_set()
        else:
            ent.state(["disabled"])
        self._sugerir_linhas()
        self._invalidar_leitura()

    def _aplicar_mapeamento(self, mapa: Mapeamento) -> None:
        por_coluna = {col: texto for texto, col in self.opcoes_coluna if col}
        for campo in CAMPOS:
            cmb, ent = self.linhas_campo[campo]
            origem = mapa.origem(campo)
            if origem.fixo is not None:
                cmb.set(FIXO)
                self.vars_fixo[campo].set(origem.fixo)
                ent.state(["!disabled"])
            elif origem.coluna:
                if origem.coluna not in por_coluna:
                    letra = planilha.numero_para_letra(origem.coluna)
                    self.opcoes_coluna.insert(-1, (f"Coluna {letra}", origem.coluna))
                    cmb.configure(values=[t for t, _ in self.opcoes_coluna])
                    por_coluna[origem.coluna] = f"Coluna {letra}"
                cmb.set(por_coluna[origem.coluna])
                ent.state(["disabled"])
            else:
                cmb.set(NENHUMA)
                ent.state(["disabled"])

    def _mapeamento_da_tela(self, silencioso: bool = False) -> Mapeamento | None:
        por_texto = dict(self.opcoes_coluna)
        campos: dict[str, Origem] = {}
        for campo in CAMPOS:
            cmb, _ = self.linhas_campo[campo]
            escolha = por_texto.get(cmb.get())
            if escolha == -1:
                fixo = self.vars_fixo[campo].get().strip()
                if fixo:
                    campos[campo] = Origem(fixo=fixo)
            elif escolha:
                campos[campo] = Origem(coluna=escolha)
        mapa = Mapeamento(campos, self._linha_cabecalho())
        falta = mapa.faltando()
        if falta and not silencioso:
            self.lbl_falta.configure(text="✖ Falta indicar: " + ", ".join(ROTULOS[c] for c in falta))
            return None
        self.lbl_falta.configure(text="")
        return mapa

    # ---- 4. Linhas e leitura --------------------------------------------------------------

    def _passo4(self, area) -> None:
        c = Card(area, "4 · Linhas e leitura", "Linhas em branco e linhas ocultas/filtradas são puladas.")
        c.pack(fill="x", pady=(0, 16), padx=(0, 12))
        linha = tk.Frame(c.corpo, bg=T.SUPERFICIE)
        linha.pack(fill="x")
        self.var_de, self.var_ate = tk.StringVar(), tk.StringVar()
        ttk.Label(linha, text="Da linha", style="Rotulo.Card.TLabel").pack(side="left")
        ttk.Spinbox(linha, from_=1, to=1_000_000, width=8, textvariable=self.var_de).pack(side="left", padx=8)
        ttk.Label(linha, text="até a linha", style="Rotulo.Card.TLabel").pack(side="left")
        ttk.Spinbox(linha, from_=1, to=1_000_000, width=8, textvariable=self.var_ate).pack(side="left", padx=8)
        self.btn_ler = ttk.Button(linha, text="Ler planilha", style="Primario.TButton", command=self.ler)
        self.btn_ler.pack(side="left", padx=(16, 0))
        self.lbl_ultima = ttk.Label(c.corpo, text="", style="Dica.Card.TLabel")
        self.lbl_ultima.pack(anchor="w", pady=(6, 0))
        self.lbl_leitura = tk.Label(c.corpo, text="", bg=T.SUPERFICIE, fg=T.TEXTO, font=T.F["negrito"],
                                    anchor="w", justify="left")
        self.lbl_leitura.pack(anchor="w", pady=(10, 4), fill="x")
        self.t_problemas = Tabela(c.corpo, [("linha", "Linha", 70, "e"), ("problema", "Problema (a linha fica de fora)", 640, "w")],
                                  altura=5, vazio="Nenhum problema encontrado.", selecao="browse")

    def _sugerir_linhas(self) -> None:
        if self.tabela is None:
            return
        mapa = self._mapeamento_da_tela(silencioso=True)
        cab = self._linha_cabecalho()
        self.var_de.set(str(cab + 1 if cab else 1))
        if mapa and mapa.colunas_usadas():
            try:
                ultima = planilha.ultima_linha_com_dados(self.tabela, mapa)
            except Exception:  # noqa: BLE001
                ultima = 0
            self.var_ate.set(str(ultima) if ultima else "")
            self.lbl_ultima.configure(text=f"Última linha com dados: {ultima}." if ultima else
                                      "Não encontrei dados nas colunas escolhidas.")

    def _invalidar_leitura(self) -> None:
        self.lidos = None
        self.lbl_leitura.configure(text="")
        self.t_problemas.pack_forget()
        self._atualizar_estado()

    def ler(self) -> None:
        if self.tabela is None:
            messagebox.showinfo(TITULO, "Escolha uma planilha primeiro.", parent=self)
            return
        mapa = self._mapeamento_da_tela()
        if mapa is None:
            return
        try:
            de = int(self.var_de.get())
            ate = int(self.var_ate.get()) if self.var_ate.get().strip() else planilha.ultima_linha_com_dados(self.tabela, mapa)
        except ValueError:
            messagebox.showerror(TITULO, "Informe as linhas com números inteiros.", parent=self)
            return
        if ate < de:
            messagebox.showerror(TITULO, "A linha final não pode ser menor que a inicial.", parent=self)
            return
        if mapa.linha_cabecalho and de <= mapa.linha_cabecalho and not messagebox.askyesno(
                TITULO, f"A linha {mapa.linha_cabecalho} é o cabeçalho e seria lida como dado. Continuar?", parent=self):
            return
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            r = planilha.ler_lotes(self.tabela, mapa, de, ate)
        except Exception as exc:  # noqa: BLE001
            log.exception("Falha ao ler a planilha")
            messagebox.showerror(TITULO, f"Falha ao ler a planilha: {exc}", parent=self)
            return
        finally:
            self.configure(cursor="")
        for p in r.problemas:
            log.warning("Planilha, linha %d ignorada: %s", p.linha, p.mensagem)
        self.lidos = (r, mapa)
        partes = [f"✔ {len(r.lotes)} linha(s) válida(s)"]
        if r.problemas:
            partes.append(f"✖ {len(r.problemas)} com problema")
        if r.vazias:
            partes.append(f"{r.vazias} em branco")
        if r.ocultas:
            partes.append(f"{r.ocultas} oculta(s)/filtrada(s)")
        self.lbl_leitura.configure(text="   ·   ".join(partes), fg=T.SUCESSO if r.lotes and not r.problemas else
                                   (T.AVISO if r.lotes else T.ERRO))
        self.t_problemas.limpar()
        if r.problemas:
            for p in r.problemas:
                self.t_problemas.inserir([p.linha, p.mensagem], tags=("erro",))
            self.t_problemas.atualizar_vazio()
            self.t_problemas.pack(fill="x", pady=(4, 0))
        self._atualizar_estado()

    # ---- Fim ------------------------------------------------------------------------------

    def _atualizar_estado(self) -> None:
        n = len(self.lidos[0].lotes) if self.lidos else 0
        if n:
            self.btn_adicionar.configure(text=f"Adicionar {n} lançamento(s) à lista")
            self.btn_adicionar.state(["!disabled"])
            self.lbl_rodape.configure(text="Você ainda poderá conferir e editar tudo antes de iniciar.")
        else:
            self.btn_adicionar.configure(text="Adicionar à lista")
            self.btn_adicionar.state(["disabled"])
            self.lbl_rodape.configure(text="Escolha a planilha, confira as colunas e clique em “Ler planilha”.")

    def confirmar(self) -> None:
        if not self.lidos or not self.lidos[0].lotes:
            return
        r, mapa = self.lidos
        if r.problemas and not messagebox.askyesno(
                TITULO, f"{len(r.problemas)} linha(s) com problema ficarão de fora.\n\n"
                        f"Continuar só com as {len(r.lotes)} válida(s)?", parent=self):
            return
        try:
            planilha.salvar_mapeamento(planilha.chave_mapeamento(self.tabela.nome, self.tabela.aba), mapa)
        except OSError:
            log.warning("Não consegui salvar o mapeamento de colunas.", exc_info=True)
        log.info("Planilha importada: %s / %s · %d lançamento(s)", self.tabela.nome, self.tabela.aba, len(r.lotes))
        self.resultado = r.lotes
        self._fechar()

    def cancelar(self) -> None:
        self.resultado = None
        self._fechar()

    def _fechar(self) -> None:
        if self.pasta is not None:
            try:
                self.pasta.fechar()
            except Exception:  # noqa: BLE001
                pass
        self.grab_release()
        self.destroy()

