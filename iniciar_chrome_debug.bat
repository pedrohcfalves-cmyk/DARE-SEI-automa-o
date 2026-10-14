@echo off
rem OPCIONAL: o programa ja abre o Chrome sozinho. Use este arquivo so para abrir manualmente.
rem Abre o Chrome em modo depuracao (porta 9222) com SEI e DARE.
rem Usa um perfil proprio: faca login uma vez e ele fica salvo.
set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" (
    echo Chrome nao encontrado. Edite este arquivo e ajuste a variavel CHROME.
    pause
    exit /b 1
)
set "PERFIL=%LOCALAPPDATA%\DARE_Chrome_Perfil"
start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PERFIL%" ^
 --disable-background-timer-throttling --disable-renderer-backgrounding ^
 --disable-backgrounding-occluded-windows ^
 "https://sei.sistemas.ro.gov.br/sip/login.php?sigla_orgao_sistema=RO&sigla_sistema=SEI" ^
 "https://dare.sefin.ro.gov.br/avulso"
