"""
DARE automação — ponto de entrada.

Gera o DARE avulso, salva o PDF e o anexa como documento externo no processo do SEI.
Funciona para um lançamento (opção 1) ou para vários, em lote (opção 2).
Uso:  python dare_automacao.py      (ou dê dois cliques em executar.bat)
Veja o README.md para o passo a passo.
"""

import logging
import os
import sys
from datetime import date

try:
    from playwright.sync_api import sync_playwright

    from dare_auto import armazenamento, config, dare, logger, menu, navegador, sei, utils
    from dare_auto.modelos import DadosDare, ResultadoLote
except ImportError as exc:  # dependência não instalada
    sys.exit(
        f"Falta instalar uma dependência ({exc}).\n"
        "Rode:  pip install -r requirements.txt"
    )

log = logging.getLogger("dare.main")

# Lembra, durante a execução do programa, se você já confirmou o login nos dois sistemas.
_estado = {"login_confirmado": False}


def _resumo_erro(exc: BaseException) -> str:
    texto = str(exc)
    return f"{type(exc).__name__}: {texto.splitlines()[0] if texto else ''}"


def _observacao(rotulo: str, extra: str = "") -> str:
    return " · ".join(p for p in (rotulo, extra) if p)[:300]


def executar_lotes(lotes: list[DadosDare]) -> tuple[list[ResultadoLote], bool]:
    """
    Processa os lançamentos em sequência, do primeiro ao último, numa única conexão com o Chrome.
    Cada lançamento percorre o fluxo completo (DARE -> PDF -> SEI). Se um falhar, o erro é
    registrado e o loop SEGUE para o próximo. Um lançamento avulso é um lote de tamanho 1.

    Devolve (resultados na ordem processada, interrompido). `interrompido` é True se o usuário
    cancelou com Ctrl+C; então os lotes que sobraram não foram processados.
    """
    total = len(lotes)
    resultados: list[ResultadoLote] = []
    interrompido = False
    try:
        with sync_playwright() as p:
            _, context = navegador.conectar(p)
            # Impede que o diálogo de impressão do Chrome abra e trave a automação;
            # o PDF é gerado diretamente por navegador.salvar_pdf(). Só vale para o DARE.
            context.add_init_script(
                f"if (location.hostname.includes('{config.HOST_DARE}')) "
                "window.print = () => {};"
            )

            # Abre/localiza as DUAS abas no mesmo Chrome em modo debug:
            # SEI primeiro e DARE por último, para o DARE ficar em foco.
            page_sei, _ = navegador.obter_aba(context, config.HOST_SEI, config.URL_SEI)
            page, dare_criada = navegador.obter_aba(context, config.HOST_DARE, config.URL_DARE)
            navegador.ativar_aba(context, page)
            if not dare_criada:
                page.goto(config.URL_DARE)
            page.wait_for_load_state("networkidle")

            if not _estado["login_confirmado"]:
                menu.aguardar_login()
                _estado["login_confirmado"] = True

            for i, dados in enumerate(lotes, 1):
                rotulo = f"Lote {i}/{total}" if total > 1 else ""
                if total > 1:
                    menu.cabecalho_lote(i, total, dados)
                armazenamento.salvar_ultimos(dados)  # se falhar, dá para repetir sem redigitar
                log.info(
                    "=== %s · processo %s · CPF %s · venc %s · R$ %s ===",
                    rotulo or "Nova execução", dados.processo, utils.mascarar_cpf(dados.cpf),
                    dados.vencimento.strftime("%d/%m/%Y"), dados.valor,
                )
                servidor, pdf = "", ""
                try:
                    # Você pode ter ficado na aba do SEI: procura de novo a do DARE e a traz à frente.
                    page = navegador.garantir_aba(context, page, config.HOST_DARE, config.URL_DARE)
                    navegador.ativar_aba(context, page)
                    if i > 1:  # a partir do 2º lote, volta ao formulário em branco do DARE
                        page.goto(config.URL_DARE)
                    page.wait_for_load_state("networkidle")

                    caminho_pdf, servidor = dare.gerar_dare(context, page, dados)
                    pdf = str(caminho_pdf)
                    page_sei = sei.anexar_pdf(context, page_sei, dados, caminho_pdf)
                except KeyboardInterrupt:
                    log.warning("%s cancelado pelo usuário.", rotulo or "Execução")
                    armazenamento.registrar_historico(
                        dados, "CANCELADO", servidor, pdf, _observacao(rotulo)
                    )
                    raise
                except Exception as exc:  # noqa: BLE001 - registra e segue para o próximo lote
                    navegador.capturar_erro(context)
                    log.exception("Falha em %s", rotulo or "execução")
                    resumo = _resumo_erro(exc)
                    armazenamento.registrar_historico(
                        dados, "ERRO", servidor, pdf, _observacao(rotulo, resumo)
                    )
                    resultados.append(ResultadoLote(dados, False, pdf, servidor, resumo))
                    if os.environ.get("DARE_DEBUG"):
                        raise  # no depurador do VS Code, para exatamente onde deu o erro
                    if total > 1:
                        menu.erro(f"{rotulo} falhou ({resumo}). Seguindo para o próximo...")
                    continue

                armazenamento.registrar_historico(
                    dados, "SUCESSO", servidor, pdf, _observacao(rotulo)
                )
                resultados.append(ResultadoLote(dados, True, pdf, servidor))
                if total > 1:
                    menu.sucesso(f"{rotulo} concluído.")
    except KeyboardInterrupt:
        interrompido = True
    except Exception as exc:  # noqa: BLE001
        if os.environ.get("DARE_DEBUG"):
            raise
        # Falha geral (ex.: Chrome fechado): os lotes que faltavam ficam com este erro.
        log.exception("Falha geral na execução")
        resumo = _resumo_erro(exc)
        for i, dados in enumerate(lotes[len(resultados):], len(resultados) + 1):
            rotulo = f"Lote {i}/{total}" if total > 1 else ""
            armazenamento.registrar_historico(dados, "ERRO", "", "", _observacao(rotulo, resumo))
            resultados.append(ResultadoLote(dados, False, "", "", resumo))

    log.info(
        "=== Fim: %s de %s com sucesso%s ===",
        sum(r.sucesso for r in resultados), total, " (interrompido)" if interrompido else "",
    )
    return resultados, interrompido


def _rodar(dados: DadosDare | None) -> None:
    """Um único lançamento (opções 1 e 3)."""
    if dados is not None and menu.confirmar(dados):
        resultados, interrompido = executar_lotes([dados])
        if interrompido:
            menu.aviso("Cancelado.")
        elif resultados and resultados[0].sucesso:
            menu.resultado_sucesso(resultados[0].pdf)
        elif resultados:
            menu.resultado_erro(resultados[0].erro)
    menu.pausar("Pressione Enter para voltar ao menu...")


def _rodar_lotes(lotes: list[DadosDare]) -> None:
    """Vários lançamentos (opção 2): roda todos e oferece repetir só os que falharam."""
    armazenamento.salvar_lote(lotes)  # lote pendente: sobrevive a erro, Ctrl+C ou queda do PC
    pendentes = list(lotes)
    while pendentes:
        rodada = pendentes
        resultados, interrompido = executar_lotes(rodada)
        # Pendentes = os que falharam + os que nem chegaram a ser processados.
        pendentes = [d for d, r in zip(rodada, resultados) if not r.sucesso] + \
            rodada[len(resultados):]
        menu.resumo_lotes(resultados, len(rodada))
        if interrompido or not pendentes:
            break
        if not menu.sim_nao(f"Tentar de novo os {len(pendentes)} lote(s) com erro?", padrao=False):
            break
    if pendentes:
        armazenamento.salvar_lote(pendentes)
        menu.info(f"{len(pendentes)} lançamento(s) pendente(s) guardado(s): "
                  "a opção 2 oferece retomá-los.")
    else:
        armazenamento.limpar_lote()
    menu.pausar("Pressione Enter para voltar ao menu...")


def _opcao_lotes(ultimos: DadosDare | None) -> None:
    pendentes = armazenamento.carregar_lote()
    if pendentes and menu.sim_nao(
        f"Há {len(pendentes)} lançamento(s) pendente(s) de uma execução anterior. "
        "Retomar? (Não = descartar e começar um lote novo)", padrao=True,
    ):
        lotes = pendentes
    else:
        lotes = menu.coletar_lotes(ultimos)
        armazenamento.salvar_lote(lotes)  # guarda já: não perde o que foi digitado
    if menu.confirmar_lotes(lotes):
        _rodar_lotes(lotes)


def main() -> None:
    menu.preparar_terminal()
    logger.configurar()
    log.info("Programa iniciado (Python %s).", sys.version.split()[0])

    while True:
        ultimos = armazenamento.carregar_ultimos()
        try:
            escolha = menu.menu_principal(navegador.chrome_debug_ativo(), ultimos is not None)
        except (KeyboardInterrupt, EOFError):
            break
        if escolha == "0":
            break
        try:
            if escolha == "1":
                _rodar(menu.coletar_dados(ultimos))
            elif escolha == "2":
                _opcao_lotes(ultimos)
            elif escolha == "3":
                if ultimos is None:
                    menu.aviso("Ainda não há dados salvos. Use a opção 1.")
                    menu.pausar()
                    continue
                if ultimos.vencimento < date.today():  # vencimento antigo não serve de padrão
                    ultimos.vencimento = utils.vencimento_padrao()
                _rodar(ultimos)
            elif escolha == "4":
                menu.mostrar_historico(armazenamento.ler_historico())
                menu.pausar()
            elif escolha == "5":
                menu.abrir_pasta(config.PASTA_PDF)
                menu.pausar()
            elif escolha == "6":
                menu.abrir_pasta(config.PASTA_LOGS)
                menu.pausar()
        except (KeyboardInterrupt, EOFError):
            menu.aviso("Cancelado.")
            menu.pausar()

    log.info("Programa encerrado.")
    print("\n  Até logo!\n")


if __name__ == "__main__":
    main()
