import base64
import calendar
import re
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

URL_DARE = "https://dare.sefin.ro.gov.br/avulso"

URL_SEI = "https://sei.sistemas.ro.gov.br/sip/login.php?sigla_orgao_sistema=RO&sigla_sistema=SEI"

HOST_DARE = "dare.sefin.ro.gov.br"
HOST_SEI = "sei.sistemas.ro.gov.br"

# Pasta onde os PDFs dos DAREs serão salvos (ao lado deste script)
PASTA_PDF = Path(__file__).resolve().parent / "DARE_PDFs"

VALOR_PADRAO = "100,00"

MESES = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]


# ========= FUNÇÕES AUXILIARES =========

def somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def proximo_dia_util(d: date) -> date:
    """Se cair em sábado ou domingo, avança para a segunda-feira."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def vencimento_padrao(hoje: date | None = None) -> date:
    """Um mês depois de hoje, ajustado para um dia útil (não considera feriados)."""
    hoje = hoje or date.today()
    mes = hoje.month % 12 + 1
    ano = hoje.year + (1 if hoje.month == 12 else 0)
    dia = min(hoje.day, calendar.monthrange(ano, mes)[1])
    return proximo_dia_util(date(ano, mes, dia))


def ler_vencimento(texto: str) -> date:
    """Lê DD/MM/AAAA; se vazio, usa o vencimento padrão."""
    texto = texto.strip()
    if not texto:
        return vencimento_padrao()
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError("Data de vencimento inválida. Use o formato DD/MM/AAAA.")


def valor_para_digitos(texto: str) -> str:
    """
    Converte o valor digitado em centavos, sem vírgula (o site coloca a vírgula sozinho).
    '100,00' -> '10000' | '1.500,5' -> '150050' | '100' -> '10000'
    """
    texto = (texto.strip() or VALOR_PADRAO).replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError("Valor inválido. Exemplo: 100,00")
    if valor <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    return str(int((valor * 100).to_integral_value()))


def selecionar_data_no_picker(page, alvo: date):
    """Abre o seletor de datas, navega até o mês/ano desejado e clica no dia."""
    page.get_by_placeholder("00/00/0000").click()
    picker = page.locator(".picker--opened")

    for _ in range(36):  # limite de segurança
        mes_txt = picker.locator(".picker__month").inner_text().strip().lower()
        ano_txt = picker.locator(".picker__year").inner_text().strip()
        mes_atual = next((i + 1 for i, m in enumerate(MESES) if mes_txt.startswith(m)), None)
        if mes_atual is None or not ano_txt.isdigit():
            break  # não foi possível interpretar o cabeçalho; tenta clicar direto
        delta = (alvo.year - int(ano_txt)) * 12 + (alvo.month - mes_atual)
        if delta == 0:
            break
        picker.locator(".picker__nav--next" if delta > 0 else ".picker__nav--prev").click()

    picker.locator(".picker__day--infocus:not(.picker__day--disabled)").get_by_text(
        str(alvo.day), exact=True
    ).click()


def nome_arquivo_seguro(texto: str) -> str:
    texto = re.sub(r'[<>:"/\\|?*]', "", texto)
    return re.sub(r"\s+", "_", texto.strip())[:80] or "SEM_NOME"


def obter_aba(context, host, url):
    """Reaproveita a aba já aberta do site (pelo host) ou abre uma nova com a URL."""
    for aba in context.pages:
        if host in aba.url.lower():
            print(f"{host} encontrado.")
            return aba, False
    print(f"{host} não encontrado; abrindo nova aba.")
    aba = context.new_page()
    aba.goto(url)
    return aba, True


_SESSOES_FOCO = []  # mantém as sessões CDP vivas para o "foco" continuar ativo


def garantir_aba(context, atual, host, url):
    """
    Devolve a aba do site: a atual, se ainda for válida; senão procura pelo host entre as
    abas abertas; se não achar, abre uma nova. Assim a aba é sempre re-encontrada, mesmo que
    você tenha trocado de aba, navegado ou fechado alguma enquanto o script esperava.
    """
    if atual is not None and not atual.is_closed() and host in atual.url.lower():
        return atual
    aba, _ = obter_aba(context, host, url)
    return aba


def ativar_aba(context, page):
    """
    Traz a aba para frente e a mantém ATIVA. Abas em segundo plano são congeladas pelo Chrome
    (a automação para até você abri-las manualmente); isso evita o problema nos dois sentidos
    (DARE -> SEI e SEI -> DARE).
    """
    page.bring_to_front()
    try:
        sessao = context.new_cdp_session(page)
        sessao.send("Emulation.setFocusEmulationEnabled", {"enabled": True})
        _SESSOES_FOCO.append(sessao)
    except Exception:
        pass  # não é essencial; segue só com o bring_to_front
    try:
        page.wait_for_function("document.visibilityState === 'visible'", timeout=5000)
    except PlaywrightTimeoutError:
        page.bring_to_front()
        page.wait_for_timeout(500)


def achar_visivel(page, seletor, timeout=30, exigir_visivel=True):
    """
    Procura o seletor na página E em todos os iframes (o SEI mostra o processo dentro de
    iframes aninhados) e devolve o primeiro elemento visível. Espera até `timeout` segundos.
    Com exigir_visivel=False basta o elemento existir (útil para <input type="file">).
    """
    fim = time.monotonic() + timeout
    while time.monotonic() < fim:
        for frame in page.frames:
            try:
                candidato = frame.locator(seletor).first
                if candidato.count() and (not exigir_visivel or candidato.is_visible()):
                    return candidato
            except Exception:
                pass  # frame recarregando; tenta de novo no próximo ciclo
        page.wait_for_timeout(250)
    raise PlaywrightTimeoutError(f"Elemento não encontrado em nenhum frame: {seletor}")


def preencher_data_hoje(page, seletor="#txtDataElaboracao", tentativas=6):
    """
    Preenche o campo com a data de hoje (DD/MM/AAAA) digitando tecla a tecla, para a máscara
    do SEI (infraMascaraData, no onkeypress) funcionar, e confere se o valor ficou no campo.
    Repete se a tela recarregar e limpar o campo.
    """
    esperado = date.today().strftime("%d/%m/%Y")
    for _ in range(tentativas):
        try:
            campo = achar_visivel(page, seletor)
            campo.click()
            campo.fill("")
            campo.press_sequentially(somente_digitos(esperado), delay=60)  # a máscara coloca as barras
            page.wait_for_timeout(500)  # dá tempo de um eventual recarregamento limpar o campo
            if achar_visivel(page, seletor).input_value() == esperado:
                return
        except PlaywrightTimeoutError:
            raise
        except Exception:
            pass  # frame recarregou no meio da digitação; tenta de novo
        page.wait_for_timeout(500)
    raise RuntimeError(f"Não consegui preencher {seletor} com {esperado}.")


def aguardar_pagina_de_impressao(context, page, paginas_antes):
    """Após clicar em IMPRIMIR, devolve a página que contém o documento (nova aba ou a mesma)."""
    for _ in range(40):  # até ~10s
        novas = [p for p in context.pages if p not in paginas_antes]
        if novas:
            alvo = novas[-1]
            alvo.wait_for_load_state("load")
            return alvo
        page.wait_for_timeout(250)
    page.wait_for_load_state("load")
    return page


def salvar_pdf(context, pagina, caminho: Path):
    """Gera o PDF da página (equivale a Imprimir > Salvar como PDF) sem abrir o diálogo do Chrome."""
    try:
        sessao = context.new_cdp_session(pagina)
        resultado = sessao.send(
            "Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True}
        )
        caminho.write_bytes(base64.b64decode(resultado["data"]))
    except Exception:
        # Alternativa (só funciona em Chromium sem interface)
        pagina.pdf(path=str(caminho), print_background=True)


with sync_playwright() as p:

    try:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    except Exception:
        raise Exception(
            "Chrome em modo de depuração não encontrado.\n"
            "Abra o Chrome com:\n"
            "\"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" "
            "--remote-debugging-port=9222 "
            "--disable-background-timer-throttling "
            "--disable-renderer-backgrounding "
            "--disable-backgrounding-occluded-windows"
        )

    context = browser.contexts[0]

    context.add_init_script(
        f"if (location.hostname.includes('{HOST_DARE}')) window.print = () => {{}};"
    )

    page_sei, _ = obter_aba(context, HOST_SEI, URL_SEI)
    page, dare_criada = obter_aba(context, HOST_DARE, URL_DARE)

    ativar_aba(context, page)

    if not dare_criada and "ADMManterCredorGeral" not in page.url:
        page.goto(URL_DARE)

    page.wait_for_load_state("networkidle")

    # ========= SUA AUTOMAÇÃO =========

    print("Menu")

    input("Entre na sua conta apos entrar pressione Enter para continuar...")

    processo = input("Digite o número do processo: ")
    cnpj = input("Digite o CNPJ: ")
    cpf = input("Digite o CPF: ")
    cnpj_recolhedor = input("Digite o CNPJ do recolhedor: ")
    mes_ano_referencia = input("Digite o mês/ano de referência (MMAAAA): ")
    vencimento = ler_vencimento(
        input(
            "Digite a data de vencimento (DD/MM/AAAA) "
            f"[Enter = {vencimento_padrao():%d/%m/%Y}, 1 mês à frente em dia útil]: "
        )
    )
    valor_digitos = valor_para_digitos(
        input(f"Digite o valor [Enter = {VALOR_PADRAO}]: ")
    )

    # Durante as perguntas acima você pode ter ficado na aba do SEI: procura de novo a aba
    # do DARE e a traz para frente antes de continuar.
    page = garantir_aba(context, page, HOST_DARE, URL_DARE)
    ativar_aba(context, page)
    page.wait_for_load_state("networkidle")

    aviso = page.locator("#dare-avulso-alert-title")

    if aviso.is_visible():
        page.locator(".dare-avulso-modal-action").click()

    #1.0 MENU

    page.locator("#select2-orgaos_opcao-container").click()
    page.click("li.select2-results__option:has-text('SEGEP - SUPERINTENDÊNCIA ESTADUAL DE GESTÃO DE PESSOAS')")
    page.locator('input[name="ind"][value="3"]').check()
    page.locator("#identificacao").fill(cnpj)
    page.locator("#identificar-contribuinte").click()

    #2.0 Onde coloca os dados

    #2.1 codigo da receita
    page.locator("#toggle-modal-rec").click()
    page.wait_for_selector("#datatable-receitas")
    page.click("tr[data-receita='7155']")
    #2.2 gestão
    page.get_by_placeholder("CÓDIGO DA UNIDADE GESTORA").fill("160001")
    page.get_by_placeholder("CÓDIGO DA GESTÃO").fill("00001")
    #2.3 CPF e nome
    cpf_campo = page.get_by_placeholder("000.000.000-00")
    cpf_campo.press_sequentially(cpf, delay=50)
    campo_nome_servidor = page.locator('input[name="reembolso_nome"]')
    campo_nome_servidor.click()
    #2.4 Data e data de vencimento
    page.locator("input[name='complemento_identificacao']").fill(cnpj_recolhedor)
    page.locator("input[name='mesano_referencia']").fill(mes_ano_referencia)

    selecionar_data_no_picker(page, vencimento)
    #2.5 Valor (a vírgula é automática: 100,00 -> digita 10000)
    page.locator("#valor_principal").press_sequentially(valor_digitos, delay=50)

    #3.0 IMPRIMIR -> salvar como PDF
    # Nome do servidor (preenchido automaticamente pelo site após informar o CPF)
    try:
        expect(campo_nome_servidor).not_to_have_value("", timeout=5000)
    except AssertionError:
        pass
    nome_servidor = campo_nome_servidor.input_value()

    PASTA_PDF.mkdir(parents=True, exist_ok=True)
    nome_pdf = (
        f"DARE_{nome_arquivo_seguro(nome_servidor)}_{somente_digitos(cpf)}"
        f"_{somente_digitos(mes_ano_referencia)}_venc-{vencimento:%d-%m-%Y}.pdf"
    )
    caminho_pdf = PASTA_PDF / nome_pdf

    paginas_antes = list(context.pages)
    page.locator("button.dare-avulso-dados-action.dare-avulso-dados-primary:has-text('IMPRIMIR')").click()

    pagina_impressao = aguardar_pagina_de_impressao(context, page, paginas_antes)
    ativar_aba(context, pagina_impressao)
    salvar_pdf(context, pagina_impressao, caminho_pdf)
    print(f"PDF salvo em: {caminho_pdf}")

    #4.0 Voltar
    voltar = pagina_impressao.locator("a.btn.btn-info[href='/avulso']")
    if voltar.count() == 0:
        voltar = page.locator("a.btn.btn-info[href='/avulso']")
    voltar.first.click()

    # Se o documento abriu em outra aba, fecha-a e volta para a aba principal
    if pagina_impressao is not page and not pagina_impressao.is_closed():
        pagina_impressao.close()

    #5.0 SEI
   
    print("Abrindo aba do SEI...")
    page_sei = garantir_aba(context, page_sei, HOST_SEI, URL_SEI)
    ativar_aba(context, page_sei)
    page_sei.locator('img[title="Controle de Processos"]:visible').first.click()
    page_sei.locator("#txtPesquisaRapida").wait_for(state="visible")
    page_sei.locator("#txtPesquisaRapida").fill(processo)
    page_sei.locator('img[title="Pesquisa Rápida"]:visible').first.click()

    #5.1 Reabrir e incluir

    # Espera a barra de ações do processo carregar (dentro dos iframes do SEI).
    # Processo fechado mostra "Reabrir Processo"; aberto mostra "Incluir Documento".
    acao = achar_visivel(
        page_sei,
        'img[title="Reabrir Processo"], img[title="Incluir Documento"]',
    )
    if acao.get_attribute("title") == "Reabrir Processo":
        acao.click()
    achar_visivel(page_sei, 'img[title="Incluir Documento"]').click()

    # 5.2 Externo 

    # Cada passo procura de novo nos frames, pois o SEI recarrega o iframe a cada tela.
    achar_visivel(page_sei, 'a[onclick="escolher(-1)"]').click()
    achar_visivel(page_sei, "#selSerie").select_option("310")
    # Data de elaboração: preenchida automaticamente com a data de hoje (DD/MM/AAAA)
    preencher_data_hoje(page_sei)
    achar_visivel(page_sei, 'label[for="optNato"]').click()

    # Anexa o PDF do DARE que acabou de ser baixado (caminho_pdf), sem precisar arrastar
    achar_visivel(page_sei, "input#filArquivo", exigir_visivel=False).set_input_files(
        str(caminho_pdf)
    )

    achar_visivel(page_sei, "#btnSalvar").click()