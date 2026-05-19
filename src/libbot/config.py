"""Paths del sistema y constantes globales.

Los datos persistentes viven fuera del binario (en `%APPDATA%\\LibBOt`)
para sobrevivir actualizaciones del .exe y para no chocar con permisos
de escritura cuando el usuario lo deja en `Program Files`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "LibBOt"


def _resource_dir() -> Path:
    # Empaquetado con PyInstaller `--onefile`: los recursos viven en el
    # directorio temporal `_MEIPASS` que PyInstaller crea al ejecutar.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # En modo desarrollo: src/libbot/config.py → src/libbot → src → root.
    return Path(__file__).resolve().parent.parent.parent


RESOURCE_DIR: Path = _resource_dir()
ICON_PATH: Path = RESOURCE_DIR / "assets" / "icon.ico"


def _resolve_app_data_dir() -> Path:
    # Si %APPDATA% no existe (perfil corrupto o entorno no-Windows en
    # desarrollo) caemos a `~/.libbot` para no reventar.
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


APP_DATA_DIR: Path = _resolve_app_data_dir()
DB_PATH: Path = APP_DATA_DIR / "libbot.db"

DEFAULT_DOWNLOAD_DIR: Path = Path.home() / "Downloads" / APP_NAME

# User-Agent común para todas las peticiones salientes. Anna's y Libgen
# rebotan cabeceras que delaten un bot.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

MAX_FAVORITES = 500
MAX_HISTORY = 50


def ensure_app_dirs() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
