"""Passos no SEI: abrir o processo e incluir o PDF como documento externo."""

import logging
from datetime import date
from pathlib import Path

from . import config, navegador
from .modelos import DadosDare
from .navegador import achar_visivel

log = logging.getLogger("dare.sei")


def anexar_pdf(context, page_sei, dados: DadosDare, caminho_pdf: Path):
    """Abre o processo no SEI e inclui `caminho_pdf` como documento externo. Devolve a aba do SEI."""
    # 5.0 Troca para a aba do SEI (em vez de abrir a página de novo)
    log.info("SEI 1/4 · Abrindo o processo %s", dados.processo)
    page_sei = navegador.garantir_aba(context, page_sei, config.HOST_SEI, config.URL_SEI)
    navegador.ativar_aba(context, page_sei)
    page_sei.locator('img[title="Controle de Processos"]:visible').first.click()
    page_sei.locator("#txtPesquisaRapida").wait_for(state="visible")
    page_sei.locator("#txtPesquisaRapida").fill(dados.processo)
    page_sei.locator('img[title="Pesquisa Rápida"]:visible').first.click()

    # 5.1 Reabrir (se estiver fechado) e incluir documento
    log.info("SEI 2/4 · Incluindo documento")
    # Espera a barra de ações do processo carregar (dentro dos iframes do SEI).
    # Processo fechado mostra "Reabrir Processo"; aberto mostra "Incluir Documento".
    acao = achar_visivel(
        page_sei, 'img[title="Reabrir Processo"], img[title="Incluir Documento"]'
    )
    if acao.get_attribute("title") == "Reabrir Processo":
        log.info("Processo fechado: reabrindo.")
        acao.click()
    achar_visivel(page_sei, 'img[title="Incluir Documento"]').click()

    # 5.2 Documento externo
    log.info("SEI 3/4 · Documento externo (série %s)", config.SERIE_SEI)
    # Cada passo procura de novo nos frames, pois o SEI recarrega o iframe a cada tela.
    achar_visivel(page_sei, 'a[onclick="escolher(-1)"]').click()
    achar_visivel(page_sei, "#selSerie").select_option(config.SERIE_SEI)
    # Data de elaboração: preenchida automaticamente com a data de hoje (DD/MM/AAAA)
    navegador.preencher_data_hoje(page_sei)
    log.info("Data de elaboração preenchida: %s", date.today().strftime("%d/%m/%Y"))
    achar_visivel(page_sei, f'label[for="{config.RADIO_NATO_DIGITAL}"]').click()

    # Anexa o PDF do DARE que acabou de ser gerado, sem precisar arrastar
    log.info("SEI 4/4 · Anexando %s e salvando", caminho_pdf.name)
    achar_visivel(page_sei, "input#filArquivo", exigir_visivel=False).set_input_files(
        str(caminho_pdf)
    )
    achar_visivel(page_sei, "#btnSalvar").click()
    log.info("Documento externo salvo no SEI.")
    return page_sei
