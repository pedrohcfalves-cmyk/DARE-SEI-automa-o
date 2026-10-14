"""Página inicial: situação geral e atalhos para o que se faz no dia a dia."""

import tkinter as tk
from datetime import date
from tkinter import ttk

from ... import armazenamento, limpeza, navegador, utils
from .. import tema as T
from ..app import Pagina
from ..widgets import KPI, Banner, CabecalhoPagina, Card, Tabela


class PaginaInicio(Pagina):
    titulo = "Início"
    icone = "⌂"

    def __init__(self, app):
        super().__init__(app)
        cab = CabecalhoPagina(self, "Olá! O que vamos fazer hoje?",
                              "Gere o DARE avulso, salve o PDF e anexe no processo do SEI — em lotes ou a partir de uma planilha.")
        cab.pack(fill="x")
        ttk.Button(cab.acoes, text="Importar planilha", command=lambda: app.paginas["lancamentos"].importar_planilha()
                   ).pack(side="left", padx=(0, 8))
        ttk.Button(cab.acoes, text="＋  Novo lançamento", style="Primario.TButton",
                   command=app.ir_para_novo_lancamento).pack(side="left")

        self.avisos = ttk.Frame(self)
        self.avisos.pack(fill="x", pady=(14, 0))

        kpis = ttk.Frame(self)
        kpis.pack(fill="x", pady=(14, 0))
        self.k_nav = KPI(kpis, "Navegador")
        self.k_lista = KPI(kpis, "Lançamentos na lista")
        self.k_hoje = KPI(kpis, "Concluídos hoje")
        self.k_pdfs = KPI(kpis, "Pasta dos PDFs")
        for i, k in enumerate((self.k_nav, self.k_lista, self.k_hoje, self.k_pdfs)):
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            kpis.columnconfigure(i, weight=1, uniform="kpi")
        self.k_nav.bind("<Button-1>", lambda e: app.abrir_navegador())
        self.k_pdfs.bind("<Button-1>", lambda e: app.mostrar("arquivos"))

        baixo = ttk.Frame(self)
        baixo.pack(fill="both", expand=True, pady=(14, 0))
        baixo.columnconfigure(0, weight=3, uniform="b")
        baixo.columnconfigure(1, weight=2, uniform="b")
        baixo.rowconfigure(0, weight=1)

        recentes = Card(baixo, "Últimas execuções", "Os registros completos ficam em dados/historico.csv (abre no Excel).")
        recentes.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.tabela = Tabela(recentes.corpo, [
            ("quando", "Quando", 98, "w"), ("situacao", "Situação", 100, "w"),
            ("processo", "Processo", 156, "w"), ("servidor", "Servidor", 130, "w"), ("valor", "Valor (R$)", 84, "e"),
        ], altura=6, vazio="Nenhuma execução ainda.\nOs DAREs processados aparecem aqui.", selecao="browse")
        self.tabela.pack(fill="both", expand=True)

        passos = Card(baixo, "Como funciona")
        passos.grid(row=0, column=1, sticky="nsew")
        etapas = [
            ("1", "Adicione os lançamentos", "Digite cada um ou importe de uma planilha do Excel."),
            ("2", "Confira a lista", "Edite ou remova antes de começar. Os dados ficam guardados."),
            ("3", "Entre no DARE e no SEI", "Na primeira vez, faça o login nas abas que o programa abre."),
            ("4", "Acompanhe", "Cada lançamento: DARE → PDF → SEI. Se um falhar, o programa segue."),
        ]
        for numero, titulo, texto in etapas:
            linha = tk.Frame(passos.corpo, bg=T.SUPERFICIE)
            linha.pack(fill="x", pady=4)
            circulo = tk.Canvas(linha, width=28, height=28, bg=T.SUPERFICIE, highlightthickness=0)
            circulo.create_oval(1, 1, 27, 27, fill=T.PRIMARIA_CLARA, outline=T.PRIMARIA_CLARA)
            circulo.create_text(14, 14, text=numero, fill=T.PRIMARIA_TEXTO, font=T.F["negrito"])
            circulo.pack(side="left", anchor="n", padx=(0, 12))
            textos = tk.Frame(linha, bg=T.SUPERFICIE)
            textos.pack(side="left", fill="x", expand=True)
            ttk.Label(textos, text=titulo, style="Rotulo.Card.TLabel").pack(anchor="w")
            # largura fixa (e não acompanhando o cartão): evita um ciclo de redimensionamento no grid
            ttk.Label(textos, text=texto, style="Dica.Card.TLabel", wraplength=240, justify="left").pack(anchor="w")
        atalhos = tk.Frame(passos.corpo, bg=T.SUPERFICIE)
        atalhos.pack(fill="x", pady=(10, 0))
        ttk.Label(atalhos, text="Atalhos: Ctrl+N novo lançamento · Ctrl+I importar planilha · F5 atualizar",
                  style="Dica.Card.TLabel", wraplength=280, justify="left").pack(anchor="w")

    def ao_mostrar(self) -> None:
        app = self.app
        for w in self.avisos.winfo_children():
            w.destroy()
        if app.lotes and not app.executando:
            Banner(self.avisos, "info",
                   f"Há {len(app.lotes)} lançamento(s) na lista aguardando processamento "
                   "(digitados ou pendentes de uma execução anterior).",
                   [("Ver lista", lambda: app.mostrar("lancamentos"), "TButton")]).pack(fill="x", pady=(0, 8))
        qtd, tam = limpeza.tamanho_pasta()
        limite = app.pref.aviso_tamanho_mb
        if limite and tam > limite * 1024 ** 2:
            Banner(self.avisos, "aviso",
                   f"A pasta dos PDFs está com {limpeza.formatar_bytes(tam)} ({qtd} arquivos), acima do limite "
                   f"de {limite} MB que você definiu.",
                   [("Limpar agora", lambda: app.mostrar("arquivos"), "TButton")]).pack(fill="x", pady=(0, 8))
        if not navegador.localizar_chrome():
            Banner(self.avisos, "erro",
                   "Não encontrei o Google Chrome nem o Microsoft Edge. Instale o Chrome para usar a automação.",
                   []).pack(fill="x", pady=(0, 8))

        aberto = navegador.chrome_debug_ativo(timeout=0.2)
        exe = navegador.localizar_chrome()
        self.k_nav.definir("Aberto" if aberto else "Fechado",
                           navegador.nome_navegador(exe) if aberto else "clique para abrir",
                           T.SUCESSO if aberto else T.TEXTO_2)
        self.k_lista.definir(str(len(app.lotes)), "prontos para processar" if app.lotes else "lista vazia")
        historico = armazenamento.ler_historico(limite=500)
        hoje = date.today().strftime("%d/%m/%Y")
        do_dia = [h for h in historico if (h.get("data_hora") or "").startswith(hoje)]
        ok = sum(1 for h in do_dia if h.get("status") == "SUCESSO")
        erros = len(do_dia) - ok
        self.k_hoje.definir(str(ok), f"{erros} com erro" if erros else "nenhum erro",
                            T.SUCESSO if ok else T.TEXTO)
        self.k_pdfs.definir(limpeza.formatar_bytes(tam), f"{qtd} PDF(s) · gerenciar")

        self.tabela.limpar()
        rotulos = {"SUCESSO": ("✔ Concluído", ""), "ERRO": ("✖ Erro", "erro"),
                   "CANCELADO": ("■ Cancelado", "aviso")}
        for h in historico[:12]:
            texto, tag = rotulos.get(h.get("status", ""), (h.get("status", ""), ""))
            quando = h.get("data_hora", "")
            quando = f"{quando[:5]} {quando[11:16]}" if len(quando) >= 16 else quando
            self.tabela.inserir([quando, texto, h.get("processo", ""),
                                 h.get("servidor", "") or utils.formatar_cpf(h.get("cpf", "")),
                                 h.get("valor", "")], tags=(tag,))
        self.tabela.atualizar_vazio()
