"""Página Configurações e sobre: versão, navegador, pastas e valores fixos."""

import tkinter as tk
from tkinter import ttk

from ... import __data_versao__, __version__, config, desempenho, navegador, preferencias
from .. import tema as T
from ..app import Pagina
from ..widgets import CabecalhoPagina, Card, Rolavel, abrir_no_sistema, quebrar_linhas


def _quebra(rotulo, conteiner):
    quebrar_linhas(rotulo, conteiner, 4)
    return rotulo


class PaginaConfiguracoes(Pagina):
    titulo = "Configurações"
    icone = "⚙"

    def __init__(self, app):
        super().__init__(app)
        CabecalhoPagina(self, "Configurações e sobre", "Versão do programa, navegador usado e onde ficam os arquivos."
                        ).pack(fill="x")
        rol = Rolavel(self)
        rol.pack(fill="both", expand=True, pady=(14, 0))
        area = rol.interno
        area.columnconfigure(0, weight=1, uniform="c")
        area.columnconfigure(1, weight=1, uniform="c")

        # Sobre
        sobre = Card(area, "Sobre o DARE Automação")
        sobre.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 14))
        s = sobre.corpo
        linha = tk.Frame(s, bg=T.SUPERFICIE)
        linha.pack(fill="x")
        tk.Label(linha, text=f"Versão {__version__}", bg=T.PRIMARIA_CLARA, fg=T.PRIMARIA_TEXTO, font=T.F["h2"],
                 padx=12, pady=4).pack(side="left")
        ttk.Label(linha, text=f"  lançada em {__data_versao__}", style="Muted.Card.TLabel").pack(side="left")
        tipo = "aplicativo instalado (executável)" if config.EMPACOTADO else "executando pelo código-fonte (Python)"
        ttk.Label(s, text=f"Modo: {tipo}", style="Muted.Card.TLabel").pack(anchor="w", pady=(10, 0))
        _quebra(ttk.Label(s, text="Automatiza o fluxo DARE avulso → PDF → documento externo no SEI, em lotes digitados "
                  "ou lidos de planilhas do Excel.", style="Card.TLabel", wraplength=440, justify="left"
                  ), s).pack(anchor="w", pady=(8, 0))
        _quebra(ttk.Label(s, text="Software proprietário · © 2026 · uso restrito a pessoas autorizadas pelo titular.",
                  style="Dica.Card.TLabel", wraplength=440, justify="left"), s).pack(anchor="w", pady=(8, 0))
        botoes = tk.Frame(s, bg=T.SUPERFICIE)
        botoes.pack(anchor="w", pady=(12, 0))
        for texto, nome in (("Guia de uso", "GUIA_DE_USO.html"), ("Licença", "LICENCA.txt")):
            caminho = config.RECURSOS / nome
            b = ttk.Button(botoes, text=texto, command=lambda c=caminho: abrir_no_sistema(c))
            b.pack(side="left", padx=(0, 8))
            if not caminho.exists():
                b.state(["disabled"])

        # Navegador
        nav = Card(area, "Navegador", "O programa usa um navegador próprio, com o login do DARE e do SEI salvo.")
        nav.grid(row=0, column=1, sticky="nsew", pady=(0, 14))
        n = nav.corpo
        exe = navegador.localizar_chrome()
        if exe:
            nome = f"{navegador.nome_navegador(exe)} {desempenho.versao_navegador(exe)}".strip()
            ttk.Label(n, text=nome, style="Rotulo.Card.TLabel").pack(anchor="w")
            _quebra(ttk.Label(n, text=exe, style="Dica.Card.TLabel", wraplength=440), n).pack(anchor="w")
            if "Edge" in nome:
                _quebra(ttk.Label(n, text="O Google Chrome não foi encontrado; o Microsoft Edge está sendo usado no lugar.",
                          style="Muted.Card.TLabel", wraplength=440, justify="left"), n).pack(anchor="w", pady=(6, 0))
        else:
            ttk.Label(n, text="Nenhum navegador compatível encontrado. Instale o Google Chrome.",
                      style="Erro.Card.TLabel").pack(anchor="w")
        _quebra(ttk.Label(n, text=f"Perfil: {navegador.perfil_para(exe) if exe else config.PERFIL_CHROME}",
                  style="Dica.Card.TLabel", wraplength=440), n).pack(anchor="w", pady=(6, 0))
        self.var_abrir = tk.BooleanVar(value=app.pref.abrir_navegador_ao_iniciar)
        ttk.Checkbutton(n, text="Abrir o navegador (SEI e DARE) ao iniciar o programa", variable=self.var_abrir,
                        command=self._salvar).pack(anchor="w", pady=(10, 0))
        ttk.Button(n, text="Abrir navegador agora", command=app.abrir_navegador).pack(anchor="w", pady=(8, 0))

        # Pastas
        pastas = Card(area, "Pastas e arquivos", "Os dados ficam no seu computador. PDFs, dados e logs contêm "
                      "CPF e nomes: não compartilhe (LGPD).")
        pastas.grid(row=1, column=0, sticky="nsew", padx=(0, 12), pady=(0, 14))
        self.corpo_pastas = pastas.corpo

        # Valores fixos
        fixos = Card(area, "Valores fixos do DARE e do SEI", "Definidos em dare_auto/config.py.")
        fixos.grid(row=1, column=1, sticky="nsew", pady=(0, 14))
        for rotulo, valor in (("Órgão", config.ORGAO), ("Código da receita", config.CODIGO_RECEITA),
                              ("Unidade gestora", config.UNIDADE_GESTORA), ("Gestão", config.GESTAO),
                              ("Valor padrão", f"R$ {config.VALOR_PADRAO}"), ("Série do documento no SEI", config.SERIE_SEI),
                              ("Site do DARE", config.URL_DARE), ("Site do SEI", config.HOST_SEI)):
            fila = tk.Frame(fixos.corpo, bg=T.SUPERFICIE)
            fila.pack(fill="x", pady=2)
            ttk.Label(fila, text=rotulo, style="Muted.Card.TLabel", width=24).pack(side="left", anchor="n")
            valor_lbl = ttk.Label(fila, text=valor, style="Card.TLabel", wraplength=300, justify="left")
            valor_lbl.pack(side="left", anchor="w", fill="x", expand=True)
            quebrar_linhas(valor_lbl, fila, 190)

    def ao_mostrar(self) -> None:
        for w in self.corpo_pastas.winfo_children():
            w.destroy()
        for rotulo, caminho in (("PDFs gerados", config.PASTA_PDF), ("Dados e histórico", config.PASTA_DADOS),
                                ("Logs e capturas de erro", config.PASTA_LOGS)):
            fila = tk.Frame(self.corpo_pastas, bg=T.SUPERFICIE)
            fila.pack(fill="x", pady=4)
            textos = tk.Frame(fila, bg=T.SUPERFICIE)
            textos.pack(side="left", fill="x", expand=True)
            ttk.Label(textos, text=rotulo, style="Rotulo.Card.TLabel").pack(anchor="w")
            _quebra(ttk.Label(textos, text=str(caminho), style="Dica.Card.TLabel", wraplength=360), textos).pack(anchor="w")
            ttk.Button(fila, text="Abrir", style="Pequeno.TButton",
                       command=lambda c=caminho: (c.mkdir(parents=True, exist_ok=True), abrir_no_sistema(c))
                       ).pack(side="right")

    def _salvar(self) -> None:
        self.app.pref.abrir_navegador_ao_iniciar = self.var_abrir.get()
        preferencias.salvar(self.app.pref)
        self.app.toast.mostrar("Preferência salva.")
