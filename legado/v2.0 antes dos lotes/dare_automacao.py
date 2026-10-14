"""
DARE automação — ponto de entrada.

Gera o DARE avulso, salva o PDF e o anexa como documento externo no processo do SEI.
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
    from dare_auto.modelos import DadosDare
except ImportError as exc:  # dependência não instalada
    sys.exit(
        f"Falta instalar uma dependência ({exc}).\n"
        "Rode:  pip install -r requirements.txt"
    )

log = logging.getLogger("dare.main")

# Lembra, durante a execução do programa, se você já confirmou o login nos dois sistemas.
_estado = {"login_confirmado": False}


def executar(dados: DadosDare) -> bool:
    """Roda o fluxo completo para um DARE. Devolve True se terminou sem erros."""
    armazenamento.salvar_ultimos(dados)  # salva antes: se falhar, dá para repetir sem redigitar
    log.info(
        "=== Nova execução · processo %s · CPF %s · venc %s · R$ %s ===",
        dados.processo, utils.mascarar_cpf(dados.cpf),
        dados.vencimento.strftime("%d/%m/%Y"), dados.valor,
    )
    servidor, pdf = "", ""
    try:
        with sync_playwright() as p:
            _, context = navegador.conectar(p)
            try:
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

                # Você pode ter ficado na aba do SEI: procura de novo a do DARE e a traz à frente.
                page = navegador.garantir_aba(context, page, config.HOST_DARE, config.URL_DARE)
                navegador.ativar_aba(context, page)
                page.wait_for_load_state("networkidle")

                caminho_pdf, servidor = dare.gerar_dare(context, page, dados)
                pdf = str(caminho_pdf)
                sei.anexar_pdf(context, page_sei, dados, caminho_pdf)
            except Exception:
                navegador.capturar_erro(context)
                raise
    except KeyboardInterrupt:
        log.warning("Execução cancelada pelo usuário.")
        armazenamento.registrar_historico(dados, "CANCELADO", servidor, pdf)
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("Falha na execução")
        resumo = f"{type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}"
        armazenamento.registrar_historico(dados, "ERRO", servidor, pdf, resumo[:300])
        menu.resultado_erro(resumo)
        if os.environ.get("DARE_DEBUG"):
            raise  # no depurador do VS Code, para parar exatamente onde deu o erro
        return False

    armazenamento.registrar_historico(dados, "SUCESSO", servidor, pdf)
    log.info("=== Execução concluída ===")
    menu.resultado_sucesso(pdf)
    return True


def _rodar(dados: DadosDare | None) -> None:
    if dados is not None and menu.confirmar(dados):
        executar(dados)
    menu.pausar("Pressione Enter para voltar ao menu...")


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
                if ultimos is None:
                    menu.aviso("Ainda não há dados salvos. Use a opção 1.")
                    menu.pausar()
                    continue
                if ultimos.vencimento < date.today():  # vencimento antigo não serve de padrão
                    ultimos.vencimento = utils.vencimento_padrao()
                _rodar(ultimos)
            elif escolha == "3":
                menu.mostrar_historico(armazenamento.ler_historico())
                menu.pausar()
            elif escolha == "4":
                menu.abrir_pasta(config.PASTA_PDF)
                menu.pausar()
            elif escolha == "5":
                menu.abrir_pasta(config.PASTA_LOGS)
                menu.pausar()
        except (KeyboardInterrupt, EOFError):
            menu.aviso("Cancelado.")
            menu.pausar()

    log.info("Programa encerrado.")
    print("\n  Até logo!\n")


if __name__ == "__main__":
    main()
