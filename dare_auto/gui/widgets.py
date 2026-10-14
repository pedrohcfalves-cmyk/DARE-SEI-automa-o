"""Componentes visuais reutilizáveis: cartões, avisos, campos com validação, tabelas e gráficos."""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable

from . import tema as T


# ---- Utilidades ---------------------------------------------------------------------------

def abrir_no_sistema(caminho: str | Path) -> bool:
    """Abre arquivo ou pasta com o programa padrão do sistema."""
    caminho = str(caminho)
    try:
        if os.name == "nt":
            os.startfile(caminho)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:  # noqa: BLE001
        return False


def mostrar_no_explorador(caminho: str | Path) -> None:
    """Abre a pasta do arquivo, com ele selecionado (Windows)."""
    caminho = Path(caminho)
    if os.name == "nt" and caminho.exists():
        subprocess.Popen(["explorer", "/select,", str(caminho)])
    else:
        abrir_no_sistema(caminho.parent if caminho.is_file() else caminho)


def formatar_duracao(segundos: float) -> str:
    segundos = max(0, int(round(segundos)))
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    if h:
        return f"{h} h {m:02d} min"
    if m:
        return f"{m} min {s:02d} s"
    return f"{s} s"


def quebrar_linhas(rotulo: tk.Misc, conteiner: tk.Misc, margem: int = 0) -> None:
    """Faz o texto do rótulo quebrar conforme a largura do contêiner (layout responsivo)."""
    conteiner.bind("<Configure>", lambda e: rotulo.configure(wraplength=max(120, e.width - margem)), add="+")


# ---- Estruturas ---------------------------------------------------------------------------

class Card(tk.Frame):
    """Cartão branco com borda fina e título opcional. Coloque o conteúdo em `.corpo`."""

    def __init__(self, master, titulo: str = "", subtitulo: str = "", padding: int = 16, **kw):
        super().__init__(master, bg=T.SUPERFICIE, highlightthickness=1,
                         highlightbackground=T.BORDA, highlightcolor=T.BORDA, **kw)
        self.cabecalho = None
        if titulo:
            self.cabecalho = tk.Frame(self, bg=T.SUPERFICIE)
            self.cabecalho.pack(fill="x", padx=padding, pady=(padding - 2, 0))
            textos = tk.Frame(self.cabecalho, bg=T.SUPERFICIE)
            textos.pack(side="left", fill="x", expand=True)
            self.lbl_titulo = ttk.Label(textos, text=titulo, style="H2.Card.TLabel")
            self.lbl_titulo.pack(anchor="w")
            self.acoes = tk.Frame(self.cabecalho, bg=T.SUPERFICIE)
            self.acoes.pack(side="right", anchor="n")
            if subtitulo:
                sub = ttk.Label(textos, text=subtitulo, style="Muted.Card.TLabel", wraplength=520,
                                justify="left")
                sub.pack(anchor="w", pady=(2, 0))
                self.cabecalho.bind("<Configure>", lambda e: sub.configure(
                    wraplength=max(160, e.width - self.acoes.winfo_reqwidth() - 16)), add="+")
        self.corpo = tk.Frame(self, bg=T.SUPERFICIE)
        self.corpo.pack(fill="both", expand=True, padx=padding, pady=(10 if titulo else padding, padding))


class CabecalhoPagina(ttk.Frame):
    """Título e subtítulo da página, com espaço para ações à direita (`.acoes`)."""

    def __init__(self, master, titulo: str, subtitulo: str = ""):
        super().__init__(master)
        self.acoes = ttk.Frame(self)  # empacotadas primeiro: as ações nunca são cortadas
        self.acoes.pack(side="right", anchor="ne")
        textos = ttk.Frame(self)
        textos.pack(side="left", fill="x", expand=True)
        ttk.Label(textos, text=titulo, style="Titulo.TLabel").pack(anchor="w")
        self.subtitulo = ttk.Label(textos, text=subtitulo, style="Subtitulo.TLabel", justify="left")
        self.subtitulo.pack(anchor="w", pady=(2, 0))
        textos.bind("<Configure>", lambda e: self.subtitulo.configure(wraplength=max(200, e.width - 8)))


class Rolavel(ttk.Frame):
    """Área com rolagem vertical (roda do mouse incluída). Coloque o conteúdo em `.interno`."""

    def __init__(self, master, fundo: str = T.FUNDO):
        super().__init__(master)
        # width=1: a área ocupa o espaço que o layout der, sem exigir uma largura mínima própria
        self.canvas = tk.Canvas(self, bg=fundo, highlightthickness=0, borderwidth=0, width=1, height=1)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interno = tk.Frame(self.canvas, bg=fundo)
        self._janela = self.canvas.create_window((0, 0), window=self.interno, anchor="nw")
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.barra.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self._barra_visivel = True
        self.interno.bind("<Configure>", lambda e: self._ajustar())
        self.canvas.bind("<Configure>", lambda e: self._ajustar())
        self.bind_all("<MouseWheel>", self._rolar, add="+")
        self.bind_all("<Button-4>", self._rolar, add="+")
        self.bind_all("<Button-5>", self._rolar, add="+")

    def _ajustar(self) -> None:
        """Atualiza a área rolável e só mostra a barra quando o conteúdo não cabe."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        precisa = self.interno.winfo_reqheight() > self.canvas.winfo_height() + 1
        if precisa != self._barra_visivel:
            self._barra_visivel = precisa
            if precisa:
                self.barra.pack(side="right", fill="y", before=self.canvas)
            else:
                self.barra.pack_forget()
                self.canvas.yview_moveto(0)
        # respiro à direita quando há barra, para o conteúdo não encostar nela
        largura = self.canvas.winfo_width() - (10 if precisa else 0)
        self.canvas.itemconfigure(self._janela, width=max(1, largura))

    def _rolar(self, evento):
        try:
            self._rolar_seguro(evento)
        except tk.TclError:  # a área já foi fechada (ex.: janela de diálogo)
            pass

    def _rolar_seguro(self, evento):
        if not self.winfo_exists() or not self.winfo_ismapped():
            return
        widget = evento.widget
        # só rola se o mouse está sobre esta área (e não sobre uma tabela/texto com rolagem própria)
        try:
            caminho = str(widget)
        except Exception:  # noqa: BLE001
            return
        if not caminho.startswith(str(self.canvas)) or isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox)):
            return
        if self.interno.winfo_height() <= self.canvas.winfo_height():
            return
        if getattr(evento, "num", None) == 4:
            passo = -1
        elif getattr(evento, "num", None) == 5:
            passo = 1
        else:
            passo = -1 if evento.delta > 0 else 1
        self.canvas.yview_scroll(passo * 3, "units")


class Banner(tk.Frame):
    """Aviso colorido em linha, com ações. tipo: info | sucesso | aviso | erro."""

    CORES = {
        "info": (T.PRIMARIA_CLARA, T.PRIMARIA_TEXTO, "ℹ"),
        "sucesso": (T.SUCESSO_CLARO, "#14532D", "✔"),
        "aviso": (T.AVISO_CLARO, "#78350F", "⚠"),
        "erro": (T.ERRO_CLARO, "#7F1D1D", "✖"),
    }

    def __init__(self, master, tipo: str, texto: str, acoes: list[tuple[str, Callable, str]] | None = None,
                 fechavel: bool = False):
        fundo, frente, icone = self.CORES[tipo]
        super().__init__(master, bg=fundo, highlightthickness=1, highlightbackground=fundo)
        if fechavel:
            fechar = tk.Label(self, text="✕", bg=fundo, fg=frente, cursor="hand2", font=T.F["base"])
            fechar.pack(side="right", padx=(0, 10))
            fechar.bind("<Button-1>", lambda e: self.destroy())
        self.botoes = tk.Frame(self, bg=fundo)  # empacotado antes do texto: os botões nunca são cortados
        self.botoes.pack(side="right", padx=10, pady=6)
        for rotulo, comando, estilo in acoes or []:
            ttk.Button(self.botoes, text=rotulo, command=comando, style=estilo).pack(side="left", padx=4)
        self.icone = tk.Label(self, text=icone, bg=fundo, fg=frente, font=T.F["icone"])
        self.icone.pack(side="left", padx=(14, 8), pady=10, anchor="n")
        self.texto = tk.Label(self, text=texto, bg=fundo, fg=frente, font=T.F["base"], justify="left",
                              anchor="w", wraplength=600)
        self.texto.pack(side="left", fill="x", expand=True, pady=10)
        self.bind("<Configure>", lambda e: self.texto.configure(
            wraplength=max(200, e.width - self.botoes.winfo_reqwidth() - 80)))


class KPI(tk.Frame):
    """Indicador grande: rótulo, valor e detalhe."""

    def __init__(self, master, rotulo: str, valor: str = "—", detalhe: str = "", cor: str = T.TEXTO):
        super().__init__(master, bg=T.SUPERFICIE, highlightthickness=1, highlightbackground=T.BORDA)
        self.rotulo = ttk.Label(self, text=rotulo.upper(), style="Dica.Card.TLabel")
        self.rotulo.pack(anchor="w", padx=16, pady=(14, 0))
        self.valor = tk.Label(self, text=valor, bg=T.SUPERFICIE, fg=cor, font=T.F["kpi"], anchor="w")
        self.valor.pack(anchor="w", padx=16, pady=(2, 0))
        self.detalhe = ttk.Label(self, text=detalhe, style="Muted.Card.TLabel")
        self.detalhe.pack(anchor="w", padx=16, pady=(0, 14))

    def definir(self, valor: str, detalhe: str | None = None, cor: str | None = None) -> None:
        self.valor.configure(text=valor)
        if cor:
            self.valor.configure(fg=cor)
        if detalhe is not None:
            self.detalhe.configure(text=detalhe)


class Toast:
    """Notificação temporária no canto inferior direito (não bloqueia o trabalho)."""

    def __init__(self, raiz: tk.Misc):
        self.raiz = raiz
        self._atual: tk.Frame | None = None
        self._tarefa = None

    def mostrar(self, texto: str, tipo: str = "sucesso", duracao_ms: int = 3500) -> None:
        if self._atual is not None:
            self._atual.destroy()
            if self._tarefa:
                self.raiz.after_cancel(self._tarefa)
        fundo, frente, icone = {"sucesso": ("#14532D", "#FFFFFF", "✔"), "info": ("#1E293B", "#FFFFFF", "ℹ"),
                                "aviso": ("#78350F", "#FFFFFF", "⚠"), "erro": ("#7F1D1D", "#FFFFFF", "✖")}[tipo]
        quadro = tk.Frame(self.raiz, bg=fundo)
        tk.Label(quadro, text=f"{icone}  {texto}", bg=fundo, fg=frente, font=T.F["base"], padx=16, pady=10,
                 wraplength=420, justify="left").pack()
        quadro.place(relx=1.0, rely=1.0, x=-20, y=-44, anchor="se")
        quadro.lift()
        self._atual = quadro
        self._tarefa = self.raiz.after(duracao_ms, self._fechar)

    def _fechar(self):
        if self._atual is not None:
            self._atual.destroy()
            self._atual = None


class Dica:
    """Tooltip simples (aparece ao parar o mouse sobre o componente)."""

    def __init__(self, widget: tk.Misc, texto: str):
        self.widget, self.texto, self.janela = widget, texto, None
        widget.bind("<Enter>", self._agendar, add="+")
        widget.bind("<Leave>", self._esconder, add="+")
        self._id = None

    def _agendar(self, _):
        self._id = self.widget.after(500, self._mostrar)

    def _mostrar(self):
        if self.janela:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.janela = tk.Toplevel(self.widget)
        self.janela.wm_overrideredirect(True)
        self.janela.wm_geometry(f"+{x}+{y}")
        tk.Label(self.janela, text=self.texto, bg="#1E293B", fg="#FFFFFF", font=T.F["pequena"],
                 padx=8, pady=5, wraplength=320, justify="left").pack()

    def _esconder(self, _):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self.janela:
            self.janela.destroy()
            self.janela = None


# ---- Campos -------------------------------------------------------------------------------

class Campo(tk.Frame):
    """
    Rótulo + campo + dica + mensagem de erro (validação em linha).
    `validar` recebe o texto e devolve o valor normalizado ou levanta ValueError.
    `exibir` formata o valor para mostrar no campo (ex.: CPF com pontos).
    """

    def __init__(self, master, rotulo: str, dica: str = "", obrigatorio: bool = True,
                 validar: Callable[[str], object] | None = None,
                 exibir: Callable[[object], str] | None = None, largura: int = 28):
        super().__init__(master, bg=T.SUPERFICIE)
        self.validar_fn, self.exibir_fn = validar, exibir
        texto = rotulo + (" *" if obrigatorio else "")
        self.rotulo = ttk.Label(self, text=texto, style="Rotulo.Card.TLabel")
        self.rotulo.pack(anchor="w")
        self.var = tk.StringVar()
        self.entrada = ttk.Entry(self, textvariable=self.var, width=largura)
        self.entrada.pack(fill="x", pady=(4, 0))
        self.dica = ttk.Label(self, text=dica, style="Dica.Card.TLabel", wraplength=320, justify="left")
        self.dica.pack(anchor="w", pady=(3, 0))
        self._texto_dica = dica
        self.entrada.bind("<FocusOut>", lambda e: self.conferir(silencioso_se_vazio=True))
        self.entrada.bind("<KeyRelease>", self._ao_digitar)

    def _ao_digitar(self, _):
        if str(self.entrada.cget("style")) == "Erro.TEntry":
            self.conferir(silencioso_se_vazio=True)

    def texto(self) -> str:
        return self.var.get().strip()

    def definir(self, valor) -> None:
        self.var.set(self.exibir_fn(valor) if (self.exibir_fn and valor not in (None, "")) else (valor or ""))
        self.limpar_erro()

    def mostrar_erro(self, msg: str) -> None:
        self.entrada.configure(style="Erro.TEntry")
        self.dica.configure(text=f"✖ {msg}", style="Erro.Card.TLabel")

    def limpar_erro(self) -> None:
        self.entrada.configure(style="TEntry")
        self.dica.configure(text=self._texto_dica, style="Dica.Card.TLabel")

    def conferir(self, silencioso_se_vazio: bool = False):
        """Valida; mostra o erro em linha. Devolve o valor normalizado ou None se inválido."""
        texto = self.texto()
        if not texto and silencioso_se_vazio:
            self.limpar_erro()
            return None
        try:
            valor = self.validar_fn(texto) if self.validar_fn else texto
        except ValueError as exc:
            self.mostrar_erro(str(exc))
            return None
        self.limpar_erro()
        if self.exibir_fn and valor not in (None, ""):
            self.var.set(self.exibir_fn(valor))
        return valor

    def focar(self) -> None:
        self.entrada.focus_set()
        self.entrada.icursor("end")
        self.entrada.select_range(0, "end")


# ---- Tabela -------------------------------------------------------------------------------

class Tabela(tk.Frame):
    """Treeview com rolagem, cabeçalhos ordenáveis e mensagem de "vazio"."""

    def __init__(self, master, colunas: list[tuple[str, str, int, str]], altura: int = 10,
                 vazio: str = "Nada por aqui ainda.", selecao: str = "extended", ordenavel: bool = True):
        """colunas: [(id, título, largura, alinhamento 'w'|'e'|'center')]"""
        super().__init__(master, bg=T.SUPERFICIE, highlightthickness=1, highlightbackground=T.BORDA)
        ids = [c[0] for c in colunas]
        self.arvore = ttk.Treeview(self, columns=ids, show="headings", height=altura, selectmode=selecao)
        self._titulos = {}
        for cid, titulo, largura, alinhamento in colunas:
            self._titulos[cid] = titulo
            self.arvore.heading(cid, text=titulo, anchor=alinhamento,
                                command=(lambda c=cid: self.ordenar(c)) if ordenavel else "")
            self.arvore.column(cid, width=largura, minwidth=40, anchor=alinhamento,
                               stretch=alinhamento == "w")
        barra = ttk.Scrollbar(self, orient="vertical", command=self.arvore.yview)
        self.arvore.configure(yscrollcommand=barra.set)
        self.arvore.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.vazio = tk.Label(self, text=vazio, bg=T.SUPERFICIE, fg=T.TEXTO_3, font=T.F["base"],
                              justify="center", wraplength=380)
        self.arvore.tag_configure("par", background="#FAFBFD")
        self.arvore.tag_configure("sucesso", foreground=T.SUCESSO)
        self.arvore.tag_configure("erro", foreground=T.ERRO)
        self.arvore.tag_configure("aviso", foreground=T.AVISO)
        self.arvore.tag_configure("andamento", foreground=T.PRIMARIA, font=T.F["negrito"])
        self.arvore.tag_configure("apagar", background="#FEECEC")
        self.arvore.tag_configure("protegido", foreground=T.AVISO)
        self._ordem: tuple[str, bool] | None = None
        self.chaves_ordenacao: dict[str, Callable[[str], object]] = {}
        self.atualizar_vazio()

    def limpar(self) -> None:
        self.arvore.delete(*self.arvore.get_children())
        self.atualizar_vazio()

    def inserir(self, valores, iid: str | None = None, tags: tuple = ()) -> str:
        n = len(self.arvore.get_children())
        tags = tuple(tags) + (("par",) if n % 2 else ())
        item = self.arvore.insert("", "end", iid=iid, values=valores, tags=tags)
        return item

    def atualizar_vazio(self) -> None:
        if self.arvore.get_children():
            self.vazio.place_forget()
        else:
            self.vazio.place(relx=0.5, rely=0.55, anchor="center")

    def selecionados(self) -> list[str]:
        return list(self.arvore.selection())

    def ordenar(self, coluna: str) -> None:
        crescente = not (self._ordem and self._ordem[0] == coluna and self._ordem[1])
        chave = self.chaves_ordenacao.get(coluna, lambda v: (str(v).lower()))
        itens = [(self.arvore.set(i, coluna), i) for i in self.arvore.get_children("")]
        try:
            itens.sort(key=lambda par: chave(par[0]), reverse=not crescente)
        except Exception:  # noqa: BLE001
            itens.sort(key=lambda par: str(par[0]), reverse=not crescente)
        for pos, (_, i) in enumerate(itens):
            self.arvore.move(i, "", pos)
            tags = [t for t in self.arvore.item(i, "tags") if t != "par"]
            self.arvore.item(i, tags=tuple(tags) + (("par",) if pos % 2 else ()))
        for cid, titulo in self._titulos.items():
            seta = (" ▲" if crescente else " ▼") if cid == coluna else ""
            self.arvore.heading(cid, text=titulo + seta)
        self._ordem = (coluna, crescente)


# ---- Gráficos (Canvas, sem bibliotecas externas) ------------------------------------------

class _Grafico(tk.Canvas):
    def __init__(self, master, altura: int = 200, **kw):
        super().__init__(master, height=altura, bg=T.SUPERFICIE, highlightthickness=0, **kw)
        self.bind("<Configure>", lambda e: self.desenhar())

    def desenhar(self):  # pragma: no cover - sobrescrito
        pass

    def _vazio(self, texto: str = "Sem dados para mostrar ainda.") -> None:
        self.create_text(self.winfo_width() / 2, self.winfo_height() / 2, text=texto,
                         fill=T.TEXTO_3, font=T.F["base"])


def _passo_eixo(maximo: float) -> float:
    """Passo "redondo" para ~4 linhas de grade."""
    if maximo <= 0:
        return 1
    bruto = maximo / 4
    import math
    potencia = 10 ** math.floor(math.log10(bruto))
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= m * potencia:
            return m * potencia
    return 10 * potencia


def _num(v: float) -> str:
    if abs(v) >= 100 or v == int(v):
        return f"{v:,.0f}".replace(",", ".")
    return f"{v:.1f}".replace(".", ",")


class GraficoLinha(_Grafico):
    """Linhas ao longo do tempo. series: [(nome, cor, [valores])]."""

    def __init__(self, master, altura: int = 200, maximo: float | None = None, unidade: str = "",
                 rotulos_x: tuple[str, str] = ("", "")):
        super().__init__(master, altura)
        self.series: list[tuple[str, str, list[float]]] = []
        self.maximo_fixo, self.unidade, self.rotulos_x = maximo, unidade, rotulos_x

    def definir(self, series: list[tuple[str, str, list[float]]]) -> None:
        self.series = series
        self.desenhar()

    def desenhar(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or h < 50:
            return
        if not any(v for _, _, v in self.series):
            self._vazio()
            return
        esq, dir_, topo, base = 52, 16, 26, 26
        maior = self.maximo_fixo or max((max(v) for _, _, v in self.series if v), default=1) * 1.15 or 1
        passo = _passo_eixo(maior)
        maior = passo * max(1, -(-maior // passo))
        y = 0.0
        while y <= maior + 1e-9:
            py = base_y = h - base - (h - base - topo) * (y / maior)
            self.create_line(esq, py, w - dir_, py, fill="#EDF1F6")
            self.create_text(esq - 8, base_y, text=_num(y), anchor="e", fill=T.TEXTO_3, font=T.F["pequena"])
            y += passo
        if self.unidade:
            self.create_text(esq - 8, topo - 14, text=self.unidade, anchor="e", fill=T.TEXTO_3, font=T.F["pequena"])
        self.create_text(esq, h - 8, text=self.rotulos_x[0], anchor="w", fill=T.TEXTO_3, font=T.F["pequena"])
        self.create_text(w - dir_, h - 8, text=self.rotulos_x[1], anchor="e", fill=T.TEXTO_3, font=T.F["pequena"])
        x_leg = esq
        for nome, cor, valores in self.series:
            if len(valores) >= 1:
                n = max(len(valores) - 1, 1)
                pontos = []
                for i, v in enumerate(valores):
                    px = esq + (w - esq - dir_) * (i / n if len(valores) > 1 else 1)
                    py = h - base - (h - base - topo) * (min(v, maior) / maior)
                    pontos.extend((px, py))
                if len(pontos) >= 4:
                    self.create_line(*pontos, fill=cor, width=2, smooth=False)
                self.create_oval(pontos[-2] - 3, pontos[-1] - 3, pontos[-2] + 3, pontos[-1] + 3, fill=cor, outline=cor)
            if nome:
                ultimo = f" {_num(valores[-1])}" if valores else ""
                self.create_rectangle(x_leg, 8, x_leg + 10, 18, fill=cor, outline=cor)
                t = self.create_text(x_leg + 15, 13, text=f"{nome}{ultimo}", anchor="w", fill=T.TEXTO_2,
                                     font=T.F["pequena"])
                x_leg = self.bbox(t)[2] + 18


class GraficoBarrasH(_Grafico):
    """Barras horizontais com rótulo e valor. itens: [(rótulo, valor)]. Destaca a maior."""

    def __init__(self, master, unidade: str = "s", destacar_maior: bool = True, altura: int = 240):
        super().__init__(master, altura)
        self.itens: list[tuple[str, float]] = []
        self.unidade, self.destacar_maior = unidade, destacar_maior

    def definir(self, itens: list[tuple[str, float]]) -> None:
        self.itens = itens
        self.configure(height=max(80, 34 * len(itens) + 16))
        self.desenhar()

    def desenhar(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 50:
            return
        if not self.itens:
            self._vazio()
            return
        import tkinter.font as tkfont
        fonte = tkfont.Font(font=T.F["pequena"])
        maior_rotulo = max(fonte.measure(r) for r, _ in self.itens) + 18
        margem = min(maior_rotulo, int(w * 0.55))
        maior = max(v for _, v in self.itens) or 1
        for i, (rotulo, valor) in enumerate(self.itens):
            y = 8 + i * 34
            cor = T.AVISO if (self.destacar_maior and valor == maior and len(self.itens) > 1) else T.SERIES[0]
            self.create_text(margem - 10, y + 12, text=rotulo, anchor="e", fill=T.TEXTO_2, font=T.F["pequena"])
            largura = max(3, (w - margem - 90) * valor / maior)
            self.create_rectangle(margem, y + 2, margem + largura, y + 22, fill=cor, outline=cor)
            self.create_text(margem + largura + 8, y + 12, text=f"{_num(valor) if valor >= 10 else f'{valor:.2f}'.replace('.', ',')} {self.unidade}",
                             anchor="w", fill=T.TEXTO, font=T.F["pequena"])


class GraficoColunas(_Grafico):
    """Colunas empilhadas por categoria. categorias: [(rótulo, [valores por série])]."""

    def __init__(self, master, series: list[tuple[str, str]], altura: int = 200):
        super().__init__(master, altura)
        self.nomes_series = series
        self.categorias: list[tuple[str, list[float]]] = []

    def definir(self, categorias: list[tuple[str, list[float]]]) -> None:
        self.categorias = categorias
        self.desenhar()

    def desenhar(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or h < 50:
            return
        if not self.categorias or not any(sum(v) for _, v in self.categorias):
            self._vazio("Nenhuma execução registrada no período.")
            return
        esq, dir_, topo, base = 40, 10, 28, 24
        maior = max(sum(v) for _, v in self.categorias) or 1
        passo = _passo_eixo(maior)
        maior = passo * max(1, -(-maior // passo))
        y = 0.0
        while y <= maior + 1e-9:
            py = h - base - (h - base - topo) * (y / maior)
            self.create_line(esq, py, w - dir_, py, fill="#EDF1F6")
            self.create_text(esq - 6, py, text=_num(y), anchor="e", fill=T.TEXTO_3, font=T.F["pequena"])
            y += passo
        n = len(self.categorias)
        largura_cat = (w - esq - dir_) / n
        barra = max(4, min(28, largura_cat * 0.6))
        for i, (rotulo, valores) in enumerate(self.categorias):
            cx = esq + largura_cat * (i + 0.5)
            acumulado = 0.0
            for (nome, cor), v in zip(self.nomes_series, valores):
                if v <= 0:
                    continue
                y0 = h - base - (h - base - topo) * (acumulado / maior)
                acumulado += v
                y1 = h - base - (h - base - topo) * (acumulado / maior)
                self.create_rectangle(cx - barra / 2, y1, cx + barra / 2, y0, fill=cor, outline=cor)
            if n <= 16 or i % 2 == 0:
                self.create_text(cx, h - 10, text=rotulo, fill=T.TEXTO_3, font=T.F["pequena"])
        x_leg = esq
        for nome, cor in self.nomes_series:
            self.create_rectangle(x_leg, 8, x_leg + 10, 18, fill=cor, outline=cor)
            t = self.create_text(x_leg + 15, 13, text=nome, anchor="w", fill=T.TEXTO_2, font=T.F["pequena"])
            x_leg = self.bbox(t)[2] + 18


class Etapas(tk.Canvas):
    """Indicador das etapas do lançamento atual (DARE 1..6 · SEI 1..4)."""

    def __init__(self, master, etapas: list[tuple[str, str]]):
        super().__init__(master, height=58, bg=T.SUPERFICIE, highlightthickness=0)
        self.etapas = etapas  # [(chave, rótulo curto)]
        self.atual: int = -1
        self.concluido = False
        self.bind("<Configure>", lambda e: self.desenhar())

    def definir(self, chave: str | None, concluido: bool = False) -> None:
        chaves = [c for c, _ in self.etapas]
        self.atual = chaves.index(chave) if chave in chaves else -1
        self.concluido = concluido
        self.desenhar()

    def desenhar(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 50:
            return
        n = len(self.etapas)
        espaco = 4
        largura = (w - espaco * (n - 1)) / n
        for i, (_, rotulo) in enumerate(self.etapas):
            x0 = i * (largura + espaco)
            if self.concluido or i < self.atual:
                cor = T.SUCESSO
            elif i == self.atual:
                cor = T.PRIMARIA
            else:
                cor = "#E2E8F0"
            self.create_rectangle(x0, 6, x0 + largura, 14, fill=cor, outline=cor)
            cor_texto = T.PRIMARIA_TEXTO if i == self.atual and not self.concluido else T.TEXTO_3
            self.create_text(x0 + largura / 2, 34, text=rotulo, fill=cor_texto, font=T.F["pequena"],
                             width=max(30, largura))
