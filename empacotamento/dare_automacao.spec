# -*- mode: python ; coding: utf-8 -*-
"""
Receita do PyInstaller: gera a pasta "dist/DARE Automacao" com o executável e TUDO o que ele
precisa (Python, Playwright com o seu Node embutido, pywin32, openpyxl, psutil e Tkinter).
O computador de destino não precisa ter Python nem instalar nada.

Uso (na pasta do projeto):  construir_aplicativo.bat
   ou:  python -m PyInstaller --noconfirm --clean empacotamento/dare_automacao.spec
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

RAIZ = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(RAIZ))
from dare_auto import __version__  # noqa: E402

NOME = "DARE Automacao"
ICONE = RAIZ / "dare_auto" / "gui" / "recursos" / "icone.ico"

# ---- Arquivos que acompanham o programa ---------------------------------------------------
datas = [(str(RAIZ / "dare_auto" / "gui" / "recursos"), "dare_auto/gui/recursos")]
for nome in ("GUIA_DE_USO.html", "GUIA_DE_USO.pdf", "LICENCA.txt"):
    if (RAIZ / nome).exists():
        datas.append((str(RAIZ / nome), "."))
# Driver do Playwright (Node + pacote). Os navegadores NÃO entram: o programa usa o Chrome/Edge do computador.
datas += collect_data_files("playwright", excludes=["**/.local-browsers/**", "**/__pycache__/**"])

# Metadados dos pacotes (o Diagnóstico mostra as versões instaladas)
for pacote in ("playwright", "openpyxl", "psutil"):
    datas += copy_metadata(pacote)

hiddenimports = collect_submodules("playwright") + ["openpyxl", "psutil"]
if sys.platform == "win32":
    hiddenimports += ["win32com", "win32com.client", "pythoncom", "pywintypes", "winreg"]

# ---- Informações de versão do .exe (aparecem em Propriedades > Detalhes) -----------------
versao_arquivo = None
if sys.platform == "win32":
    from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                     VarFileInfo, VarStruct, VSVersionInfo)
    numeros = tuple(int(x) for x in __version__.split(".")[:3]) + (0,)
    info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=numeros, prodvers=numeros),
        kids=[
            StringFileInfo([StringTable("041604B0", [
                StringStruct("CompanyName", "DARE Automação"),
                StringStruct("FileDescription", "DARE Automação - DARE avulso, PDF e SEI"),
                StringStruct("FileVersion", __version__),
                StringStruct("InternalName", NOME),
                StringStruct("LegalCopyright", "© 2026. Todos os direitos reservados."),
                StringStruct("OriginalFilename", f"{NOME}.exe"),
                StringStruct("ProductName", "DARE Automação"),
                StringStruct("ProductVersion", __version__),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0416, 1200])]),
        ],
    )
    versao_arquivo = Path(workpath) / "versao_windows.txt"
    versao_arquivo.parent.mkdir(parents=True, exist_ok=True)
    versao_arquivo.write_text(str(info), encoding="utf-8")

a = Analysis(
    [str(RAIZ / "dare_app.py")],
    pathex=[str(RAIZ)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Bibliotecas grandes que o programa não usa (deixa o instalador menor e a abertura mais rápida)
    excludes=["matplotlib", "numpy", "pandas", "scipy", "PIL", "IPython", "pytest", "setuptools",
              "tkinter.test", "lib2to3", "pydoc_data"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # modo pasta (onedir): abre bem mais rápido que um .exe único
    name=NOME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # sem compactação UPX: evita alarmes falsos de antivírus
    console=False,  # aplicativo com janela, sem tela preta
    disable_windowed_traceback=False,
    icon=str(ICONE) if ICONE.exists() else None,
    version=str(versao_arquivo) if versao_arquivo else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=NOME,
)
