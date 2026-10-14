"""Página Arquivos PDF: tamanho da pasta DARE_PDFs, limpeza quando o usuário quiser e limpeza automática."""

import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ... import config, limpeza, preferencias
from .. import tema as T
from ..app import TITULO, Pagina
from ..widgets import KPI, CabecalhoPagina, Card, Rolavel, Tabela, abrir_no_sistema

CRITERIOS = [
    ("mais_antigos", "PDFs com mais de"),
    ("ate_data", "PDFs gerados até o dia"),
    ("selecionados", "Somente os que eu selecionar na lista"),
    ("todos", "Todos os PDFs da pasta"),
]


class PaginaArquivos(Pagina):
    titulo = "Arquivos PDF"
    icone = "▤"

    def __init__(self, app):
        super().__init__(app)
        self.arquivos: list[limpeza.ArquivoPdf] = []
        self._por_iid: dict[str, limpeza.ArquivoPdf] = {}

        cab = CabecalhoPagina(self, "Arquivos PDF",
                              "Veja quanto espaço os DAREs ocupam e escolha quando e o que apagar.")
        cab.pack(fill="x")
        ttk.Button(cab.acoes, text="↻  Atualizar", command=self.ao_mostrar).pack(side="left", padx=(0, 8))
        ttk.Button(cab.acoes, text="Alterar pasta…", command=self.alterar_pasta).pack(side="left", padx=(0, 8))
        ttk.Button(cab.acoes, text="Abrir pasta", command=self.abrir_pasta).pack(side="left")
        self.lbl_pasta = ttk.Label(self, text="", style="Subtitulo.TLabel")
        self.lbl_pasta.pack(anchor="w", pady=(6, 0))

        rolavel = Rolavel(self)
        rolavel.pack(fill="both", expand=True, pady=(10, 0))
        area = rolavel.interno

        kpis = tk.Frame(area, bg=T.FUNDO)
        kpis.pack(fill="x")
        self.k_qtd = KPI(kpis, "Arquivos")
        self.k_tam = KPI(kpis, "Espaço ocupado")
        self.k_antigo = KPI(kpis, "Mais antigo")
        self.k_prot = KPI(kpis, "Não anexados no SEI")
        for i, k in enumerate((self.k_qtd, self.k_tam, self.k_antigo, self.k_prot)):
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            kpis.columnconfigure(i, weight=1, uniform="k")

        linha = tk.Frame(area, bg=T.FUNDO)
        linha.pack(fill="x", pady=(14, 0))
        linha.columnconfigure(0, weight=3, uniform="l")
        linha.columnconfigure(1, weight=2, uniform="l")

        # ---- Limpar agora
        agora = Card(linha, "Limpar agora", "Escolha o que apagar. As linhas marcadas em vermelho na lista "
                     "abaixo mostram exatamente o que será removido.")
        agora.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        c = agora.corpo
        self.var_criterio = tk.StringVar(value="mais_antigos")
        self.var_dias = tk.StringVar(value=str(app.pref.limpeza_dias or 30))
        self.var_data = tk.StringVar(value=(date.today() - timedelta(days=30)).strftime("%d/%m/%Y"))
        for chave, texto in CRITERIOS:
            fila = tk.Frame(c, bg=T.SUPERFICIE)
            fila.pack(fill="x", pady=1)
            ttk.Radiobutton(fila, text=texto, value=chave, variable=self.var_criterio,
                            command=self.atualizar_previa).pack(side="left")
            if chave == "mais_antigos":
                caixa = ttk.Spinbox(fila, from_=0, to=3650, width=6, textvariable=self.var_dias,
                                    command=self.atualizar_previa)
                caixa.pack(side="left", padx=(6, 4))
                caixa.bind("<KeyRelease>", lambda e: self.atualizar_previa())
                ttk.Label(fila, text="dias", style="Card.TLabel").pack(side="left")
            elif chave == "ate_data":
                entrada = ttk.Entry(fila, textvariable=self.var_data, width=12)
                entrada.pack(side="left", padx=(6, 4))
                entrada.bind("<KeyRelease>", lambda e: self.atualizar_previa())
                ttk.Label(fila, text="(DD/MM/AAAA)", style="Dica.Card.TLabel").pack(side="left")
        ttk.Separator(c).pack(fill="x", pady=10)
        self.var_lixeira = tk.BooleanVar(value=app.pref.usar_lixeira)
        self.var_proteger = tk.BooleanVar(value=app.pref.proteger_nao_anexados)
        ttk.Checkbutton(c, text="Enviar para a Lixeira (dá para recuperar depois)", variable=self.var_lixeira,
                        command=self._salvar_opcoes).pack(anchor="w")
        ttk.Checkbutton(c, text="Manter os PDFs de DAREs que não foram anexados no SEI (recomendado)",
                        variable=self.var_proteger, command=lambda: (self._salvar_opcoes(), self.atualizar_previa())
                        ).pack(anchor="w")
        rodape = tk.Frame(c, bg=T.SUPERFICIE)
        rodape.pack(fill="x", pady=(12, 0))
        self.lbl_previa = tk.Label(rodape, text="", bg=T.SUPERFICIE, fg=T.TEXTO, font=T.F["negrito"],
                                   anchor="w", justify="left", wraplength=420)
        self.lbl_previa.pack(side="left", fill="x", expand=True)
        self.btn_limpar = ttk.Button(rodape, text="Apagar PDFs…", style="Perigo.TButton", command=self.limpar)
        self.btn_limpar.pack(side="right")

        # ---- Automático
        auto = Card(linha, "Limpeza automática", "Opcional. Fica guardado para as próximas vezes.")
        auto.grid(row=0, column=1, sticky="nsew")
        a = auto.corpo
        self.var_auto = tk.BooleanVar(value=app.pref.limpeza_automatica)
        self.var_auto_dias = tk.StringVar(value=str(app.pref.limpeza_dias))
        self.var_aviso = tk.StringVar(value=str(app.pref.aviso_tamanho_mb))
        ttk.Checkbutton(a, text="Ao abrir o programa, apagar PDFs antigos", variable=self.var_auto,
                        command=self._salvar_opcoes).pack(anchor="w")
        fila = tk.Frame(a, bg=T.SUPERFICIE)
        fila.pack(anchor="w", padx=(26, 0), pady=(2, 8))
        ttk.Label(fila, text="Antigos = com mais de", style="Card.TLabel").pack(side="left")
        s = ttk.Spinbox(fila, from_=1, to=3650, width=6, textvariable=self.var_auto_dias, command=self._salvar_opcoes)
        s.pack(side="left", padx=6)
        s.bind("<FocusOut>", lambda e: self._salvar_opcoes())
        ttk.Label(fila, text="dias", style="Card.TLabel").pack(side="left")
        ttk.Label(a, text="Avisar na tela inicial quando a pasta passar de", style="Card.TLabel").pack(anchor="w")
        fila = tk.Frame(a, bg=T.SUPERFICIE)
        fila.pack(anchor="w", pady=(4, 0))
        s = ttk.Spinbox(fila, from_=0, to=100000, increment=100, width=8, textvariable=self.var_aviso,
                        command=self._salvar_opcoes)
        s.pack(side="left")
        s.bind("<FocusOut>", lambda e: self._salvar_opcoes())
        ttk.Label(fila, text="MB   (0 = nunca avisar)", style="Card.TLabel").pack(side="left", padx=6)
        self.lbl_ultima = ttk.Label(a, text="", style="Dica.Card.TLabel")
        self.lbl_ultima.pack(anchor="w", pady=(12, 0))

        # ---- Lista
        lista = Card(area, "PDFs na pasta", "Clique duas vezes para abrir. Ctrl/Shift + clique seleciona vários.")
        lista.pack(fill="both", expand=True, pady=(14, 0))
        self.lbl_selecao = ttk.Label(lista.acoes, text="", style="Muted.Card.TLabel")
        self.lbl_selecao.pack(side="left")
        self.tabela = Tabela(lista.corpo, [
            ("nome", "Arquivo", 420, "w"), ("data", "Gerado em", 130, "center"),
            ("tamanho", "Tamanho", 90, "e"), ("situacao", "Situação", 170, "w"),
        ], altura=12, vazio="A pasta dos PDFs está vazia.")
        self.tabela.pack(fill="both", expand=True)
        self.tabela.chaves_ordenacao.update({
            "data": lambda v: datetime.strptime(v, "%d/%m/%Y %H:%M") if v else datetime.min,
            "tamanho": lambda v: self._bytes_de(v),
        })
        self.tabela.arvore.bind("<Double-1>", self._abrir)
        self.tabela.arvore.bind("<<TreeviewSelect>>", lambda e: self.atualizar_previa())

    # ---- Dados ----------------------------------------------------------------------------

    @staticmethod
    def _bytes_de(texto: str) -> float:
        try:
            numero, unidade = texto.replace(",", ".").split()
            return float(numero) * {"bytes": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}[unidade]
        except (ValueError, KeyError):
            return 0.0

    def ao_mostrar(self) -> None:
        pref = self.app.pref
        self.lbl_pasta.configure(text=f"Pasta: {config.PASTA_PDF}")
        self.arquivos = limpeza.listar_pdfs()
        r = limpeza.resumo(self.arquivos)
        self.k_qtd.definir(str(r["quantidade"]), "arquivos PDF")
        self.k_tam.definir(limpeza.formatar_bytes(r["bytes"]),
                           f"média {limpeza.formatar_bytes(r['bytes'] / r['quantidade'])}" if r["quantidade"] else "—")
        if r["mais_antigo"]:
            dias = (datetime.now() - r["mais_antigo"]).days
            self.k_antigo.definir(r["mais_antigo"].strftime("%d/%m/%Y"), f"há {dias} dia(s)")
        else:
            self.k_antigo.definir("—", "")
        self.k_prot.definir(str(r["protegidos"]), "protegidos da limpeza" if r["protegidos"] else "nenhum pendente",
                            T.AVISO if r["protegidos"] else T.TEXTO)
        self.lbl_ultima.configure(text=f"Última limpeza: {pref.ultima_limpeza}" if pref.ultima_limpeza
                                  else "Nenhuma limpeza feita ainda.")
        self.tabela.limpar()
        self._por_iid.clear()
        for i, a in enumerate(self.arquivos):
            iid = str(i)
            self._por_iid[iid] = a
            situacao = "⚠ Gerado, não anexado" if a.protegido else "✔ Gerado"
            self.tabela.inserir([a.nome, a.modificado.strftime("%d/%m/%Y %H:%M"),
                                 limpeza.formatar_bytes(a.tamanho), situacao], iid=iid,
                                tags=("protegido",) if a.protegido else ())
        self.tabela.atualizar_vazio()
        self.atualizar_previa()

    def _escolhidos(self) -> list[limpeza.ArquivoPdf] | None:
        criterio = self.var_criterio.get()
        proteger = self.var_proteger.get()
        try:
            if criterio == "selecionados":
                escolhidos = [self._por_iid[i] for i in self.tabela.selecionados() if i in self._por_iid]
                return [a for a in escolhidos if not (proteger and a.protegido)]
            if criterio == "mais_antigos":
                dias = int(self.var_dias.get() or 0)
                return limpeza.selecionar(self.arquivos, "mais_antigos", dias=dias, proteger=proteger)
            if criterio == "ate_data":
                ate = datetime.strptime(self.var_data.get().strip(), "%d/%m/%Y").date()
                return limpeza.selecionar(self.arquivos, "ate_data", ate=ate, proteger=proteger)
            return limpeza.selecionar(self.arquivos, "todos", proteger=proteger)
        except ValueError:
            return None

    def atualizar_previa(self) -> None:
        escolhidos = self._escolhidos()
        sel = len(self.tabela.selecionados())
        self.lbl_selecao.configure(text=f"{sel} selecionado(s)" if sel else "")
        marcados = {str(a.caminho) for a in (escolhidos or [])}
        for iid, a in self._por_iid.items():
            tags = [t for t in self.tabela.arvore.item(iid, "tags") if t != "apagar"]
            if str(a.caminho) in marcados:
                tags.append("apagar")
            self.tabela.arvore.item(iid, tags=tuple(tags))
        if escolhidos is None:
            self.lbl_previa.configure(text="Confira o número de dias ou a data (DD/MM/AAAA).", fg=T.ERRO)
            self.btn_limpar.state(["disabled"])
            return
        if not escolhidos:
            dica = " Selecione arquivos na lista." if self.var_criterio.get() == "selecionados" else ""
            self.lbl_previa.configure(text="Nenhum PDF se encaixa nessa escolha." + dica, fg=T.TEXTO_2)
            self.btn_limpar.state(["disabled"])
            return
        total = sum(a.tamanho for a in escolhidos)
        self.lbl_previa.configure(text=f"Serão removidos {len(escolhidos)} PDF(s) · {limpeza.formatar_bytes(total)}",
                                  fg=T.ERRO)
        self.btn_limpar.state(["!disabled"])

    # ---- Ações ----------------------------------------------------------------------------

    def limpar(self) -> None:
        escolhidos = self._escolhidos()
        if not escolhidos:
            return
        total = limpeza.formatar_bytes(sum(a.tamanho for a in escolhidos))
        lixeira = self.var_lixeira.get()
        destino = ("Eles irão para a Lixeira e podem ser recuperados." if lixeira
                   else "ATENÇÃO: eles serão apagados DE VEZ, sem passar pela Lixeira.")
        if not messagebox.askyesno(TITULO, f"Apagar {len(escolhidos)} PDF(s) ({total})?\n\n{destino}",
                                   icon="warning", parent=self):
            return
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            r = limpeza.apagar(escolhidos, lixeira=lixeira)
        finally:
            self.configure(cursor="")
        self.app.pref.ultima_limpeza = datetime.now().strftime("%d/%m/%Y %H:%M")
        preferencias.salvar(self.app.pref)
        if r.falhas:
            nomes = "\n".join(f"• {n}: {m}" for n, m in r.falhas[:8])
            messagebox.showwarning(TITULO, f"{r.apagados} PDF(s) removido(s). {len(r.falhas)} não puderam ser "
                                           f"apagados (talvez estejam abertos):\n\n{nomes}", parent=self)
        else:
            onde = "enviados para a Lixeira" if r.para_lixeira else "apagados"
            self.app.toast.mostrar(f"{r.apagados} PDF(s) {onde} · {limpeza.formatar_bytes(r.bytes_liberados)} liberados.")
        self.ao_mostrar()

    def _salvar_opcoes(self) -> None:
        pref = self.app.pref
        pref.usar_lixeira = self.var_lixeira.get()
        pref.proteger_nao_anexados = self.var_proteger.get()
        pref.limpeza_automatica = self.var_auto.get()
        try:
            pref.limpeza_dias = max(1, int(self.var_auto_dias.get()))
            pref.aviso_tamanho_mb = max(0, int(self.var_aviso.get()))
        except ValueError:
            return
        preferencias.salvar(pref)

    def alterar_pasta(self) -> None:
        nova = filedialog.askdirectory(parent=self, title="Escolha a pasta onde os PDFs serão salvos",
                                       initialdir=str(config.PASTA_PDF if config.PASTA_PDF.exists() else Path.home()))
        if not nova:
            return
        self.app.pref.pasta_pdf = nova
        preferencias.salvar(self.app.pref)
        preferencias.aplicar(self.app.pref)
        self.app.toast.mostrar("Pasta dos PDFs alterada. Os próximos DAREs serão salvos nela.")
        self.ao_mostrar()

    def abrir_pasta(self) -> None:
        config.PASTA_PDF.mkdir(parents=True, exist_ok=True)
        abrir_no_sistema(config.PASTA_PDF)

    def _abrir(self, _evento) -> None:
        sel = self.tabela.selecionados()
        if sel and sel[0] in self._por_iid:
            abrir_no_sistema(self._por_iid[sel[0]].caminho)
