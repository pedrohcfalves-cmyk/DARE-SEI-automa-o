@echo off
rem Abre a versão com janela pelo código-fonte (para quem tem Python e rodou instalar.bat).
rem Nos outros computadores, use o instalador gerado por construir_aplicativo.bat.
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 dare_app.py & exit /b 0)
where pythonw >nul 2>nul && (start "" pythonw dare_app.py & exit /b 0)
python dare_app.py
