"""
Página Desempenho (estudo e apresentação): métricas reais da automação, monitor em tempo real,
diagnóstico do sistema e testes de velocidade.
"""

import queue
import shutil
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ... import config, desempenho as D
from ...motor import ROTULO_ETAPA
from .. import tema as T
from ..app import TITULO, Pagina
from ..widgets import (KPI, CabecalhoPagina, Card, GraficoBarrasH, GraficoColunas, GraficoLinha, Rolavel,
                       Tabela, abrir_no_sistema)

AMOSTRAS = 120  # 2 minutos de monitor


def _n(v: float, casas: int = 2) -> str:
    return D.num_br(v, casas)


def _taxa(bps: float) -> str:
    if bps >= 1024 ** 2:
        return f"{_n(bps / 1024 ** 2, 1)} MB/s"
    return f"{_n(bps / 1024, 0)} KB/s"


class PaginaDesempenho(Pagina):
    titulo = "Desempenho"
    icone = "◔"

    def __init__(self, app):
        super().__init__(app)
        self.diagnostico: list[D.ItemDiagnostico] = []
        self.benchmarks: list[D.ResultadoBenchmark] = []
        self._fila: queue.Queue = queue.Queue()
        self._monitor_ativo = threading.Event()
        self._thread_monitor: threading.Thread | None = None
        self._serie: dict[str, list[float]] = {k: [] for k in
                                                ("cpu", "ram", "app_cpu", "rede_rx", "rede_tx", "disco_leitura", "disco_escrita")}
        self._diag_feito = False

        cab = CabecalhoPagina(self, "Desempenho e diagnóstico",
                              "Medições do sistema e da automação, para acompanhamento, estudo e apresentação.")
        cab.pack(fill="x")
        ttk.Button(cab.acoes, text="Exportar dados (CSV)…", command=self.exportar_csv).pack(side="left", padx=(0, 8))
        ttk.Button(cab.acoes, text="Gerar relatório…", style="Primario.TButton",
                   command=self.exportar_relatorio).pack(side="left")

        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, pady=(14, 0))
        self._montar_visao_geral()
        self._montar_monitor()
        self._montar_diagnostico()
        self._montar_testes()
        self.abas.bind("<<NotebookTabChanged>>", self._aba_trocada)
        self.after(500, self._drenar)

    # ---- Visão geral (automação) ----------------------------------------------------------

    def _montar_visao_geral(self) -> None:
        rol = Rolavel(self.abas)
        self.abas.add(rol, text="  Automação  ")
        area = rol.interno
        topo = tk.Frame(area, bg=T.FUNDO)
        topo.pack(fill="x", pady=(14, 0))
        self.var_so_sucesso = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(topo, text="Estatísticas só com lançamentos concluídos com sucesso",
                              variable=self.var_so_sucesso, command=self.atualizar_visao_geral)
        chk.configure(style="Fundo.TCheckbutton")
        chk.pack(side="left")
        ttk.Button(topo, text="↻  Atualizar", style="Pequeno.TButton",
                   command=self.atualizar_visao_geral).pack(side="right")

        kpis = tk.Frame(area, bg=T.FUNDO)
        kpis.pack(fill="x", pady=(10, 0))
        self.k_lotes = KPI(kpis, "Lançamentos medidos")
        self.k_taxa = KPI(kpis, "Taxa de sucesso")
        self.k_media = KPI(kpis, "Tempo médio / lote")
        self.k_hora = KPI(kpis, "Lotes por hora")
        self.k_conexao = KPI(kpis, "Conexão ao navegador")
        for i, k in enumerate((self.k_lotes, self.k_taxa, self.k_media, self.k_hora, self.k_conexao)):
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            kpis.columnconfigure(i, weight=1, uniform="k")

        self.vazio_auto = tk.Label(area, text="", bg=T.FUNDO, fg=T.TEXTO_2, font=T.F["base"], justify="left")

        linha = tk.Frame(area, bg=T.FUNDO)
        linha.pack(fill="x", pady=(12, 0))
        linha.columnconfigure(0, weight=3, uniform="a")
        linha.columnconfigure(1, weight=2, uniform="a")
        c1 = Card(linha, "Tempo médio por etapa", "Em âmbar, a etapa mais demorada (gargalo).")
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.g_etapas = GraficoBarrasH(c1.corpo, unidade="s")
        self.g_etapas.pack(fill="x")
        self.lbl_gargalo = ttk.Label(c1.corpo, text="", style="Muted.Card.TLabel", wraplength=560, justify="left")
        self.lbl_gargalo.pack(anchor="w", pady=(8, 0))
        c2 = Card(linha, "Divisão do tempo", "Quanto de cada lançamento vai para o DARE e para o SEI.")
        c2.grid(row=0, column=1, sticky="nsew")
        self.divisao = tk.Canvas(c2.corpo, height=34, bg=T.SUPERFICIE, highlightthickness=0)
        self.divisao.pack(fill="x", pady=(4, 6))
        self.divisao.bind("<Configure>", lambda e: self._desenhar_divisao())
        self.lbl_divisao = ttk.Label(c2.corpo, text="", style="Muted.Card.TLabel", justify="left", wraplength=360)
        self.lbl_divisao.pack(anchor="w")
        ttk.Separator(c2.corpo).pack(fill="x", pady=12)
        ttk.Label(c2.corpo, text="Como os tempos são medidos", style="Rotulo.Card.TLabel").pack(anchor="w")
        ttk.Label(c2.corpo, text="Cada etapa é cronometrada com relógio de alta resolução no momento em que o "
                  "programa a inicia. Os dados ficam em dados/desempenho.csv (sem CPF nem processo) e podem ser "
                  "exportados para o Excel.", style="Dica.Card.TLabel", wraplength=360, justify="left").pack(anchor="w")
        self._divisao = (0.0, 0.0)

        linha2 = tk.Frame(area, bg=T.FUNDO)
        linha2.pack(fill="x", pady=(12, 0))
        linha2.columnconfigure(0, weight=1, uniform="b")
        linha2.columnconfigure(1, weight=1, uniform="b")
        c3 = Card(linha2, "Tempo de cada lançamento", "Últimos 60, em segundos (linha = tempo total).")
        c3.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.g_lotes = GraficoLinha(c3.corpo, altura=210, unidade="s", rotulos_x=("mais antigo", "mais recente"))
        self.g_lotes.pack(fill="x")
        c4 = Card(linha2, "Lançamentos por dia", "Últimos 14 dias, a partir do histórico.")
        c4.grid(row=0, column=1, sticky="nsew")
        self.g_dias = GraficoColunas(c4.corpo, [("Concluídos", T.SERIES[2]), ("Com erro", T.ERRO)], altura=210)
        self.g_dias.pack(fill="x")

        c5 = Card(area, "Estatística descritiva (segundos)",
                  "n = amostras · P95 = 95% dos lotes levaram até este tempo · CV = desvio ÷ média (variabilidade).")
        c5.pack(fill="x", pady=(12, 14))
        self.t_estat = Tabela(c5.corpo, [
            ("medida", "Medida", 260, "w"), ("n", "n", 50, "e"), ("media", "Média", 80, "e"),
            ("mediana", "Mediana", 80, "e"), ("desvio", "Desvio", 80, "e"), ("min", "Mín", 70, "e"),
            ("max", "Máx", 70, "e"), ("p95", "P95", 70, "e"), ("cv", "CV", 70, "e"),
        ], altura=10, vazio="Sem medições ainda.", selecao="none", ordenavel=False)
        self.t_estat.pack(fill="x")

    def atualizar_visao_geral(self) -> None:
        a = D.analisar_automacao(apenas_sucesso=self.var_so_sucesso.get())
        self.k_lotes.definir(str(a.lotes), f"em {a.execucoes} execução(ões)" if a.lotes else "nenhum ainda")
        self.k_taxa.definir(f"{_n(a.taxa_sucesso, 1)} %" if a.lotes else "—", f"{a.erros} com erro" if a.lotes else "",
                            T.SUCESSO if a.lotes and a.taxa_sucesso >= 90 else (T.AVISO if a.lotes else T.TEXTO))
        self.k_media.definir(f"{_n(a.total.media, 1)} s" if a.total.n else "—",
                             f"mediana {_n(a.total.mediana, 1)} s" if a.total.n else "")
        self.k_hora.definir(_n(a.lotes_por_hora, 0) if a.lotes_por_hora else "—", "estimado pela média")
        self.k_conexao.definir(f"{_n(a.conexao.media, 1)} s" if a.conexao.n else "—",
                               "média ao iniciar" if a.conexao.n else "")
        if not a.lotes:
            self.vazio_auto.configure(text="Ainda não há medições. Os tempos são registrados automaticamente a cada "
                                           "lançamento processado por este aplicativo.")
            self.vazio_auto.pack(anchor="w", pady=(8, 0), after=self.k_lotes.master)
        else:
            self.vazio_auto.pack_forget()
        itens = [(ROTULO_ETAPA[c], e.media) for c, e in a.etapas.items()]
        self.g_etapas.definir(itens)
        if a.gargalo and a.total.media:
            e = a.etapas[a.gargalo]
            self.lbl_gargalo.configure(
                text=f"Gargalo: “{ROTULO_ETAPA[a.gargalo]}” leva {_n(e.media)} s em média "
                     f"({_n(e.media / a.total.media * 100, 1)} % do lançamento).")
        else:
            self.lbl_gargalo.configure(text="")
        self._divisao = (a.dare.media, a.sei.media)
        self._desenhar_divisao()
        self.g_lotes.definir([("Tempo total", T.SERIES[0], a.ultimos_totais)] if a.ultimos_totais else [])
        dias = D.contagem_historico_por_dia(14)
        self.g_dias.definir([(r, [s, e]) for r, s, e in dias])
        self.t_estat.limpar()
        linhas = [("Lançamento completo", a.total), ("Fase DARE (gerar + PDF)", a.dare), ("Fase SEI (anexar)", a.sei),
                  ("Conexão com o navegador", a.conexao)]
        linhas += [(f"   {ROTULO_ETAPA[c]}", e) for c, e in a.etapas.items()]
        for nome, e in linhas:
            if e.n:
                self.t_estat.inserir([nome, e.n, _n(e.media), _n(e.mediana), _n(e.desvio), _n(e.minimo),
                                      _n(e.maximo), _n(e.p95), f"{_n(e.cv, 1)} %"])
        self.t_estat.arvore.configure(height=max(4, min(16, len(self.t_estat.arvore.get_children()))))
        self.t_estat.atualizar_vazio()

    def _desenhar_divisao(self) -> None:
        c = self.divisao
        c.delete("all")
        w = c.winfo_width()
        dare, sei = self._divisao
        total = dare + sei
        if w < 20 or not total:
            self.lbl_divisao.configure(text="Sem medições ainda.")
            c.create_rectangle(0, 4, w, 30, fill="#EEF2F7", outline="#EEF2F7")
            return
        x = w * dare / total
        c.create_rectangle(0, 4, x, 30, fill=T.SERIES[0], outline=T.SERIES[0])
        c.create_rectangle(x, 4, w, 30, fill=T.SERIES[1], outline=T.SERIES[1])
        if x > 60:
            c.create_text(x / 2, 17, text=f"DARE {_n(dare / total * 100, 0)} %", fill="#FFFFFF", font=T.F["negrito"])
        if w - x > 60:
            c.create_text(x + (w - x) / 2, 17, text=f"SEI {_n(sei / total * 100, 0)} %", fill="#FFFFFF",
                          font=T.F["negrito"])
        self.lbl_divisao.configure(text=f"DARE: {_n(dare)} s em média (preencher, imprimir e salvar o PDF).\n"
                                        f"SEI: {_n(sei)} s em média (abrir o processo e anexar).")

    # ---- Monitor --------------------------------------------------------------------------

    def _montar_monitor(self) -> None:
        aba = ttk.Frame(self.abas)
        self.abas.add(aba, text="  Monitor em tempo real  ")
        topo = tk.Frame(aba, bg=T.FUNDO)
        topo.pack(fill="x", pady=(14, 0))
        self.btn_monitor = ttk.Button(topo, text="▶  Iniciar monitor", style="Primario.TButton", command=self.alternar_monitor)
        self.btn_monitor.pack(side="left")
        self.lbl_monitor = ttk.Label(topo, text="Mede o uso do computador a cada segundo (últimos 2 minutos). "
                                     "Deixe ligado durante um processamento para ver o impacto da automação.",
                                     style="Subtitulo.TLabel", wraplength=680, justify="left")
        self.lbl_monitor.pack(side="left", padx=12)
        kpis = tk.Frame(aba, bg=T.FUNDO)
        kpis.pack(fill="x", pady=(12, 0))
        self.m_cpu = KPI(kpis, "CPU do computador")
        self.m_ram = KPI(kpis, "Memória em uso")
        self.m_app = KPI(kpis, "Este programa")
        self.m_nav = KPI(kpis, "Navegador")
        self.m_rede = KPI(kpis, "Rede")
        for i, k in enumerate((self.m_cpu, self.m_ram, self.m_app, self.m_nav, self.m_rede)):
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            kpis.columnconfigure(i, weight=1, uniform="m")
        graficos = tk.Frame(aba, bg=T.FUNDO)
        graficos.pack(fill="both", expand=True, pady=(12, 0))
        graficos.columnconfigure(0, weight=1, uniform="g")
        graficos.columnconfigure(1, weight=1, uniform="g")
        graficos.rowconfigure(0, weight=1)
        g1 = Card(graficos, "Processador e memória (%)")
        g1.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.g_cpu = GraficoLinha(g1.corpo, altura=230, maximo=100, unidade="%", rotulos_x=("-2 min", "agora"))
        self.g_cpu.pack(fill="both", expand=True)
        g2 = Card(graficos, "Rede e disco (KB/s)")
        g2.grid(row=0, column=1, sticky="nsew")
        self.g_io = GraficoLinha(g2.corpo, altura=230, unidade="KB/s", rotulos_x=("-2 min", "agora"))
        self.g_io.pack(fill="both", expand=True)
        if not D.psutil:
            self.btn_monitor.state(["disabled"])
            self.lbl_monitor.configure(text="O componente psutil não está instalado: o monitor não está disponível.")

    def alternar_monitor(self) -> None:
        if self._monitor_ativo.is_set():
            self._monitor_ativo.clear()
            self.btn_monitor.configure(text="▶  Iniciar monitor", style="Primario.TButton")
            return
        if self._thread_monitor is not None and self._thread_monitor.is_alive():
            return  # a anterior ainda está terminando
        self._monitor_ativo.set()
        self.btn_monitor.configure(text="■  Parar monitor", style="PerigoContorno.TButton")
        self._thread_monitor = threading.Thread(target=self._laco_monitor, daemon=True, name="dare-monitor")
        self._thread_monitor.start()

    def _laco_monitor(self) -> None:
        monitor = D.Monitor()
        monitor.amostra()  # a 1ª leitura serve só de base para as taxas e o uso de CPU
        time.sleep(1)
        while self._monitor_ativo.is_set():
            try:
                self._fila.put(("amostra", monitor.amostra()))
            except Exception:  # noqa: BLE001
                pass
            for _ in range(10):  # 1 amostra por segundo, parando rápido se pedirem
                if not self._monitor_ativo.is_set():
                    return
                time.sleep(0.1)

    def _nova_amostra(self, a: dict) -> None:
        if not a:
            return
        for chave in self._serie:
            valor = a.get(chave, 0.0)
            if chave.startswith(("rede", "disco")):
                valor /= 1024
            serie = self._serie[chave]
            serie.append(valor)
            del serie[:-AMOSTRAS]
        self.m_cpu.definir(f"{_n(a['cpu'], 0)} %", "uso total", T.ERRO if a["cpu"] > 90 else T.TEXTO)
        self.m_ram.definir(f"{_n(a['ram'], 0)} %", f"{_n(a['ram_usada_gb'], 1)} GB em uso")
        self.m_app.definir(f"{_n(a['app_mb'], 0)} MB", f"CPU {_n(a['app_cpu'], 1)} % · {a['threads']} threads")
        self.m_nav.definir(f"{_n(a['navegador_mb'], 0)} MB", "todas as janelas")
        self.m_rede.definir(f"↓ {_taxa(a['rede_rx'])}", f"↑ {_taxa(a['rede_tx'])}")
        if self.abas.index("current") == 1:
            janela = (f"-{len(self._serie['cpu'])} s", "agora")
            self.g_cpu.rotulos_x = self.g_io.rotulos_x = janela
            self.g_cpu.definir([("CPU", T.SERIES[0], self._serie["cpu"]), ("Memória", T.SERIES[1], self._serie["ram"]),
                                ("Este programa", T.SERIES[2], self._serie["app_cpu"])])
            self.g_io.definir([("Rede ↓", T.SERIES[0], self._serie["rede_rx"]),
                               ("Rede ↑", T.SERIES[3], self._serie["rede_tx"]),
                               ("Disco leitura", T.SERIES[2], self._serie["disco_leitura"]),
                               ("Disco escrita", T.SERIES[1], self._serie["disco_escrita"])])

    # ---- Diagnóstico ----------------------------------------------------------------------

    def _montar_diagnostico(self) -> None:
        aba = ttk.Frame(self.abas)
        self.abas.add(aba, text="  Diagnóstico do sistema  ")
        topo = tk.Frame(aba, bg=T.FUNDO)
        topo.pack(fill="x", pady=(14, 0))
        self.btn_diag = ttk.Button(topo, text="↻  Executar diagnóstico", style="Primario.TButton", command=self.diagnosticar)
        self.btn_diag.pack(side="left")
        self.lbl_diag = ttk.Label(topo, text="Confere o computador, os componentes do programa e a conexão com o DARE e o SEI.",
                                  style="Subtitulo.TLabel")
        self.lbl_diag.pack(side="left", padx=12)
        self.t_diag = Tabela(aba, [
            ("grupo", "Grupo", 110, "w"), ("item", "Item", 220, "w"), ("resultado", "Resultado", 260, "w"),
            ("detalhe", "Detalhe", 420, "w"),
        ], altura=16, vazio="Clique em “Executar diagnóstico”.", selecao="browse", ordenavel=False)
        self.t_diag.pack(fill="both", expand=True, pady=(12, 0))
        self.t_diag.arvore.tag_configure("ok", foreground=T.TEXTO)
        self.t_diag.arvore.tag_configure("info", foreground=T.TEXTO)

    def diagnosticar(self) -> None:
        self.btn_diag.state(["disabled"])
        self.lbl_diag.configure(text="Executando… (a parte de rede pode levar alguns segundos)")
        self.t_diag.limpar()

        def trabalho():
            try:
                itens = D.diagnosticar()
            except Exception as exc:  # noqa: BLE001
                itens = [D.ItemDiagnostico("Erro", "Diagnóstico", "falhou", D.ERRO, str(exc))]
            self._fila.put(("diagnostico", itens))

        threading.Thread(target=trabalho, daemon=True).start()

    def _mostrar_diagnostico(self, itens: list[D.ItemDiagnostico]) -> None:
        self.diagnostico = itens
        self._diag_feito = True
        self.btn_diag.state(["!disabled"])
        icones = {D.OK: "✔", D.AVISO: "⚠", D.ERRO: "✖", D.INFO: "•"}
        tags = {D.OK: "ok", D.AVISO: "aviso", D.ERRO: "erro", D.INFO: "info"}
        self.t_diag.limpar()
        for i in itens:
            self.t_diag.inserir([i.grupo, i.nome, f"{icones[i.status]}  {i.valor}", i.detalhe], tags=(tags[i.status],))
        self.t_diag.atualizar_vazio()
        contagem = {s: sum(1 for i in itens if i.status == s) for s in (D.OK, D.AVISO, D.ERRO)}
        self.lbl_diag.configure(
            text=f"{len(itens)} itens verificados às {datetime.now():%H:%M}: {contagem[D.OK]} OK · "
                 f"{contagem[D.AVISO]} aviso(s) · {contagem[D.ERRO]} problema(s).")

    # ---- Testes de velocidade -------------------------------------------------------------

    def _montar_testes(self) -> None:
        rol = Rolavel(self.abas)
        self.abas.add(rol, text="  Testes de velocidade  ")
        area = rol.interno
        topo = tk.Frame(area, bg=T.FUNDO)
        topo.pack(fill="x", pady=(14, 0))
        self.btn_testes = ttk.Button(topo, text="▶  Executar testes", style="Primario.TButton", command=self.rodar_testes)
        self.btn_testes.pack(side="left")
        self.lbl_testes = ttk.Label(topo, text="Testes padronizados (≈10 s) de CPU, memória, disco e rede. Rode em "
                                    "computadores diferentes para comparar.", style="Subtitulo.TLabel")
        self.lbl_testes.pack(side="left", padx=12)
        self.barra_testes = ttk.Progressbar(area, mode="determinate", maximum=100)
        c = Card(area, "Resultados", "Comparação: diferença em relação à média das rodadas anteriores neste computador.")
        c.pack(fill="x", pady=(12, 0))
        self.t_testes = Tabela(c.corpo, [
            ("teste", "Teste", 230, "w"), ("resultado", "Resultado", 190, "e"), ("comparacao", "Comparação", 120, "e"),
            ("detalhe", "Detalhe", 360, "w"),
        ], altura=9, vazio="Clique em “Executar testes”.", selecao="browse", ordenavel=False)
        self.t_testes.pack(fill="x")
        h = Card(area, "Rodadas anteriores", "Guardadas em dados/benchmarks.json.")
        h.pack(fill="x", pady=(12, 14))
        self.t_hist = Tabela(h.corpo, [
            ("data", "Data", 130, "w"), ("pc", "Computador", 140, "w"), ("cpu", "Valid./s", 90, "e"),
            ("sha", "SHA MB/s", 84, "e"), ("plan", "Planilha l/s", 96, "e"),
            ("disco", "Disco MB/s", 90, "e"), ("rede", "Rede ms", 80, "e"),
        ], altura=6, vazio="Nenhuma rodada salva ainda.", selecao="browse", ordenavel=True)
        self.t_hist.pack(fill="x")

    def rodar_testes(self) -> None:
        self.btn_testes.state(["disabled"])
        self.barra_testes.pack(fill="x", pady=(10, 0), after=self.btn_testes.master)
        self.barra_testes.configure(value=0)

        def progresso(i, total, nome):
            self._fila.put(("progresso_testes", (i, total, nome)))

        def trabalho():
            resultados = D.rodar_benchmarks(progresso)
            try:
                D.salvar_benchmark(resultados)
            except OSError:
                pass
            self._fila.put(("testes", resultados))

        threading.Thread(target=trabalho, daemon=True).start()

    def _mostrar_testes(self, resultados: list[D.ResultadoBenchmark]) -> None:
        self.benchmarks = resultados
        self.btn_testes.state(["!disabled"])
        self.barra_testes.pack_forget()
        anteriores = D.carregar_benchmarks()[:-1]
        self.t_testes.limpar()
        for r in resultados:
            valores = [x["valor"] for rodada in anteriores for x in rodada.get("resultados", [])
                       if x.get("chave") == r.chave and x.get("valor")]
            comparacao, tag = "primeira rodada", ""
            if valores and r.valor:
                media = sum(valores) / len(valores)
                delta = (r.valor - media) / media * 100
                melhor = delta > 0 if r.maior_melhor else delta < 0
                comparacao = f"{'+' if delta >= 0 else ''}{_n(delta, 1)} %"
                tag = "sucesso" if melhor and abs(delta) >= 5 else ("erro" if abs(delta) >= 5 else "")
            resultado = f"{_n(r.valor)} {r.unidade}" if r.valor else "—"
            self.t_testes.inserir([r.nome, resultado, comparacao, r.detalhe], tags=(tag,))
        self.t_testes.atualizar_vazio()
        self.lbl_testes.configure(text=f"Concluído às {datetime.now():%H:%M}. Resultado salvo para comparação.")
        self._carregar_historico_testes()

    def _carregar_historico_testes(self) -> None:
        self.t_hist.limpar()
        for rodada in reversed(D.carregar_benchmarks()[-30:]):
            por = {x.get("chave"): x.get("valor", 0) for x in rodada.get("resultados", [])}
            self.t_hist.inserir([rodada.get("data_hora", ""), rodada.get("computador", ""),
                                 _n(por.get("cpu_validacao", 0), 0), _n(por.get("cpu_hash", 0), 0),
                                 _n(por.get("planilha", 0), 0), _n(por.get("disco_escrita", 0), 0),
                                 _n(por.get("rede_dare", 0), 0)])
        self.t_hist.atualizar_vazio()

    # ---- Comum ----------------------------------------------------------------------------

    def _drenar(self) -> None:
        try:
            while True:
                tipo, dados = self._fila.get_nowait()
                if tipo == "amostra":
                    self._nova_amostra(dados)
                elif tipo == "diagnostico":
                    self._mostrar_diagnostico(dados)
                elif tipo == "testes":
                    self._mostrar_testes(dados)
                elif tipo == "progresso_testes":
                    i, total, nome = dados
                    self.barra_testes.configure(value=i / total * 100)
                    self.lbl_testes.configure(text=f"Executando: {nome}…" if i < total else "Concluído.")
        except queue.Empty:
            pass
        self.after(250, self._drenar)

    def _aba_trocada(self, _evento=None) -> None:
        indice = self.abas.index("current")
        if indice == 0:
            self.atualizar_visao_geral()
        elif indice == 2 and not self._diag_feito:
            self.diagnosticar()
        elif indice == 3:
            self._carregar_historico_testes()

    def ao_mostrar(self) -> None:
        self._aba_trocada()

    def exportar_relatorio(self) -> None:
        padrao = f"relatorio_desempenho_{datetime.now():%Y%m%d_%H%M}.html"
        caminho = filedialog.asksaveasfilename(parent=self, title="Salvar relatório de desempenho",
                                               defaultextension=".html", initialfile=padrao,
                                               initialdir=str(config.BASE_DADOS),
                                               filetypes=[("Página HTML", "*.html")])
        if not caminho:
            return
        benchmarks = self.benchmarks
        if not benchmarks:
            rodadas = D.carregar_benchmarks()
            if rodadas:
                benchmarks = [D.ResultadoBenchmark(**x) for x in rodadas[-1].get("resultados", [])]
        try:
            D.gerar_relatorio_html(Path(caminho), self.diagnostico or None, benchmarks or None,
                                   D.analisar_automacao(apenas_sucesso=self.var_so_sucesso.get()))
        except OSError as exc:
            messagebox.showerror(TITULO, f"Não consegui salvar o relatório:\n{exc}", parent=self)
            return
        self.app.toast.mostrar("Relatório gerado. Abrindo no navegador…")
        abrir_no_sistema(caminho)
        if not self.diagnostico:
            self.app.toast.mostrar("Dica: rode o Diagnóstico antes para incluí-lo no relatório.", "info", 5000)

    def exportar_csv(self) -> None:
        if not config.ARQ_DESEMPENHO.exists():
            messagebox.showinfo(TITULO, "Ainda não há medições para exportar. Elas são gravadas a cada lançamento "
                                        "processado pelo aplicativo.", parent=self)
            return
        caminho = filedialog.asksaveasfilename(parent=self, title="Exportar medições (abre no Excel)",
                                               defaultextension=".csv", initialfile="desempenho_dare.csv",
                                               filetypes=[("CSV (Excel)", "*.csv")])
        if caminho:
            shutil.copyfile(config.ARQ_DESEMPENHO, caminho)
            self.app.toast.mostrar("Medições exportadas.")
