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
ARQ_LOTE = PASTA_DADOS / "lote_pendente.json"  # lançamentos em lote ainda não concluídos
ARQ_MAPEAMENTOS = PASTA_DADOS / "mapeamentos_planilha.json"  # colunas escolhidas por planilha/aba
PASTA_MODELOS = RAIZ / "modelos"  # planilha modelo gerada pelo programa

# ---- Chrome em modo depuração -------------------------------------------------------------
PORTA_CDP = 9222
CDP_URL = f"http://127.0.0.1:{PORTA_CDP}"
# Perfil próprio do Chrome de depuração (o login nos sistemas fica salvo aqui).
PERFIL_CHROME = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "DARE_Chrome_Perfil"
# Para usar outro Chrome, defina a variável de ambiente DARE_CHROME_PATH com o caminho do chrome.exe.
ESPERA_CHROME = 30  # segundos esperando o Chrome abrir a porta de depuração

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
