"""
Identidade visual do aplicativo: cores, fontes e estilos ttk.

Regras seguidas (UI/UX):
  • contraste de texto >= 4,5:1 (WCAG AA) em todas as combinações usadas;
  • uma única cor de destaque (azul) para a ação principal de cada tela;
  • cores de estado consistentes: verde = sucesso, âmbar = atenção, vermelho = erro/ação destrutiva;
  • espaçamento em múltiplos de 4 px e alvos de clique com pelo menos ~32 px de altura.
"""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# ---- Cores (tokens) -----------------------------------------------------------------------
FUNDO = "#F3F5F9"          # fundo da janela
SUPERFICIE = "#FFFFFF"     # cartões
SUPERFICIE_2 = "#F8FAFC"   # áreas internas, cabeçalho de tabelas
BORDA = "#DDE3EC"
BORDA_FORTE = "#C3CCD9"
TEXTO = "#0F172A"          # 17,4:1 no branco
TEXTO_2 = "#475569"        # 7,6:1 no branco
TEXTO_3 = "#5B6B82"        # 5,5:1 no branco (dicas)

PRIMARIA = "#1D4ED8"       # 6,7:1 com texto branco
PRIMARIA_HOVER = "#1E40AF"
PRIMARIA_CLARA = "#DBEAFE"
PRIMARIA_TEXTO = "#1E3A8A"

SUCESSO = "#15803D"
SUCESSO_CLARO = "#DCFCE7"
AVISO = "#B45309"
AVISO_CLARO = "#FEF3C7"
ERRO = "#B91C1C"
ERRO_CLARO = "#FEE2E2"
PERIGO = "#DC2626"
PERIGO_HOVER = "#B91C1C"

LATERAL = "#0F1E3A"        # barra lateral (azul-marinho)
LATERAL_ITEM_ATIVO = "#1C335E"
LATERAL_TEXTO = "#C7D2E3"  # 10:1 no azul-marinho
LATERAL_TEXTO_3 = "#8FA0BC"
LATERAL_DESTAQUE = "#60A5FA"

# Séries de gráficos (distinguíveis também por quem tem daltonismo comum)
SERIES = ["#2563EB", "#EA580C", "#059669", "#9333EA", "#DB2777", "#0891B2"]

FAMILIA = "Segoe UI"
FAMILIA_MONO = "Consolas"
F = {}  # fontes nomeadas, preenchidas em aplicar()


def _familia_disponivel(raiz: tk.Misc, preferidas: list[str]) -> str:
    existentes = {f.lower() for f in tkfont.families(raiz)}
    for nome in preferidas:
        if nome.lower() in existentes:
            return nome
    return "TkDefaultFont"


_IMAGENS: dict[str, tk.PhotoImage] = {}  # referências: sem elas o Tk descarta as imagens


def _indicadores(raiz: tk.Tk, s: ttk.Style) -> None:
    """Caixas de seleção e botões de opção desenhados (o padrão do tema 'clam' mostra um X)."""
    from .imagens import IMAGENS
    try:
        escala = float(raiz.tk.call("tk", "scaling"))
    except (tk.TclError, ValueError):
        escala = 1.33
    tam = 24 if escala >= 1.7 else 16
    for chave, dados in IMAGENS.items():
        if chave.endswith(f"_{tam}"):
            _IMAGENS[chave[: -len(f"_{tam}")]] = tk.PhotoImage(master=raiz, data=dados)
    for tipo, elemento, classe in (("check", "Caixa.indicator", "Checkbutton"),
                                   ("radio", "Opcao.indicator", "Radiobutton")):
        try:
            s.element_create(elemento, "image", _IMAGENS[f"{tipo}_off"],
                             ("selected", "disabled", _IMAGENS[f"{tipo}_on_dis"]),
                             ("disabled", _IMAGENS[f"{tipo}_off_dis"]),
                             ("selected", _IMAGENS[f"{tipo}_on"]), sticky="w", width=tam + 8)
        except tk.TclError:  # já criado (segunda janela no mesmo processo)
            pass
        s.layout(f"T{classe}", [(f"{classe}.padding", {"sticky": "nswe", "children": [
            (elemento, {"side": "left", "sticky": ""}),
            (f"{classe}.focus", {"side": "left", "sticky": "w", "children": [
                (f"{classe}.label", {"sticky": "nswe"})]})]})])


def aplicar(raiz: tk.Tk) -> None:
    """Define fontes e estilos. Chamar uma vez, logo depois de criar a janela."""
    global FAMILIA, FAMILIA_MONO
    FAMILIA = _familia_disponivel(raiz, ["Segoe UI", "Inter", "Helvetica Neue", "DejaVu Sans", "Arial"])
    FAMILIA_MONO = _familia_disponivel(raiz, ["Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"])
    semibold = _familia_disponivel(raiz, ["Segoe UI Semibold", FAMILIA])
    F.update({
        "base": (FAMILIA, 10),
        "pequena": (FAMILIA, 9),
        "negrito": (FAMILIA, 10, "bold"),
        "titulo": (semibold, 18, "bold" if semibold == FAMILIA else "normal"),
        "subtitulo": (FAMILIA, 10),
        "h2": (semibold, 12, "bold" if semibold == FAMILIA else "normal"),
        "kpi": (semibold, 20, "bold" if semibold == FAMILIA else "normal"),
        "marca": (semibold, 12, "bold" if semibold == FAMILIA else "normal"),
        "mono": (FAMILIA_MONO, 9),
        "nav": (FAMILIA, 10),
        "icone": (FAMILIA, 12),
    })
    padrao = tkfont.nametofont("TkDefaultFont")
    padrao.configure(family=FAMILIA, size=10)
    for nome in ("TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(nome).configure(family=FAMILIA, size=10)
        except tk.TclError:
            pass
    raiz.configure(background=FUNDO)
    raiz.option_add("*TCombobox*Listbox.font", F["base"])
    raiz.option_add("*TCombobox*Listbox.selectBackground", PRIMARIA_CLARA)
    raiz.option_add("*TCombobox*Listbox.selectForeground", TEXTO)

    s = ttk.Style(raiz)
    s.theme_use("clam")
    s.configure(".", background=FUNDO, foreground=TEXTO, font=F["base"], bordercolor=BORDA,
                focuscolor=PRIMARIA, troughcolor=SUPERFICIE_2, lightcolor=SUPERFICIE, darkcolor=BORDA)

    # Estruturas
    s.configure("TFrame", background=FUNDO)
    s.configure("Card.TFrame", background=SUPERFICIE)
    s.configure("Interno.TFrame", background=SUPERFICIE_2)
    s.configure("TLabel", background=FUNDO, foreground=TEXTO)
    s.configure("Titulo.TLabel", font=F["titulo"], background=FUNDO)
    s.configure("Subtitulo.TLabel", font=F["subtitulo"], foreground=TEXTO_2, background=FUNDO)
    s.configure("Card.TLabel", background=SUPERFICIE)
    s.configure("H2.Card.TLabel", background=SUPERFICIE, font=F["h2"])
    s.configure("Muted.Card.TLabel", background=SUPERFICIE, foreground=TEXTO_2)
    s.configure("Dica.Card.TLabel", background=SUPERFICIE, foreground=TEXTO_3, font=F["pequena"])
    s.configure("Erro.Card.TLabel", background=SUPERFICIE, foreground=ERRO, font=F["pequena"])
    s.configure("KPI.Card.TLabel", background=SUPERFICIE, font=F["kpi"])
    s.configure("Rotulo.Card.TLabel", background=SUPERFICIE, font=F["negrito"])
    s.configure("Interno.TLabel", background=SUPERFICIE_2, foreground=TEXTO_2)

    # Botões
    base_botao = {"padding": (14, 7), "font": F["negrito"], "borderwidth": 1, "focusthickness": 2}
    s.configure("TButton", background=SUPERFICIE, foreground=TEXTO, bordercolor=BORDA_FORTE,
                lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, **base_botao)
    s.map("TButton",
          background=[("disabled", SUPERFICIE_2), ("pressed", "#E2E8F0"), ("active", "#EEF2F7")],
          foreground=[("disabled", "#94A3B8")],
          bordercolor=[("focus", PRIMARIA)])
    s.configure("Primario.TButton", background=PRIMARIA, foreground="#FFFFFF", bordercolor=PRIMARIA,
                lightcolor=PRIMARIA, darkcolor=PRIMARIA, **base_botao)
    s.map("Primario.TButton",
          background=[("disabled", "#93A9D8"), ("pressed", "#1E3A8A"), ("active", PRIMARIA_HOVER)],
          bordercolor=[("disabled", "#93A9D8"), ("focus", "#0B2A7A")],
          lightcolor=[("active", PRIMARIA_HOVER)], darkcolor=[("active", PRIMARIA_HOVER)],
          foreground=[("disabled", "#EEF2FF")])
    s.configure("Perigo.TButton", background=PERIGO, foreground="#FFFFFF", bordercolor=PERIGO,
                lightcolor=PERIGO, darkcolor=PERIGO, **base_botao)
    s.map("Perigo.TButton",
          background=[("disabled", "#F1A9A9"), ("pressed", "#991B1B"), ("active", PERIGO_HOVER)],
          bordercolor=[("disabled", "#F1A9A9"), ("focus", "#7F1D1D")],
          foreground=[("disabled", "#FFF5F5")])
    s.configure("PerigoContorno.TButton", background=SUPERFICIE, foreground=ERRO, bordercolor="#F3B4B4",
                lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, **base_botao)
    s.map("PerigoContorno.TButton", background=[("disabled", SUPERFICIE_2), ("active", ERRO_CLARO)],
          foreground=[("disabled", "#94A3B8")])
    s.configure("Link.TButton", background=SUPERFICIE, foreground=PRIMARIA, borderwidth=0,
                padding=(2, 2), font=F["negrito"], lightcolor=SUPERFICIE, darkcolor=SUPERFICIE,
                bordercolor=SUPERFICIE)
    s.map("Link.TButton", foreground=[("active", PRIMARIA_HOVER), ("disabled", "#94A3B8")],
          background=[("active", SUPERFICIE)])
    s.configure("Pequeno.TButton", padding=(10, 4), font=F["pequena"])

    # Campos
    s.configure("TEntry", padding=(8, 6), fieldbackground=SUPERFICIE, bordercolor=BORDA_FORTE,
                lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, insertcolor=TEXTO)
    s.map("TEntry", bordercolor=[("focus", PRIMARIA), ("invalid", ERRO)],
          lightcolor=[("focus", PRIMARIA)], fieldbackground=[("disabled", SUPERFICIE_2), ("readonly", SUPERFICIE_2)])
    s.configure("Erro.TEntry", padding=(8, 6), fieldbackground="#FFF7F7", bordercolor=ERRO,
                lightcolor=ERRO, darkcolor=ERRO)
    s.configure("TCombobox", padding=(8, 5), fieldbackground=SUPERFICIE, bordercolor=BORDA_FORTE,
                arrowcolor=TEXTO_2, lightcolor=SUPERFICIE, darkcolor=SUPERFICIE)
    s.map("TCombobox", bordercolor=[("focus", PRIMARIA)],
          fieldbackground=[("readonly", SUPERFICIE), ("disabled", SUPERFICIE_2)],
          selectbackground=[("readonly", SUPERFICIE)], selectforeground=[("readonly", TEXTO)])
    s.configure("TSpinbox", padding=(8, 5), fieldbackground=SUPERFICIE, bordercolor=BORDA_FORTE,
                arrowcolor=TEXTO_2, lightcolor=SUPERFICIE, darkcolor=SUPERFICIE)
    s.map("TSpinbox", bordercolor=[("focus", PRIMARIA)])
    for nome in ("TCheckbutton", "TRadiobutton"):
        s.configure(nome, background=SUPERFICIE, foreground=TEXTO, focuscolor=PRIMARIA,
                    indicatorbackground=SUPERFICIE, indicatorforeground=PRIMARIA, padding=(2, 4))
        s.map(nome, background=[("active", SUPERFICIE)],
              indicatorbackground=[("selected", PRIMARIA_CLARA), ("active", "#EEF2F7")],
              foreground=[("disabled", "#94A3B8")])

    _indicadores(raiz, s)
    s.configure("Fundo.TCheckbutton", background=FUNDO)
    s.map("Fundo.TCheckbutton", background=[("active", FUNDO)])

    # Tabelas
    s.configure("Treeview", background=SUPERFICIE, fieldbackground=SUPERFICIE, foreground=TEXTO,
                rowheight=30, bordercolor=BORDA, borderwidth=0, font=F["base"])
    s.map("Treeview", background=[("selected", PRIMARIA_CLARA)], foreground=[("selected", TEXTO)])
    s.configure("Treeview.Heading", background=SUPERFICIE_2, foreground=TEXTO_2, font=F["negrito"],
                relief="flat", padding=(8, 6), bordercolor=BORDA)
    s.map("Treeview.Heading", background=[("active", "#EEF2F7")])
    s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    # Abas, barras de progresso e rolagem
    s.configure("TNotebook", background=FUNDO, borderwidth=0, tabmargins=(0, 0, 0, 0))
    s.configure("TNotebook.Tab", background=FUNDO, foreground=TEXTO_2, padding=(16, 8),
                font=F["negrito"], borderwidth=0)
    s.map("TNotebook.Tab", background=[("selected", SUPERFICIE), ("active", "#E8EDF5")],
          foreground=[("selected", PRIMARIA_TEXTO)], expand=[("selected", (0, 0, 0, 0))])
    s.configure("Horizontal.TProgressbar", troughcolor="#E5EAF2", background=PRIMARIA,
                bordercolor="#E5EAF2", lightcolor=PRIMARIA, darkcolor=PRIMARIA, thickness=10)
    s.configure("Sucesso.Horizontal.TProgressbar", troughcolor="#E5EAF2", background=SUCESSO,
                bordercolor="#E5EAF2", lightcolor=SUCESSO, darkcolor=SUCESSO, thickness=10)
    s.configure("Vertical.TScrollbar", background=SUPERFICIE_2, troughcolor=SUPERFICIE,
                bordercolor=SUPERFICIE, arrowcolor=TEXTO_3, lightcolor=SUPERFICIE_2, darkcolor=SUPERFICIE_2,
                gripcount=0, arrowsize=12)
    s.map("Vertical.TScrollbar", background=[("active", "#D5DCE6")])
    s.configure("TSeparator", background=BORDA)
