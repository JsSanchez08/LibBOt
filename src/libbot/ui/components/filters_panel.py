"""Panel de filtros (formato, idioma, año).

Widget controlado: no guarda estado propio, recibe `state` y emite cambios
por callback. La vista padre decide cuándo reconstruirlo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import flet as ft

from libbot.ui import theme


@dataclass
class FilterState:
    extensions: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    year_from: str = ""
    year_to: str = ""

    def is_empty(self) -> bool:
        return (
            not self.extensions
            and not self.languages
            and not self.year_from
            and not self.year_to
        )

    def copy(self) -> "FilterState":
        return FilterState(
            extensions=list(self.extensions),
            languages=list(self.languages),
            year_from=self.year_from,
            year_to=self.year_to,
        )


class FiltersPanel(ft.Container):
    def __init__(
        self,
        state: FilterState,
        available_extensions: list[str],
        available_languages: list[str],
        on_change: Callable[[FilterState], None],
        on_reset: Callable[[], None],
    ) -> None:
        super().__init__(
            padding=theme.SPACING_MD,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border_radius=8,
        )
        self._state = state
        self._on_change = on_change
        self._on_reset = on_reset

        self._year_from = ft.TextField(
            value=state.year_from,
            label="Desde",
            width=110,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: self._set_year("year_from", e.control.value),
        )
        self._year_to = ft.TextField(
            value=state.year_to,
            label="Hasta",
            width=110,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: self._set_year("year_to", e.control.value),
        )

        sections: list[ft.Control] = []

        if available_extensions:
            sections.append(self._section("Formato", [
                self._chip(ext.upper(), ext in state.extensions,
                           lambda _, v=ext: self._toggle("extensions", v))
                for ext in available_extensions
            ]))

        if available_languages:
            # Limitamos a 30 para no saturar la grilla cuando un mirror
            # devuelve listas larguísimas de combinaciones de idiomas.
            langs = available_languages[:30]
            sections.append(self._section("Idioma", [
                self._chip(lang, lang in state.languages,
                           lambda _, v=lang: self._toggle("languages", v))
                for lang in langs
            ]))

        year_section = ft.Column(
            spacing=theme.SPACING_XS,
            controls=[
                ft.Text("AÑO", size=theme.TEXT_CAPTION,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row(
                    spacing=theme.SPACING_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self._year_from,
                        ft.Icon(ft.Icons.ARROW_FORWARD, size=16,
                                color=ft.Colors.ON_SURFACE_VARIANT),
                        self._year_to,
                    ],
                ),
            ],
        )
        sections.append(year_section)

        if not state.is_empty():
            sections.append(
                ft.TextButton(
                    content="Limpiar filtros",
                    icon=ft.Icons.CLEAR,
                    on_click=lambda _: self._on_reset(),
                )
            )

        self.content = ft.Column(spacing=theme.SPACING_MD, controls=sections)

    @staticmethod
    def _section(title: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Column(
            spacing=theme.SPACING_XS,
            controls=[
                ft.Text(title.upper(), size=theme.TEXT_CAPTION,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row(controls=controls, wrap=True, spacing=theme.SPACING_XS,
                       run_spacing=theme.SPACING_XS),
            ],
        )

    @staticmethod
    def _chip(label: str, selected: bool, on_click: Callable) -> ft.Control:
        # ft.Chip funciona como filter chip cuando se le pasa `selected` +
        # `on_select` (no existe FilterChip independiente en Flet 0.85).
        return ft.Chip(
            label=ft.Text(label),
            selected=selected,
            show_checkmark=True,
            on_select=on_click,
        )

    def _toggle(self, group: str, value: str) -> None:
        items: list[str] = list(getattr(self._state, group))
        if value in items:
            items.remove(value)
        else:
            items.append(value)
        new_state = self._state.copy()
        setattr(new_state, group, items)
        self._on_change(new_state)

    def _set_year(self, field_name: str, value: str) -> None:
        new_state = self._state.copy()
        setattr(new_state, field_name, value.strip())
        self._on_change(new_state)
