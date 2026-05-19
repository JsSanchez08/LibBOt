"""Tarjeta visual de un libro con botones de favorito y descarga."""
from __future__ import annotations

from typing import Callable

import flet as ft

from libbot.models import Book
from libbot.ui import theme


class BookCard(ft.Card):
    def __init__(
        self,
        book: Book,
        is_favorite: bool,
        on_toggle_favorite: Callable[[Book], None],
        on_download: Callable[[Book], None],
        on_show_mirrors: Callable[[Book], None],
        show_remove: bool = False,
    ) -> None:
        self.book = book
        self._on_toggle_fav = on_toggle_favorite
        self._on_download = on_download
        self._on_show_mirrors = on_show_mirrors

        self._fav_btn = ft.IconButton(
            icon=ft.Icons.STAR if is_favorite else ft.Icons.STAR_BORDER,
            icon_color=ft.Colors.AMBER if is_favorite else ft.Colors.ON_SURFACE_VARIANT,
            tooltip="Quitar de favoritos" if show_remove else "Marcar como favorito",
            on_click=lambda _: self._on_toggle_fav(self.book),
        )

        super().__init__(
            elevation=1,
            content=ft.Container(
                padding=theme.SPACING_MD,
                content=ft.Column(
                    spacing=theme.SPACING_XS,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    book.Title or "(sin título)",
                                    size=theme.TEXT_HEADING,
                                    weight=ft.FontWeight.W_600,
                                    expand=True,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                self._fav_btn,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        ft.Text(
                            book.Author or "Autor desconocido",
                            size=theme.TEXT_BODY,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Row(
                            spacing=theme.SPACING_SM,
                            wrap=True,
                            controls=self._build_chips(),
                        ),
                        ft.Container(height=theme.SPACING_XS),
                        ft.Row(
                            spacing=theme.SPACING_SM,
                            controls=[
                                ft.Container(expand=True),
                                ft.TextButton(
                                    content="Mirrors",
                                    icon=ft.Icons.LINK,
                                    tooltip="Ver/elegir mirror manualmente",
                                    on_click=lambda _: self._on_show_mirrors(self.book),
                                ),
                                ft.FilledTonalButton(
                                    content="Descargar",
                                    icon=ft.Icons.DOWNLOAD,
                                    on_click=lambda _: self._on_download(self.book),
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        )

    def _build_chips(self) -> list[ft.Control]:
        chips: list[ft.Control] = []
        if self.book.Extension:
            chips.append(_chip(self.book.Extension.upper(), ft.Icons.INSERT_DRIVE_FILE))
        if self.book.Year:
            chips.append(_chip(self.book.Year, ft.Icons.CALENDAR_TODAY))
        if self.book.Language:
            chips.append(_chip(self.book.Language, ft.Icons.LANGUAGE))
        if self.book.Size:
            chips.append(_chip(self.book.Size, ft.Icons.STORAGE))
        if self.book.Source:
            chips.append(_chip(self.book.Source, ft.Icons.CLOUD))
        return chips


def _chip(label: str, icon: str) -> ft.Control:
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border_radius=12,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        content=ft.Row(
            spacing=4,
            tight=True,
            controls=[
                ft.Icon(icon, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(label, size=theme.TEXT_CAPTION, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
        ),
    )
