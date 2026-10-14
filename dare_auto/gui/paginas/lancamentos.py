"""Página Lançamentos: digitar, importar, conferir e iniciar o processamento."""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from ... import armazenamento, config, menu, utils
from ...modelos import DadosDare
from .. import tema as T
from ..app import TITULO, Pagina
from ..widgets import Banner, CabecalhoPagina, Card, Campo, Dica, Rolavel, Tabela


# ---- Validações (mesmas regras do modo terminal) -------------------------------------------

def _documento(nome: str, digitos: int, validador):
    def validar(texto: str) -> str:
        d = utils.somente_digitos(texto)
        if not d:
            raise ValueError("Campo obrigatório.")
        if len(d) != digitos:
            raise ValueError(f"O {nome} deve ter {digitos} dígitos (tem {len(d)}).")
        if not validador(d):
            raise ValueError(f"{nome} inválido: os dígitos verificadores não conferem.")
        return d
    return validar


def _obrigatorio(funcao):
    def validar(texto: str):
        if not texto.strip():
            raise ValueError("Campo obrigatório.")
        return funcao(texto)
    return validar


def _vencimento(texto: str):
    texto = texto.strip()
    if not texto:
        raise ValueError("Campo obrigatório.")
    d = utils.somente_digitos(texto)
    if len(d) == 8 and "/" not in texto:
        texto = f"{d[:2]}/{d[2:4]}/{d[4:]}"
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError("Data inválida. Use DD/MM/AAAA (ex.: 10/11/2026).")


def _valor(texto: str) -> str:
    if not texto.strip():
        raise ValueError("Campo obrigatório.")
    try:
        return utils.formatar_valor(texto)
    except ValueError as exc:
        raise ValueError(str(exc).replace("Exemplo", "Ex.")) from exc


class PaginaLancamentos(Pagina):
    titulo = "Lançamentos"
    icone = "☰"

    def __init__(self, app):
        super().__init__(app)
        self.editando: int | None = None

        cab = CabecalhoPagina(self, "Lançamentos",
                              "Cada lançamento gera um DARE, salva o PDF e o anexa no processo do SEI.")
        cab.pack(fill="x")
        self.btn_importar = ttk.Button(cab.acoes, text="Importar planilha…", command=self.importar_planilha)
        self.btn_importar.pack(side="left", padx=(0, 8))
        self.btn_iniciar = ttk.Button(cab.acoes, text="▶  Iniciar processamento", style="Primario.TButton",
                                      command=self.iniciar)
        self.btn_iniciar.pack(side="left")

        self.area_aviso = ttk.Frame(self)
        self.area_aviso.pack(fill="x")

        corpo = ttk.Frame(self)
        corpo.pack(fill="both", expand=True, pady=(14, 0))
        corpo.columnconfigure(1, weight=1)
        corpo.rowconfigure(0, weight=1)

        # ---- Formulário
        self.form = Card(corpo, "Novo lançamento", "Campos com * são obrigatórios. Enter adiciona.")
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        corpo.columnconfigure(0, minsize=392)
        self.titulo_form = self.form.lbl_titulo
        # Botões presos embaixo do cartão: sempre visíveis, mesmo em telas baixas.
        botoes = tk.Frame(self.form.corpo, bg=T.SUPERFICIE)
        botoes.pack(side="bottom", fill="x", pady=(12, 0))
        self.btn_salvar = ttk.Button(botoes, text="＋  Adicionar à lista", style="Primario.TButton",
                                     command=self.salvar)
        self.btn_salvar.pack(side="left", fill="x", expand=True)
        self.btn_cancelar = ttk.Button(botoes, text="Limpar", command=self.cancelar_edicao)
        self.btn_cancelar.pack(side="left", padx=(8, 0))
        rol = Rolavel(self.form.corpo, fundo=T.SUPERFICIE)
        rol.pack(fill="both", expand=True)
        f = rol.interno
        self.c_processo = Campo(f, "Processo SEI", "Ex.: 0012.123456/2026-12",
                                validar=_obrigatorio(utils.validar_processo))
        self.c_processo.pack(fill="x")
        self.c_cpf = Campo(f, "CPF do servidor", "11 dígitos, com ou sem pontos",
                           validar=_documento("CPF", 11, utils.validar_cpf), exibir=utils.formatar_cpf)
        self.c_cpf.pack(fill="x", pady=(6, 0))
        self.c_cnpj = Campo(f, "CNPJ do órgão", "Identifica o contribuinte no DARE",
                            validar=_documento("CNPJ", 14, utils.validar_cnpj), exibir=utils.formatar_cnpj)
        self.c_cnpj.pack(fill="x", pady=(6, 0))
        self.var_mesmo = tk.BooleanVar(value=False)
        self.chk_mesmo = ttk.Checkbutton(f, text="Recolhedor é o mesmo CNPJ do órgão", variable=self.var_mesmo,
                                         command=self._espelhar_recolhedor)
        self.chk_mesmo.pack(anchor="w")
        self.c_recolhedor = Campo(f, "CNPJ do recolhedor", "",
                                  validar=_documento("CNPJ", 14, utils.validar_cnpj), exibir=utils.formatar_cnpj)
        self.c_recolhedor.pack(fill="x")
        tres = tk.Frame(f, bg=T.SUPERFICIE)
        tres.pack(fill="x", pady=(6, 0))
        for i in range(3):
            tres.columnconfigure(i, weight=1, uniform="t")
        self.c_ref = Campo(tres, "Referência", "MMAAAA",
                           validar=_obrigatorio(utils.validar_mes_ano), exibir=utils.formatar_mes_ano, largura=6)
        self.c_venc = Campo(tres, "Vencimento", "DD/MM/AAAA",
                            validar=_vencimento, exibir=lambda d: d.strftime("%d/%m/%Y"), largura=7)
        self.c_valor = Campo(tres, "Valor (R$)", "Ex.: 7.273,07", validar=_valor, largura=6)
        for i, c in enumerate((self.c_ref, self.c_venc, self.c_valor)):
            c.grid(row=0, column=i, sticky="new", padx=(0 if i == 0 else 4, 0 if i == 2 else 4))
            c.dica.configure(wraplength=110, justify="left")
        Dica(self.c_venc.entrada, "Padrão: 1 mês à frente, em dia útil (sem contar feriados).")
        Dica(self.c_valor.entrada, "A vírgula é colocada automaticamente no site. 7.243 = sete mil duzentos e quarenta e três.")
        self.campos = [self.c_processo, self.c_cpf, self.c_cnpj, self.c_recolhedor, self.c_ref,
                       self.c_venc, self.c_valor]
        self.c_cnpj.var.trace_add("write", lambda *a: self._espelhar_recolhedor())
        fixos = (f"Valores fixos: {config.ORGAO.split(' - ')[0]} · receita {config.CODIGO_RECEITA} · "
                 f"UG {config.UNIDADE_GESTORA} / gestão {config.GESTAO} · série SEI {config.SERIE_SEI}")
        ttk.Label(f, text=fixos, style="Dica.Card.TLabel", wraplength=330, justify="left").pack(anchor="w", pady=(10, 0))
        for c in self.campos:
            c.entrada.bind("<Return>", lambda e: self.salvar())
            c.entrada.bind("<KP_Enter>", lambda e: self.salvar())
            c.entrada.bind("<Escape>", lambda e: self.cancelar_edicao())

        # ---- Lista
        lista = Card(corpo, "Lista para processar", "Clique duas vezes para editar · Delete remove · "
                     "clique no título da coluna para ordenar.")
        lista.grid(row=0, column=1, sticky="nsew")
        barra = tk.Frame(lista.corpo, bg=T.SUPERFICIE)
        barra.pack(fill="x", pady=(0, 8))
        self.btn_editar = ttk.Button(barra, text="✎ Editar", style="Pequeno.TButton", command=self.editar_selecionado)
        self.btn_duplicar = ttk.Button(barra, text="⧉ Duplicar", style="Pequeno.TButton", command=self.duplicar)
        self.btn_remover = ttk.Button(barra, text="✕ Remover", style="Pequeno.TButton", command=self.remover)
        self.btn_limpar = ttk.Button(barra, text="Esvaziar lista", style="Pequeno.TButton", command=self.esvaziar)
        for b in (self.btn_editar, self.btn_duplicar, self.btn_remover):
            b.pack(side="left", padx=(0, 6))
        self.btn_limpar.pack(side="right")
        self.tabela = Tabela(lista.corpo, [
            ("n", "#", 34, "e"), ("processo", "Processo SEI", 152, "w"), ("cpf", "CPF", 110, "w"),
            ("ref", "Ref.", 58, "center"), ("venc", "Vencimento", 86, "center"),
            ("valor", "Valor (R$)", 86, "e"), ("origem", "Origem", 64, "w"),
        ], altura=12, vazio="Nenhum lançamento ainda.\n\nPreencha o formulário ao lado e clique em "
                            "“Adicionar à lista”, ou importe uma planilha do Excel.")
        self.tabela.pack(fill="both", expand=True)
        self.tabela.chaves_ordenacao.update({
            "n": int, "valor": lambda v: int(utils.valor_para_digitos(v) or 0),
            "venc": lambda v: datetime.strptime(v, "%d/%m/%Y") if v else datetime.min,
        })
        self.tabela.arvore.bind("<Double-1>", lambda e: self.editar_selecionado())
        self.tabela.arvore.bind("<Delete>", lambda e: self.remover())
        self.tabela.arvore.bind("<<TreeviewSelect>>", lambda e: self._estado_botoes())
        self.avisos = tk.Frame(lista.corpo, bg=T.SUPERFICIE)
        self.avisos.pack(fill="x", pady=(8, 0))
        self.totais = ttk.Label(lista.corpo, text="", style="Muted.Card.TLabel")
        self.totais.pack(anchor="e", pady=(6, 0))

        self.novo(focar=False)

    # ---- Formulário -----------------------------------------------------------------------

    def _espelhar_recolhedor(self) -> None:
        if self.var_mesmo.get():
            self.c_recolhedor.var.set(self.c_cnpj.var.get())
            self.c_recolhedor.entrada.state(["disabled"])
            self.c_recolhedor.limpar_erro()
        else:
            self.c_recolhedor.entrada.state(["!disabled"])

    def _base(self) -> DadosDare | None:
        return self.app.lotes[-1] if self.app.lotes else armazenamento.carregar_ultimos()

    def novo(self, focar: bool = True) -> None:
        """Formulário em branco, com CNPJ, recolhedor, referência, vencimento e valor do anterior."""
        self.editando = None
        base = self._base()
        for c in self.campos:
            c.definir("")
        if base:
            self.c_cnpj.definir(base.cnpj)
            self.c_recolhedor.definir(base.cnpj_recolhedor)
            self.c_ref.definir(base.mes_ano_referencia)
            self.c_valor.definir(base.valor)
            self.var_mesmo.set(utils.somente_digitos(base.cnpj) == utils.somente_digitos(base.cnpj_recolhedor))
        else:
            self.c_valor.definir(config.VALOR_PADRAO)
            self.var_mesmo.set(True)
        venc = self.app.lotes[-1].vencimento if self.app.lotes else utils.vencimento_padrao()
        self.c_venc.definir(venc)
        self._espelhar_recolhedor()
        self.titulo_form.configure(text="Novo lançamento")
        self.btn_salvar.configure(text="＋  Adicionar à lista")
        self.btn_cancelar.configure(text="Limpar")
        if focar:
            self.c_processo.focar()

    def _ler_formulario(self) -> DadosDare | None:
        valores = [c.conferir() for c in self.campos]
        if any(v is None for v in valores):
            primeiro = next(c for c, v in zip(self.campos, valores) if v is None)
            primeiro.focar()
            return None
        processo, cpf, cnpj, recolhedor, ref, venc, valor = valores
        return DadosDare(processo, cnpj, cpf, recolhedor, ref, venc, valor)

    def salvar(self) -> None:
        if self.app.executando:
            return
        dados = self._ler_formulario()
        if dados is None:
            self.app.toast.mostrar("Corrija os campos destacados em vermelho.", "erro")
            return
        if self.editando is not None and self.editando < len(self.app.lotes):
            dados.origem = self.app.lotes[self.editando].origem
            self.app.lotes[self.editando] = dados
            n = self.editando + 1
            self.app.toast.mostrar(f"Lançamento {n} atualizado.")
        else:
            self.app.lotes.append(dados)
            n = len(self.app.lotes)
            self.app.toast.mostrar(f"Lançamento {n} adicionado. Preencha o próximo.")
        self.app.lotes_alterados()
        self.atualizar_lista(selecionar=n - 1)
        self.novo()

    def cancelar_edicao(self) -> None:
        self.novo()

    def editar(self, indice: int) -> None:
        if self.app.executando or not 0 <= indice < len(self.app.lotes):
            return
        d = self.app.lotes[indice]
        self.editando = indice
        self.c_processo.definir(d.processo)
        self.c_cpf.definir(d.cpf)
        self.c_cnpj.definir(d.cnpj)
        self.var_mesmo.set(utils.somente_digitos(d.cnpj) == utils.somente_digitos(d.cnpj_recolhedor))
        self.c_recolhedor.definir(d.cnpj_recolhedor)
        self._espelhar_recolhedor()
        self.c_ref.definir(d.mes_ano_referencia)
        self.c_venc.definir(d.vencimento)
        self.c_valor.definir(d.valor)
        self.titulo_form.configure(text=f"Editando o lançamento {indice + 1}" + (f" ({d.origem})" if d.origem else ""))
        self.btn_salvar.configure(text="✔  Salvar alterações")
        self.btn_cancelar.configure(text="Cancelar")
        self.c_processo.focar()

    # ---- Lista ----------------------------------------------------------------------------

    def _indices_selecionados(self) -> list[int]:
        return sorted(int(i) for i in self.tabela.selecionados())

    def editar_selecionado(self) -> None:
        sel = self._indices_selecionados()
        if sel:
            self.editar(sel[0])

    def duplicar(self) -> None:
        sel = self._indices_selecionados()
        if not sel or self.app.executando:
            return
        original = self.app.lotes[sel[0]]
        copia = DadosDare(**{**original.para_dict(), "vencimento": original.vencimento, "origem": ""})
        self.app.lotes.insert(sel[0] + 1, copia)
        self.app.lotes_alterados()
        self.atualizar_lista()
        self.editar(sel[0] + 1)
        self.app.toast.mostrar("Cópia criada logo abaixo. Ajuste o processo e o CPF.", "info")

    def remover(self) -> None:
        sel = self._indices_selecionados()
        if not sel or self.app.executando:
            return
        texto = (f"Remover o lançamento {sel[0] + 1} ({self.app.lotes[sel[0]].processo})?" if len(sel) == 1
                 else f"Remover os {len(sel)} lançamentos selecionados?")
        if not messagebox.askyesno(TITULO, texto, parent=self):
            return
        for i in reversed(sel):
            del self.app.lotes[i]
        if self.editando is not None:
            self.novo(focar=False)
        self.app.lotes_alterados()
        self.atualizar_lista()
        self.app.toast.mostrar(f"{len(sel)} lançamento(s) removido(s).", "info")

    def esvaziar(self) -> None:
        if not self.app.lotes or self.app.executando:
            return
        if not messagebox.askyesno(TITULO, f"Remover TODOS os {len(self.app.lotes)} lançamentos da lista?\n\n"
                                           "Os PDFs e o histórico não são afetados.", icon="warning", parent=self):
            return
        self.app.lotes.clear()
        self.app.lotes_alterados()
        self.atualizar_lista()
        self.novo()

    def atualizar_lista(self, selecionar: int | None = None) -> None:
        self.tabela.limpar()
        total_centavos = 0
        for i, d in enumerate(self.app.lotes):
            self.tabela.inserir([i + 1, d.processo, utils.formatar_cpf(d.cpf),
                                 utils.formatar_mes_ano(d.mes_ano_referencia),
                                 d.vencimento.strftime("%d/%m/%Y"), d.valor, d.origem or "digitado"], iid=str(i))
            try:
                total_centavos += int(d.valor_digitos)
            except ValueError:
                pass
        self.tabela.atualizar_vazio()
        if selecionar is not None and str(selecionar) in self.tabela.arvore.get_children():
            self.tabela.arvore.selection_set(str(selecionar))
            self.tabela.arvore.see(str(selecionar))
        n = len(self.app.lotes)
        reais = utils.formatar_valor(f"{total_centavos / 100:.2f}".replace(".", ",")) if total_centavos else "0,00"
        self.totais.configure(text=f"{n} lançamento(s) · total R$ {reais}" if n else "")
        for w in self.avisos.winfo_children():
            w.destroy()
        avisos = menu._avisos_lotes(self.app.lotes)
        for texto in avisos[:5]:
            tk.Label(self.avisos, text=f"⚠  {texto}", bg=T.AVISO_CLARO, fg="#78350F", font=T.F["pequena"],
                     anchor="w", justify="left", padx=10, pady=4, wraplength=620).pack(fill="x", pady=1)
        if len(avisos) > 5:
            tk.Label(self.avisos, text=f"… e mais {len(avisos) - 5} aviso(s).", bg=T.SUPERFICIE, fg=T.AVISO,
                     font=T.F["pequena"]).pack(anchor="w")
        self._estado_botoes()

    def _estado_botoes(self) -> None:
        rodando = self.app.executando
        sel = self.tabela.selecionados()
        n = len(self.app.lotes)
        def estado(botao, ativo):
            botao.state(["!disabled"] if ativo else ["disabled"])
        estado(self.btn_editar, len(sel) == 1 and not rodando)
        estado(self.btn_duplicar, len(sel) == 1 and not rodando)
        estado(self.btn_remover, bool(sel) and not rodando)
        estado(self.btn_limpar, n > 0 and not rodando)
        estado(self.btn_iniciar, n > 0 and not rodando)
        estado(self.btn_importar, not rodando)
        estado(self.btn_salvar, not rodando)
        self.btn_iniciar.configure(text=f"▶  Iniciar processamento ({n})" if n else "▶  Iniciar processamento")

    def ao_mostrar(self) -> None:
        for w in self.area_aviso.winfo_children():
            w.destroy()
        if self.app.executando:
            Banner(self.area_aviso, "info", "Há um processamento em andamento: a lista fica bloqueada até ele terminar.",
                   [("Acompanhar", lambda: self.app.mostrar("execucao"), "TButton")]).pack(fill="x", pady=(14, 0))
        if self.editando is None and not self.c_processo.texto() and not self.c_cpf.texto():
            self.novo(focar=False)  # formulário intocado: atualiza os padrões (ex.: lista recuperada)
        self.atualizar_lista()

    # ---- Ações principais -----------------------------------------------------------------

    def importar_planilha(self) -> None:
        if self.app.executando:
            self.app.toast.mostrar("Aguarde o processamento atual terminar.", "aviso")
            return
        from ..dialogo_planilha import DialogoPlanilha
        self.app.mostrar("lancamentos")
        lotes = DialogoPlanilha.abrir(self.app)
        if not lotes:
            return
        if self.app.lotes:
            resposta = messagebox.askyesnocancel(
                TITULO, f"A lista já tem {len(self.app.lotes)} lançamento(s).\n\n"
                        f"Sim: ACRESCENTAR os {len(lotes)} da planilha no fim da lista.\n"
                        "Não: SUBSTITUIR a lista pelos da planilha.", parent=self)
            if resposta is None:
                return
            if not resposta:
                self.app.lotes.clear()
        self.app.lotes.extend(lotes)
        self.app.lotes_alterados()
        self.atualizar_lista()
        self.novo(focar=False)
        self.app.toast.mostrar(f"{len(lotes)} lançamento(s) importado(s) da planilha. Confira e clique em Iniciar.")

    def iniciar(self) -> None:
        lotes = self.app.lotes
        if not lotes or self.app.executando:
            return
        if self.editando is not None or self.c_processo.texto():
            if not messagebox.askyesno(TITULO, "Há dados no formulário que ainda não foram adicionados à lista.\n\n"
                                               "Iniciar mesmo assim (sem eles)?", parent=self):
                return
        avisos = menu._avisos_lotes(lotes)
        texto = (f"Processar {len(lotes)} lançamento(s) agora?\n\n"
                 "Para cada um, o programa gera o DARE, salva o PDF e anexa no SEI, usando o navegador "
                 "aberto por ele. Evite mexer nas abas do DARE e do SEI enquanto ele trabalha.")
        if avisos:
            texto += f"\n\nAtenção: há {len(avisos)} aviso(s) na lista (ex.: {avisos[0]})"
        if messagebox.askyesno(TITULO, texto, parent=self):
            self.app.iniciar_execucao(lotes)
