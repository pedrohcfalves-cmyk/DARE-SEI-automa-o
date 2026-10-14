@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Instalação - DARE automação
echo.
echo  ==============================================
echo    DARE automação - instalação (só uma vez)
echo  ==============================================
echo.

set "PY="
where py >nul 2>nul
if not errorlevel 1 (set "PY=py -3" & goto achou)
where python >nul 2>nul
if not errorlevel 1 (set "PY=python" & goto achou)
goto sem_python

:achou
%PY% --version >nul 2>nul
if errorlevel 1 goto sem_python

echo  [1/3] Python encontrado. Instalando os componentes do programa...
echo        (precisa de internet; pode demorar alguns minutos)
echo.
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto erro_pip

echo.
echo  [2/3] Conferindo a instalação...
%PY% -c "import playwright" >nul 2>nul
if errorlevel 1 goto erro_pip
echo        Componente principal: OK

echo.
echo  [3/3] Conferindo o suporte ao Excel (modo planilha)...
%PY% -c "import win32com.client" >nul 2>nul
if errorlevel 1 (
    echo        Modo planilha NÃO disponível neste computador.
    echo        Ele precisa do Microsoft Excel instalado. O modo em lotes funciona normalmente.
) else (
    echo        Suporte ao Excel: OK
)

echo.
echo  ==============================================
echo    PRONTO! Instalação concluída.
echo    Para usar o programa, dê dois cliques em:  executar.bat
echo  ==============================================
echo.
pause
exit /b 0

:sem_python
echo  O Python NÃO está instalado neste computador.
echo.
echo  O que fazer:
echo    1. Abra o site  https://www.python.org/downloads/
echo    2. Clique no botão amarelo "Download Python" e abra o arquivo baixado.
echo    3. IMPORTANTE: na primeira tela, marque a caixinha
echo       "Add python.exe to PATH" ^(ou "Add Python to PATH"^).
echo    4. Clique em "Install Now" e espere terminar.
echo    5. Feche esta janela e dê dois cliques em instalar.bat de novo.
echo.
pause
exit /b 1

:erro_pip
echo.
echo  NÃO foi possível instalar os componentes.
echo  Verifique se o computador está com internet e tente de novo.
echo  Se continuar dando erro, tire uma foto desta tela e envie para
echo  quem lhe entregou o programa.
echo.
pause
exit /b 1
