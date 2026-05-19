"""Barra de búsqueda con toggle title/author y botón de envío."""
from __future__ import annotations

from typing import Callable, Literal

import flet as ft

from libbot.ui import theme

SearchBy = Literal["title", "author"]


class LibBOtSearchBar(ft.Container):
    def __init__(
        self,
        on_submit: Callable[[str, SearchBy], None],
        initial_query: str = "",
    ) -> None:
        super().__init__(padding=0)
        self._on_submit = on_submit

        self._field = ft.TextField(
            value=initial_query,
            label="Título o autor del libro",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda _: self._submit(),
            expand=True,
            autofocus=True,
        )

        self._by = ft.SegmentedButton(
            selected=["title"],
            allow_multiple_selection=False,
            segments=[
                ft.Segment(value="title", label=ft.Text("Título"), icon=ft.Icon(ft.Icons.TITLE)),
                ft.Segment(value="author", label=ft.Text("Autor"), icon=ft.Icon(ft.Icons.PERSON)),
            ],
        )

        self._button = ft.FilledButton(
            content="Buscar",
            icon=ft.Icons.SEARCH,
            on_click=lambda _: self._submit(),
        )

        self.content = ft.Row(
            controls=[self._field, self._by, self._button],
            spacing=theme.SPACING_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def set_query(self, query: str) -> None:
        self._field.value = query
        self._field.update()

    def set_busy(self, busy: bool) -> None:
        self._button.disabled = busy
        self._field.disabled = busy
        self._button.update()
        self._field.update()

    def _submit(self) -> None:
        query = (self._field.value or "").strip()
        if not query:
            return
        by: SearchBy = "author" if "author" in self._by.selected else "title"
        self._on_submit(query, by)
