"""Empaqueta LibBOt como `LibBOt-v<version>.exe` usando PyInstaller.

La versión vive en `src/libbot/__init__.py` y de ahí se derivan el
nombre del .exe y el recurso de versión Windows embebido en el binario.

Uso:
    python scripts/build_exe.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "src" / "libbot" / "main.py"
ASSETS_DIR = ROOT / "assets"
ICON = ASSETS_DIR / "icon.ico"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
# El version_info.txt se regenera en cada build a partir de
# `__version__` para no duplicar el número de versión en el repo.
GENERATED_VERSION_FILE = BUILD / "version_info.txt"


def _read_version() -> str:
    # Parseamos el archivo a mano en lugar de importar `libbot` porque
    # importar el paquete dispara el monkey-patch de libgen-api, que
    # requeriría tener `requests` instalado solo para leer un string.
    init = ROOT / "src" / "libbot" / "__init__.py"
    for line in init.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(f"No se encontró __version__ en {init}")


def _build_version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(p) for p in version.split(".") if p.isdigit()]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])  # type: ignore[return-value]


def _write_version_info(version: str) -> Path:
    GENERATED_VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    vt = _build_version_tuple(version)
    vs = f"{vt[0]}.{vt[1]}.{vt[2]}.{vt[3]}"
    content = f"""# UTF-8
# Generado automáticamente por scripts/build_exe.py a partir de
# src/libbot/__init__.py:__version__. No editar a mano.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={vt},
    prodvers={vt},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040a04e4',
          [
            StringStruct(u'CompanyName', u'JsSanchez08'),
            StringStruct(u'FileDescription', u'LibBOt - Buscador y descargador de libros'),
            StringStruct(u'FileVersion', u'{vs}'),
            StringStruct(u'InternalName', u'LibBOt'),
            StringStruct(u'LegalCopyright', u'Copyright (c) 2026 JsSanchez08. Apache License 2.0.'),
            StringStruct(u'OriginalFilename', u'LibBOt-v{version}.exe'),
            StringStruct(u'ProductName', u'LibBOt'),
            StringStruct(u'ProductVersion', u'{vs}'),
          ],
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [0x040a, 1252])]),
  ],
)
"""
    GENERATED_VERSION_FILE.write_text(content, encoding="utf-8")
    return GENERATED_VERSION_FILE


def main() -> int:
    if not ENTRY.exists():
        print(f"No se encontró el entry point: {ENTRY}")
        return 1
    if not ICON.exists():
        print(f"No se encontró el icono: {ICON}")
        return 1

    version = _read_version()
    exe_basename = f"LibBOt-v{version}"
    print(f"Building {exe_basename}.exe (libbot.__version__={version})")

    for path in (DIST, BUILD):
        if path.exists():
            shutil.rmtree(path)

    version_file = _write_version_info(version)

    # PyInstaller separa src/dst con `;` en Windows y `:` en POSIX.
    add_data_sep = os.pathsep

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", exe_basename,
        "--onefile",
        "--windowed",
        "--icon", str(ICON),
        "--version-file", str(version_file),
        "--paths", str(ROOT / "src"),
        # Incluye assets/ en el bundle para que la ventana de Flet pueda
        # leer el icono en runtime vía sys._MEIPASS.
        "--add-data", f"{ASSETS_DIR}{add_data_sep}assets",
        # Imports que PyInstaller no detecta solo.
        "--hidden-import", "lxml._elementpath",
        "--hidden-import", "lxml.etree",
        # libgen_api importa submódulos dinámicamente.
        "--collect-submodules", "libgen_api",
        "--collect-submodules", "libbot",
        # Flet trae sus assets vía hook oficial.
        "--collect-data", "flet",
        # `flet_desktop` lleva binarios nativos del runtime de Flutter.
        # `--collect-all` arrastra submódulos + data + binarios de una vez;
        # `--collect-data` solo (lo anterior) dejaba fuera los .dll/.so.
        "--collect-all", "flet_desktop",
        str(ENTRY),
    ]

    print(">>", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    exe = DIST / f"{exe_basename}.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\n.exe generado: {exe}")
        print(f"Tamaño: {size_mb:.1f} MB")
    else:
        print(f"PyInstaller terminó pero no se encontró el .exe en {exe}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
