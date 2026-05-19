"""Punto de entrada de LibBOt desktop.

Orden de inicialización:
    1. Importar `libbot.core` para aplicar el monkey-patch a libgen-api
       antes de que cualquier servicio instancie `LibgenSearch`.
    2. Inicializar la base de datos.
    3. Lanzar la UI Flet.
"""
from __future__ import annotations

import flet as ft

# Side-effect import: el patch de libgen-api se aplica al cargar `core`.
# Mantener este import por encima de los servicios; el orden importa.
from libbot import core  # noqa: F401
from libbot.db import init_db
from libbot.ui.app import LibBOtApp


def _flet_main(page: ft.Page) -> None:
    LibBOtApp(page).mount()


def run() -> None:
    init_db()
    ft.run(main=_flet_main)


if __name__ == "__main__":
    run()
