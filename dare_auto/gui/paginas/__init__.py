"""Páginas do aplicativo, na ordem em que aparecem na barra lateral."""

from .arquivos import PaginaArquivos
from .configuracoes import PaginaConfiguracoes
from .desempenho import PaginaDesempenho
from .execucao import PaginaExecucao
from .inicio import PaginaInicio
from .lancamentos import PaginaLancamentos

PAGINAS = [
    ("inicio", PaginaInicio),
    ("lancamentos", PaginaLancamentos),
    ("execucao", PaginaExecucao),
    ("arquivos", PaginaArquivos),
    ("desempenho", PaginaDesempenho),
    ("configuracoes", PaginaConfiguracoes),
]
