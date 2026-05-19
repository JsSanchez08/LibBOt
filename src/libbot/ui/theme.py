"""Tokens visuales de la app.

Material 3 (vía Flet) hace el grueso del styling. Aquí solo viven los
tokens compartidos entre componentes: paleta de acentos y escalas de
espaciado y tipografía.
"""
from __future__ import annotations

import flet as ft

PRIMARY = ft.Colors.BLUE_700
ERROR = ft.Colors.RED_500
SUCCESS = ft.Colors.GREEN_600

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32

TEXT_TITLE = 22
TEXT_HEADING = 18
TEXT_BODY = 14
TEXT_CAPTION = 12


def build_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        use_material3=True,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )
