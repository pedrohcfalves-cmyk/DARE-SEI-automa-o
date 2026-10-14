# DARE automação

Automatiza, **em lotes** (digitados na tela ou lidos de uma **planilha do Excel**), o fluxo **DARE avulso → PDF → documento externo no SEI**:

1. preenche o DARE avulso (órgão, receita, servidor, referência, vencimento e valor);
2. imprime e salva o PDF numa pasta local, com nome fácil de achar;
3. abre o processo no SEI e inclui o PDF como **documento externo**, com a data de hoje.

Ao iniciar, o programa **abre sozinho o Chrome em modo depuração com as duas abas (SEI e DARE)** e alterna
entre elas durante o trabalho.

---

## Requisitos

- Windows com **Google Chrome**
- **Python 3.10 ou superior**
- Pacote `playwright` (não precisa rodar `playwright install`: o script usa o seu Chrome)
- Só para o **modo planilha**: **Microsoft Excel** instalado e o pacote `pywin32` (já está no `requirements.txt`)

```bash
pip install -r requirements.txt
```

## Como usar

1. **Rode o programa:** dois cliques em `executar.bat` (ou `python dare_automacao.py`).
   O Chrome abre sozinho, num perfil próprio, com o SEI e o DARE. **Na primeira vez**, entre com a sua conta nos
   dois sistemas; nas próximas o login costuma ficar salvo nesse perfil.
2. No menu, escolha **1 · Modo em lotes** (digitar) ou **2 · Modo planilha** (ver a seção abaixo).
3. No modo em lotes, preencha o **Lote 1** e responda se quer **adicionar outro lote**, até acabar:

   | Pergunta | Observação |
   |---|---|
   | Processo SEI | número do processo que receberá o DARE |
   | CNPJ (órgão) | validado (dígitos verificadores) |
   | CPF do servidor | validado (dígitos verificadores) |
   | CNPJ do recolhedor | validado |
   | Mês/ano de referência | `MMAAAA`, ex.: `102026` |
   | Data de vencimento | `DD/MM/AAAA`. Enter = 1 mês à frente, em dia útil |
   | Valor | Enter = `100,00`. Aceita `7.273,07`, `7273,07` e `7.243` (= 7.243,00); a vírgula é colocada automaticamente no site |

   Do lote 2 em diante, CNPJ, recolhedor, referência, vencimento e valor já vêm preenchidos com o lote anterior
   (Enter aceita). **Processo e CPF** são sempre digitados.
4. Na **tela de conferência** você vê todos os lotes e pode corrigir antes de executar:

   | Comando | Faz |
   |---|---|
   | `I` | **Iniciar** (só começa com este comando; Enter não inicia) |
   | `E 2` | **Editar** o lote 2 (Enter mantém cada valor; digite só o que quer corrigir) |
   | `R 2` | **Remover** o lote 2 (pede confirmação) |
   | `A` | **Adicionar** mais um lote |
   | `C` | **Cancelar** |

5. Se for a primeira vez, entre nos dois sistemas e pressione Enter. O programa então roda **todos os lotes em
   sequência**, do primeiro ao último, repetindo `DARE → PDF → SEI` para cada um.
6. **Se um lote falhar, o programa segue para o próximo.** No fim aparece um resumo (o que deu certo, o que falhou
   e, se o DARE já tinha sido gerado, o caminho do PDF). Ele pergunta se quer **tentar de novo só os que falharam**.

Os lançamentos que ficarem pendentes (por erro, Ctrl+C ou queda do computador) ficam guardados em
`dados/lote_pendente.json`, e as opções 1 e 2 oferecem **retomá-los** na próxima vez.

### Modo planilha

Em vez de digitar, o programa lê os lançamentos de uma planilha do Excel (via `pywin32`), **uma linha por DARE**.
Depois de lidos, os lotes passam pela mesma tela de conferência (editar/remover/adicionar) e pelo mesmo loop.

1. **Escolha a planilha.** O programa lista as planilhas **abertas no Excel**; digite o número. Se a sua não estiver
   aberta, digite `C` e informe o **caminho do arquivo** (ela é aberta só para leitura, sem aparecer, e fechada
   sem salvar). Digite `M` para **criar a planilha modelo** (`modelos/modelo_dare.xlsx`).
2. **Escolha a aba** pelo número ou pelo nome (se só houver uma, ela é usada).
3. **Indique as colunas.** Funciona com **qualquer layout**: o programa procura sozinho a linha de cabeçalho e
   reconhece nomes como *Nº do Processo*, *CPF Servidor*, *Referência*, *Data Vencimento*, *Valor Principal*...
   Você confirma ou corrige. Para cada campo pode digitar:

   | Digite | Significa |
   |---|---|
   | `C` ou `AB` | a coluna pela letra |
   | `Nº Processo` | a coluna pelo nome do cabeçalho |
   | `=100,00` | o mesmo valor em **todas as linhas** (ex.: um CNPJ ou valor que nunca muda) |
   | `-` | nenhuma (só vale para vencimento e valor, que têm padrão) |

   O mapeamento fica salvo por planilha + aba (`dados/mapeamentos_planilha.json`): na próxima vez é só confirmar.
   Se a planilha não tem cabeçalho, informe linha `0`.
4. **Escolha a linha inicial e a final.** Enter na inicial = primeira linha depois do cabeçalho; Enter na final =
   **última linha com dados**.
5. O programa mostra quantas linhas são válidas e **lista as que têm problema** (com o número da linha e o motivo,
   ex.: *CPF inválido*). Essas ficam de fora; você escolhe se continua com as válidas. Linhas em branco e
   **linhas ocultas/filtradas** são puladas.

O que a planilha aceita: CPF/CNPJ com ou sem pontuação (e **zeros à esquerda perdidos pelo Excel são recuperados**);
mês/ano como `102026`, `10/2026`, `2026-10`, `out/2026` ou uma data; vencimento como data do Excel ou texto
`DD/MM/AAAA` (vazio = 1 mês à frente, em dia útil); valor numérico ou texto (`7.273,07`; vazio = `100,00`).

Colunas do **modelo** (`M`): Processo SEI · CNPJ do órgão · CPF do servidor · CNPJ do recolhedor ·
Mês/Ano referência · Vencimento · Valor (R$). A linha 2 do modelo é só um exemplo: troque ou apague antes de rodar.

> Planilhas em **Modo de Exibição Protegido** (baixadas da internet/e-mail) não aparecem na lista: clique em
> *Habilitar edição*. O programa **nunca grava** na sua planilha.

### Menu

| Opção | Faz |
|---|---|
| 1 | Modo em lotes (digitar os dados) |
| 2 | Modo planilha (ler os dados do Excel) |
| 3 | Abre a pasta dos PDFs |
| 4 | Abre a pasta de logs |
| 0 | Sair |

## Onde ficam os arquivos

| O quê | Onde |
|---|---|
| **PDFs gerados** | `DARE_PDFs/` (ao lado do script) |
| Histórico de execuções (uma linha por lote) | `dados/historico.csv` (abre no Excel) |
| Últimos dados digitados (viram padrão) | `dados/ultimos_dados.json` |
| Lançamentos de lote ainda pendentes | `dados/lote_pendente.json` |
| Colunas escolhidas para cada planilha/aba | `dados/mapeamentos_planilha.json` |
| Planilha modelo | `modelos/modelo_dare.xlsx` |
| Log completo | `logs/dare_automacao.log` (rotativo, até 6 MB) |
| Capturas de tela de erros | `logs/erros/` |
| Perfil do Chrome de depuração | `%LOCALAPPDATA%\DARE_Chrome_Perfil` |

Nome dos PDFs: `DARE_<NOME>_<CPF>_<MMAAAA>_venc-<DD-MM-AAAA>.pdf`.
Se o arquivo já existir, o novo recebe ` (2)`, ` (3)`... e nada é sobrescrito.

Para guardar os PDFs em outra pasta, defina a variável de ambiente `DARE_PASTA_PDF` (ex.: `D:\DAREs`).
Para usar um Chrome em outro local, defina `DARE_CHROME_PATH` com o caminho do `chrome.exe`.

## Configuração

Tudo que é fixo fica em `dare_auto/config.py`: URLs, órgão, código da receita (`7155`), unidade gestora
(`160001`), gestão (`00001`), série do documento no SEI (`310`), valor padrão e as pastas.

## Estrutura

```
dare_automacao.py        ponto de entrada (menu, abertura do Chrome e loop dos lotes)
dare_auto/
  config.py              constantes e pastas
  menu.py                interface de terminal (coleta, conferência, resumo)
  dare.py                passos no site do DARE
  sei.py                 passos no SEI
  navegador.py           Chrome, abas, iframes, PDF, capturas de erro
  fluxo_planilha.py      modo planilha: escolha da planilha/aba, colunas, linhas (interface)
  planilha.py            modo planilha: reconhece colunas e converte as células (sem Excel)
  excel_com.py           modo planilha: acesso ao Excel via pywin32 (COM) e planilha modelo
  armazenamento.py       últimos dados, lote pendente (JSON) e histórico (CSV)
  utils.py               validações, datas, valores (sem navegador)
  modelos.py             dados de um lançamento e resultado de um lote
  logger.py              logs em arquivo + console
tests/                   testes automáticos
iniciar_chrome_debug.bat abre o Chrome de depuração manualmente (opcional)
legado/                  versões anteriores do código
```

## Testes

```bash
python -m unittest discover -v
```

Cobrem validação de CPF/CNPJ, datas, valores, gravação dos dados, abertura do Chrome (simulada), a coleta e a
conferência dos lotes, o **loop de lotes** (com o navegador simulado: falha no meio, falha no SEI, Ctrl+C,
Chrome ausente, retomada dos pendentes) e o **modo planilha** (vários layouts, cabeçalho fora da linha 1, colunas
embaralhadas, CPF numérico, datas e números do Excel, linhas em branco/ocultas/inválidas e o fluxo do menu), com um
Excel simulado. Os passos nos sites (DARE/SEI) e o Excel/COM reais só podem ser testados rodando o programa de verdade.

## Depuração no VS Code

Use a configuração **DARE automação** (`.vscode/launch.json`). Ela define `DARE_DEBUG=1`, e o programa
passa a parar exatamente onde o erro acontece, em vez de só registrar e seguir para o próximo lote.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| *Não consegui abrir o Chrome sozinho* | Defina `DARE_CHROME_PATH` ou use `iniciar_chrome_debug.bat`. Se o Chrome abre mas a porta não responde, feche **todas** as janelas do Chrome que usam o perfil `DARE_Chrome_Perfil` e tente de novo |
| Trava até você trocar de aba | O Chrome congela abas em segundo plano. O script ativa a aba certa e o Chrome já abre com o congelamento desligado |
| `strict mode violation ... resolved to 2 elements` | O seletor achou mais de um elemento. Use `achar_visivel(...)` ou `.first` |
| Elemento do SEI não encontrado | O SEI usa iframes. Use `achar_visivel(page_sei, seletor)`, que procura em todos |
| Data de elaboração vazia no SEI | A máscara exige digitação; `preencher_data_hoje` já faz isso e confere o valor |
| *A biblioteca pywin32 não está instalada* | `pip install pywin32` (só no Windows, com o Excel instalado) |
| Minha planilha não aparece na lista | Ela precisa estar aberta no Excel (e fora do Modo de Exibição Protegido); ou use `C` e digite o caminho |
| Um lote falhou | Veja `logs/dare_automacao.log` e as capturas em `logs/erros/`; depois use "tentar de novo" no resumo, ou as opções 1/2 na próxima vez (lançamentos pendentes) |

> A partir do Chrome 136, a porta de depuração só funciona com um perfil separado (`--user-data-dir`).
> Por isso o programa usa o perfil `%LOCALAPPDATA%\DARE_Chrome_Perfil`.

## Privacidade (LGPD)

Este projeto manipula **CPF, CNPJ e nomes de servidores**. `DARE_PDFs/`, `dados/` e `logs/` estão no
`.gitignore` e **não devem ser versionados nem compartilhados**. Nos logs o CPF aparece mascarado
(`***.456.789-**`); já `dados/` e `historico.csv` guardam os dados completos, porque é para isso que servem.
Apague-os quando não precisar mais.

## Limitações conhecidas

- O vencimento padrão considera só fins de semana, não feriados.
- Os seletores dependem do HTML atual do DARE e do SEI; se os sites mudarem, os passos em `dare.py` e
  `sei.py` podem precisar de ajuste.
- Depois de clicar em Salvar no SEI, o programa espera o formulário sumir (até 15 s) antes do próximo lote. Se
  não sumir, só registra um aviso no log: confira o processo.
- Cada lote é independente: se o DARE já foi gerado e o anexo no SEI falhou, o DARE **existe**. Não refaça o
  lote sem conferir (o PDF fica em `DARE_PDFs/`).
