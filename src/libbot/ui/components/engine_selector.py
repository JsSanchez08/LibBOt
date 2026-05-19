"""Selector entre motores de búsqueda Libgen / Anna's Archive."""
from __future__ import annotations

from typing import Callable, Literal

import flet as ft

Engine = Literal["libgen", "annas"]


class EngineSelector(ft.SegmentedButton):
    def __init__(
        self,
        on_change: Callable[[Engine], None],
        initial: Engine = "annas",
    ) -> None:
        self._on_change_cb = on_change
        super().__init__(
            selected=[initial],
            allow_multiple_selection=False,
            on_change=self._handle_change,
            segments=[
                ft.Segment(
                    value="libgen",
                    label=ft.Text("Libgen"),
                    icon=ft.Icon(ft.Icons.LIBRARY_BOOKS),
                ),
                ft.Segment(
                    value="annas",
                    label=ft.Text("Anna's Archive"),
                    icon=ft.Icon(ft.Icons.ARCHIVE),
                ),
            ],
        )

    @property
    def value(self) -> Engine:
        return "annas" if "annas" in self.selected else "libgen"

    def _handle_change(self, _: ft.ControlEvent) -> None:
        self._on_change_cb(self.value)
