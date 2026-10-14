"""Logs: arquivo rotativo completo (logs/dare_automacao.log) + console enxuto e colorido."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from . import config

NOME = "dare"

_CORES = {
    logging.DEBUG: "\033[2m",
    logging.INFO: "",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[1;31m",
}


class _FormatoConsole(logging.Formatter):
    def __init__(self, usar_cor: bool):
        super().__init__()
        self.usar_cor = usar_cor

    def format(self, record: logging.LogRecord) -> str:
        hora = self.formatTime(record, "%H:%M:%S")
        msg = record.getMessage()
        if not self.usar_cor:
            return f"  {hora}  {msg}"
        return f"  \033[2m{hora}\033[0m  {_CORES.get(record.levelno, '')}{msg}\033[0m"


def configurar(nivel_console: int = logging.INFO) -> logging.Logger:
    """Configura (uma única vez) os logs do projeto e devolve o logger raiz 'dare'."""
    log = logging.getLogger(NOME)
    if log.handlers:
        return log
    log.setLevel(logging.DEBUG)
    log.propagate = False

    config.PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    arquivo = RotatingFileHandler(
        config.ARQ_LOG, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    arquivo.setLevel(logging.DEBUG)
    arquivo.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    log.addHandler(arquivo)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(nivel_console)
    console.setFormatter(_FormatoConsole(sys.stdout.isatty()))
    log.addHandler(console)
    return log
