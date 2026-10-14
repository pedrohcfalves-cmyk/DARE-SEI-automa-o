@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 dare_automacao.py
) else (
    python dare_automacao.py
)
echo.
pause
