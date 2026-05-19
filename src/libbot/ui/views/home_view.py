"""Vista de bienvenida con accesos rápidos."""
from __future__ import annotations

from typing import Callable

import flet as ft

from libbot.ui import theme


class HomeView(ft.Container):
    def __init__(self, on_go_search: Callable[[], None]) -> None:
        super().__init__(expand=True, padding=theme.SPACING_XL)
        self._on_go_search = on_go_search
        self.content = self._build()

    def _build(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text(
                    "LibBOt",
                    size=42,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    "Busca y descarga libros desde Library Genesis y Anna's Archive.",
                    size=theme.TEXT_HEADING,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Container(height=theme.SPACING_LG),
                ft.FilledButton(
                    content="Empezar a buscar",
                    icon=ft.Icons.SEARCH,
                    on_click=lambda _: self._on_go_search(),
                ),
            ],
            spacing=theme.SPACING_SM,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )
