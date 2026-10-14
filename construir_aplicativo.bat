@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Construir o aplicativo - DARE Automação
echo.
echo  ===============================================================
echo    DARE Automação - construir o aplicativo (.exe e instalador)
echo  ===============================================================
echo.
echo  Use este arquivo UMA vez, no SEU computador (que já tem Python).
echo  Ele gera o instalador para levar aos outros computadores, que
echo  NÃO precisam ter Python nem nenhum outro componente.
echo.

rem ---- 1. Python ------------------------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY goto sem_python
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" || goto sem_python
%PY% -c "import tkinter" >nul 2>nul || goto sem_tkinter

rem ---- 2. Ambiente de construção (isolado, não mexe no seu Python) ---------
echo  [1/5] Preparando o ambiente de construção (.venv-build)...
if not exist ".venv-build\Scripts\python.exe" (
    %PY% -m venv .venv-build || goto erro
)
set "VPY=.venv-build\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip --quiet --disable-pip-version-check
echo  [2/5] Baixando os componentes (precisa de internet; alguns minutos na 1a vez)...
"%VPY%" -m pip install -r requirements.txt -r requirements-build.txt --quiet --disable-pip-version-check || goto erro
for /f "delims=" %%v in ('%VPY% -c "import dare_auto; print(dare_auto.__version__)"') do set "VERSAO=%%v"
echo        Versão do programa: %VERSAO%

rem ---- 3. Testes ------------------------------------------------------------
echo  [3/5] Rodando os testes automáticos...
"%VPY%" -m unittest discover -q >"%TEMP%\dare_testes.txt" 2>&1
if errorlevel 1 (
    type "%TEMP%\dare_testes.txt"
    echo.
    echo  ATENÇÃO: algum teste falhou.
    choice /C SN /M "  Continuar a construção mesmo assim"
    if errorlevel 2 goto erro
) else (
    echo        Testes: OK
)

rem ---- 4. Executável --------------------------------------------------------
echo  [4/5] Gerando o executável (pasta dist\DARE Automacao)...
"%VPY%" -m PyInstaller --noconfirm --clean --log-level WARN empacotamento\dare_automacao.spec --distpath dist --workpath build || goto erro
"dist\DARE Automacao\DARE Automacao.exe" --diagnostico "build\diagnostico_teste.html" >nul 2>nul
if errorlevel 1 (
    echo  ATENÇÃO: o executável foi gerado, mas o motor de automação não iniciou no teste.
    echo           Veja build\diagnostico_teste.html
) else (
    echo        Executável testado: OK
)
if exist "dist\DARE_Automacao_Portatil_%VERSAO%.zip" del "dist\DARE_Automacao_Portatil_%VERSAO%.zip"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\DARE Automacao' -DestinationPath 'dist\DARE_Automacao_Portatil_%VERSAO%.zip'" && echo        Versão portátil: dist\DARE_Automacao_Portatil_%VERSAO%.zip

rem ---- 5. Instalador (Inno Setup) -------------------------------------------
echo  [5/5] Gerando o instalador...
call :achar_iscc
if not defined ISCC (
    echo        O Inno Setup ^(gerador de instaladores, gratuito^) não está instalado.
    where winget >nul 2>nul && (
        choice /C SN /M "  Instalar o Inno Setup agora pelo winget"
        if not errorlevel 2 (
            winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
            call :achar_iscc
        )
    )
)
if not defined ISCC (
    echo.
    echo        Sem o Inno Setup não dá para gerar o instalador, mas a versão portátil
    echo        já está pronta: dist\DARE_Automacao_Portatil_%VERSAO%.zip
    echo        Para o instalador: https://jrsoftware.org/isdl.php e rode este arquivo de novo.
    goto fim
)
"%ISCC%" /Q /DVersao=%VERSAO% empacotamento\instalador.iss || goto erro
echo        Instalador: dist\instalador\DARE_Automacao_Instalador_%VERSAO%.exe

:fim
echo.
echo  ===============================================================
echo    PRONTO!  Leve para os outros computadores:
echo      - dist\instalador\DARE_Automacao_Instalador_%VERSAO%.exe  (recomendado)
echo      - ou dist\DARE_Automacao_Portatil_%VERSAO%.zip  (sem instalar: descompacte e abra)
echo  ===============================================================
echo.
start "" explorer "dist"
pause
exit /b 0

:achar_iscc
set "ISCC="
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
    if exist "%%~P" set "ISCC=%%~P"
)
if not defined ISCC ( for /f "delims=" %%I in ('where iscc 2^>nul') do set "ISCC=%%I" )
exit /b 0

:sem_python
echo  Este computador não tem o Python 3.10 ou superior.
echo  Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH".
pause
exit /b 1

:sem_tkinter
echo  O Python instalado está sem o Tkinter (a parte de janelas).
echo  Reinstale o Python pelo site python.org deixando marcada a opção "tcl/tk and IDLE".
pause
exit /b 1

:erro
echo.
echo  NÃO foi possível concluir. Leia as mensagens acima (ou tire uma foto da tela).
pause
exit /b 1
