"""Teste de fumaça da janela: abre o aplicativo, passa por todas as páginas e fecha (sem navegador)."""

import os
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from dare_auto import config, navegador
from dare_auto.modelos import DadosDare

try:
    import tkinter as tk
    _raiz = tk.Tk()
    _raiz.destroy()
    TEM_TELA = True
except Exception:  # noqa: BLE001 - sem tela (servidor) ou sem Tkinter
    TEM_TELA = False


@unittest.skipUnless(TEM_TELA, "sem tela disponível para abrir janelas")
class TestJanela(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        alvos = {
            "BASE_DADOS": base, "PASTA_DADOS": base / "dados", "PASTA_PDF": base / "pdf",
            "PASTA_LOGS": base / "logs", "ARQ_ULTIMOS": base / "dados" / "u.json",
            "ARQ_HISTORICO": base / "dados" / "h.csv", "ARQ_LOTE": base / "dados" / "l.json",
            "ARQ_PREFERENCIAS": base / "dados" / "p.json", "ARQ_DESEMPENHO": base / "dados" / "d.csv",
            "ARQ_BENCHMARKS": base / "dados" / "b.json", "PASTA_PDF_PADRAO": base / "pdf",
        }
        for nome, valor in alvos.items():
            p = mock.patch.object(config, nome, valor)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(navegador, "chrome_debug_ativo", lambda timeout=0.4: False)
        p.start()
        self.addCleanup(p.stop)
        os.environ.pop("DARE_PASTA_PDF", None)

    def test_abre_todas_as_paginas(self):
        from dare_auto.gui.app import Aplicacao
        app = Aplicacao()
        try:
            app.pref.abrir_navegador_ao_iniciar = False
            app.lotes = [DadosDare("0029.000001/2026-01", "11222333000181", "52998224725", "11222333000181",
                                   "102026", date(2026, 11, 10), "100,00")]
            for chave in app.paginas:
                app.mostrar(chave)
                app.update_idletasks()
            lanc = app.paginas["lancamentos"]
            lanc.c_processo.var.set("0029.000002/2026-02")
            lanc.c_cpf.var.set("52998224725")
            lanc.salvar()
            self.assertEqual(len(app.lotes), 2)
            self.assertEqual(app.lotes[1].processo, "0029.000002/2026-02")
            lanc.c_cpf.var.set("123")
            self.assertIsNone(lanc.c_cpf.conferir())
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
