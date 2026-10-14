"""Configurações centrais do projeto. Ajuste aqui URLs, códigos fixos e pastas."""

import os
from pathlib import Path

# Pasta do projeto (a que contém dare_automacao.py)
RAIZ = Path(__file__).resolve().parent.parent

# ---- Pastas e arquivos -------------------------------------------------------------------
# PDFs gerados. Para usar outra pasta, defina a variável de ambiente DARE_PASTA_PDF.
PASTA_PDF = Path(os.environ.get("DARE_PASTA_PDF") or RAIZ / "DARE_PDFs")
PASTA_LOGS = RAIZ / "logs"
PASTA_ERROS = PASTA_LOGS / "erros"  # capturas de tela quando algo falha
PASTA_DADOS = RAIZ / "dados"
ARQ_LOG = PASTA_LOGS / "dare_automacao.log"
ARQ_ULTIMOS = PASTA_DADOS / "ultimos_dados.json"  # últimos dados digitados (viram padrão)
ARQ_HISTORICO = PASTA_DADOS / "historico.csv"  # um registro por execução

# ---- Chrome em modo depuração -------------------------------------------------------------
PORTA_CDP = 9222
CDP_URL = f"http://127.0.0.1:{PORTA_CDP}"

# ---- Sites --------------------------------------------------------------------------------
URL_DARE = "https://dare.sefin.ro.gov.br/avulso"
URL_SEI = "https://sei.sistemas.ro.gov.br/sip/login.php?sigla_orgao_sistema=RO&sigla_sistema=SEI"
HOST_DARE = "dare.sefin.ro.gov.br"
HOST_SEI = "sei.sistemas.ro.gov.br"

# ---- Valores fixos do DARE ----------------------------------------------------------------
ORGAO = "SEGEP - SUPERINTENDÊNCIA ESTADUAL DE GESTÃO DE PESSOAS"
CODIGO_RECEITA = "7155"
UNIDADE_GESTORA = "160001"
GESTAO = "00001"
VALOR_PADRAO = "100,00"

# ---- Valores fixos do SEI -----------------------------------------------------------------
SERIE_SEI = "310"  # tipo do documento externo
RADIO_NATO_DIGITAL = "optNato"  # id do rádio "Nato-digital"

# ---- Tempos (segundos) --------------------------------------------------------------------
TIMEOUT_ELEMENTO = 30
TIMEOUT_IMPRESSAO = 10
