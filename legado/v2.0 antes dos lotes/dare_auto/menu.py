"""Interface de terminal: banner, menu, perguntas com validação, resumo e mensagens."""

import os
import re
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

from . import config, utils
from .modelos import DadosDare

LARGURA = 66  # largura total das caixas

_USAR_COR = False
RESET, NEGRITO, DIM = "\033[0m", "\033[1m", "\033[2m"
VERMELHO, VERDE, AMARELO, CIANO = "\033[31m", "\033[32m", "\033[33m", "\033[36m"
_ANSI = re.compile(r"\033\[[0-9;]*m")


def preparar_terminal() -> None:
    """UTF-8 na saída e cores ANSI (inclusive no Windows 10+). Sem cor se não for um terminal."""
    global _USAR_COR
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.name == "nt":
        os.system("")  # habilita sequências ANSI no console do Windows
    _USAR_COR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(texto: str, *estilos: str) -> str:
    return "".join(estilos) + texto + RESET if _USAR_COR and estilos else texto


def _tamanho(texto: str) -> int:
    return len(_ANSI.sub("", texto))


def limpar() -> None:
    if _USAR_COR:
        print("\033[2J\033[H", end="")


# ---- Blocos visuais -----------------------------------------------------------------------

def banner() -> None:
    interno = LARGURA - 2
    titulo = "DARE AUTOMAÇÃO"
    sub = "gerar DARE  →  salvar PDF  →  anexar no SEI"
    print(_c("╔" + "═" * interno + "╗", CIANO))
    for texto, estilo in ((titulo, NEGRITO), (sub, DIM)):
        meio = texto.center(interno)
        print(_c("║", CIANO) + _c(meio, estilo) + _c("║", CIANO))
    print(_c("╚" + "═" * interno + "╝", CIANO))


def caixa(titulo: str, linhas: list[str], cor: str = CIANO) -> None:
    """Caixa com título; cada linha é um texto simples (quebra automática)."""
    interno = LARGURA - 4
    topo = f"┌─ {titulo} " + "─" * (LARGURA - 5 - len(titulo)) + "┐"
    print(_c(topo, cor))
    for linha in linhas:
        pedacos = textwrap.wrap(linha, interno) or [""]
        for p in pedacos:
            print(_c("│", cor) + " " + p.ljust(interno) + " " + _c("│", cor))
    print(_c("└" + "─" * (LARGURA - 2) + "┘", cor))


def caixa_campos(titulo: str, campos: list[tuple[str, str]], cor: str = CIANO) -> None:
    """Caixa de pares rótulo/valor alinhados."""
    interno = LARGURA - 4
    largura_rotulo = max(len(r) for r, _ in campos) + 2
    topo = f"┌─ {titulo} " + "─" * (LARGURA - 5 - len(titulo)) + "┐"
    print(_c(topo, cor))
    for rotulo, valor in campos:
        pedacos = textwrap.wrap(str(valor), interno - largura_rotulo) or [""]
        for i, p in enumerate(pedacos):
            esq = (rotulo + ":").ljust(largura_rotulo) if i == 0 else " " * largura_rotulo
            conteudo = _c(esq, DIM) + p
            falta = interno - _tamanho(conteudo)
            print(_c("│", cor) + " " + conteudo + " " * falta + " " + _c("│", cor))
    print(_c("└" + "─" * (LARGURA - 2) + "┘", cor))


def info(msg: str) -> None:
    print(f"  {_c('ℹ', CIANO)} {msg}")


def sucesso(msg: str) -> None:
    print(f"  {_c('✔', VERDE)} {msg}")


def aviso(msg: str) -> None:
    print(f"  {_c('⚠', AMARELO)} {msg}")


def erro(msg: str) -> None:
    print(f"  {_c('✖', VERMELHO)} {msg}")


def pausar(msg: str = "Pressione Enter para continuar...") -> None:
    input(f"\n  {_c(msg, DIM)}")


# ---- Menu principal -----------------------------------------------------------------------

def menu_principal(chrome_ok: bool, tem_ultimos: bool) -> str:
    """Mostra o menu e devolve a opção escolhida ('1'..'5' ou '0')."""
    limpar()
    banner()
    chrome = _c("● conectado", VERDE) if chrome_ok else _c("● não encontrado", VERMELHO)
    print(f"\n  Chrome (porta {config.PORTA_CDP}): {chrome}")
    print(f"  Pasta dos PDFs: {_c(str(config.PASTA_PDF), DIM)}\n")
    opcoes = [
        ("1", "Novo DARE e anexar no SEI"),
        ("2", "Repetir os últimos dados" + ("" if tem_ultimos else "  (indisponível)")),
        ("3", "Ver histórico das últimas execuções"),
        ("4", "Abrir a pasta dos PDFs"),
        ("5", "Abrir a pasta de logs"),
        ("0", "Sair"),
    ]
    for chave, texto in opcoes:
        print(f"   {_c(chave, NEGRITO, CIANO)}  {texto}")
    if not chrome_ok:
        print()
        aviso("Abra o Chrome com 'iniciar_chrome_debug.bat' antes de iniciar um DARE.")
    validas = {c for c, _ in opcoes}
    while True:
        escolha = input(f"\n  {_c('›', CIANO)} Escolha uma opção: ").strip()
        if escolha in validas:
            return escolha
        erro("Opção inválida.")


# ---- Perguntas ----------------------------------------------------------------------------

def _perguntar(rotulo, ajuda="", padrao="", exibir_padrao=None, validar=None):
    while True:
        if ajuda:
            print(f"     {_c(ajuda, DIM)}")
        dica = ""
        if padrao:
            dica = " " + _c(f"[Enter = {exibir_padrao or padrao}]", DIM)
        resposta = input(f"  {_c('›', CIANO)} {rotulo}{dica}: ").strip()
        valor = resposta or padrao
        if not valor:
            erro("Campo obrigatório.")
            continue
        if validar is None:
            return valor
        try:
            return validar(valor)
        except ValueError as exc:
            erro(str(exc))


def _doc(validador, nome, digitos):
    def verificar(texto):
        d = utils.somente_digitos(texto)
        if len(d) != digitos:
            raise ValueError(f"{nome} deve ter {digitos} dígitos.")
        if not validador(texto):
            raise ValueError(f"{nome} inválido (dígitos verificadores não conferem).")
        return texto.strip()

    return verificar


def _processo(texto):
    if len(utils.somente_digitos(texto)) < 6:
        raise ValueError("Informe o número do processo (ex.: 0012.123456/2026-12).")
    return texto.strip()


def _valor(texto):
    return utils.formatar_valor(texto)


def coletar_dados(ultimos: DadosDare | None) -> DadosDare:
    """Faz as perguntas. Enter reaproveita o último valor digitado (quando existir)."""
    limpar()
    banner()
    print()
    caixa(
        "Novo DARE",
        [
            "Preencha os dados. Enter aceita o valor entre colchetes.",
            "Ctrl+C a qualquer momento cancela e volta ao menu.",
        ],
    )
    print()
    u = ultimos
    processo = _perguntar(
        "Processo SEI", "Número do processo que receberá o DARE.",
        padrao=u.processo if u else "", validar=_processo,
    )
    cnpj = _perguntar(
        "CNPJ (órgão)", "Usado para identificar o contribuinte no DARE.",
        padrao=u.cnpj if u else "", validar=_doc(utils.validar_cnpj, "CNPJ", 14),
    )
    cpf = _perguntar(
        "CPF do servidor", "",
        padrao=u.cpf if u else "", validar=_doc(utils.validar_cpf, "CPF", 11),
    )
    recolhedor = _perguntar(
        "CNPJ do recolhedor", "",
        padrao=u.cnpj_recolhedor if u else "", validar=_doc(utils.validar_cnpj, "CNPJ", 14),
    )
    referencia = _perguntar(
        "Mês/ano de referência", "Formato MMAAAA (ex.: 102026).",
        padrao=u.mes_ano_referencia if u else "", validar=utils.validar_mes_ano,
        exibir_padrao=utils.formatar_mes_ano(u.mes_ano_referencia) if u else None,
    )
    sugestao = utils.vencimento_padrao()
    vencimento = _perguntar(
        "Data de vencimento", "DD/MM/AAAA. Padrão: 1 mês à frente, em dia útil.",
        padrao=sugestao.strftime("%d/%m/%Y"), validar=utils.ler_vencimento,
    )
    valor = _perguntar(
        "Valor (R$)", "Ex.: 100,00 — a vírgula é colocada automaticamente no site.",
        padrao=u.valor if u else config.VALOR_PADRAO, validar=_valor,
    )
    return DadosDare(processo, cnpj, cpf, recolhedor, referencia, vencimento, valor)


def confirmar(dados: DadosDare) -> bool:
    """Mostra o resumo e pergunta se pode iniciar."""
    if dados.vencimento < date.today():
        aviso("A data de vencimento está no passado.")
    print()
    caixa_campos(
        "Confira os dados",
        [
            ("Processo SEI", dados.processo),
            ("CNPJ (órgão)", utils.formatar_cnpj(dados.cnpj)),
            ("CPF do servidor", utils.formatar_cpf(dados.cpf)),
            ("CNPJ recolhedor", utils.formatar_cnpj(dados.cnpj_recolhedor)),
            ("Referência", utils.formatar_mes_ano(dados.mes_ano_referencia)),
            ("Vencimento", dados.vencimento.strftime("%d/%m/%Y")),
            ("Valor", f"R$ {dados.valor}"),
        ],
    )
    print()
    caixa_campos(
        "Fixos (config.py)",
        [
            ("Órgão", config.ORGAO),
            ("Receita", config.CODIGO_RECEITA),
            ("Unid. gestora / Gestão", f"{config.UNIDADE_GESTORA} / {config.GESTAO}"),
        ],
        cor=DIM,
    )
    resposta = input(f"\n  {_c('›', CIANO)} Iniciar? [S/n]: ").strip().lower()
    return resposta in ("", "s", "sim", "y", "yes")


def aguardar_login() -> None:
    print()
    caixa(
        "Antes de continuar",
        [
            "1. Na aba do DARE e na aba do SEI, entre com a sua conta.",
            "2. Quando as duas estiverem logadas, volte aqui.",
            "O script troca de aba sozinho; não precisa deixar nenhuma em foco.",
        ],
        cor=AMARELO,
    )
    pausar("Pressione Enter quando estiver logado nos dois sistemas...")
    print()


# ---- Resultados ---------------------------------------------------------------------------

def resultado_sucesso(pdf: Path) -> None:
    print()
    caixa("Concluído", ["DARE gerado e anexado no SEI.", f"PDF: {pdf}"], cor=VERDE)


def resultado_erro(resumo: str) -> None:
    print()
    caixa(
        "Falhou",
        [
            resumo,
            f"Detalhes no log: {config.ARQ_LOG}",
            f"Capturas de tela: {config.PASTA_ERROS}",
            "Seus dados foram salvos: use 'Repetir os últimos dados' para tentar de novo.",
        ],
        cor=VERMELHO,
    )


def mostrar_historico(linhas: list[dict]) -> None:
    limpar()
    banner()
    print()
    if not linhas:
        info("Nenhuma execução registrada ainda.")
        return
    caixa("Últimas execuções", [f"Arquivo: {config.ARQ_HISTORICO}"])
    print()
    for l in linhas:
        ok = l.get("status") == "SUCESSO"
        marca = _c("✔", VERDE) if ok else _c("✖", VERMELHO)
        servidor = (l.get("servidor") or "—")[:28]
        print(
            f"  {marca} {l.get('data_hora', '')}  {servidor:<28}  "
            f"venc {l.get('vencimento', '')}  R$ {l.get('valor', '')}"
        )
        if not ok and l.get("observacao"):
            print(f"      {_c(l['observacao'][:LARGURA - 8], DIM)}")


def abrir_pasta(pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            os.startfile(pasta)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(pasta)], check=False)
        else:
            subprocess.run(["xdg-open", str(pasta)], check=False)
        sucesso(f"Pasta aberta: {pasta}")
    except Exception as exc:  # noqa: BLE001
        erro(f"Não consegui abrir a pasta ({exc}). Caminho: {pasta}")
