"""Vista de historial de búsquedas con opción de repetir o limpiar."""
from __future__ import annotations

from datetime import datetime

import flet as ft

from libbot.models import HistoryItem
from libbot.services.history_service import HistoryService
from libbot.ui import theme
from libbot.ui.components.toast import show_toast


class HistoryView(ft.Container):
    def __init__(self, page: ft.Page, history_service: HistoryService) -> None:
        super().__init__(expand=True, padding=theme.SPACING_LG)
        self._page = page
        self._history = history_service
        # `LibBOtApp` sobrescribe este callback con la navegación real a
        # Search; lo dejamos como no-op para tener una vista usable aislada.
        self.on_repeat_search = lambda query, by: None

        self._title = ft.Text("Historial", size=theme.TEXT_TITLE, weight=ft.FontWeight.BOLD)
        self._counter = ft.Text("", color=ft.Colors.ON_SURFACE_VARIANT)
        self._list = ft.Column(
            spacing=theme.SPACING_SM,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.content = ft.Column(
            expand=True,
            spacing=theme.SPACING_MD,
            controls=[
                ft.Row(
                    controls=[
                        self._title,
                        ft.Container(expand=True),
                        ft.OutlinedButton(
                            content="Limpiar historial",
                            icon=ft.Icons.DELETE_SWEEP,
                            on_click=self._on_clear,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._counter,
                ft.Divider(),
                self._list,
            ],
        )
        self.refresh()

    def did_mount(self) -> None:  # type: ignore[override]
        self.refresh()

    def refresh(self) -> None:
        items = self._history.list()
        self._counter.value = f"{len(items)} búsqueda(s)"
        if not items:
            self._list.controls = [
                ft.Container(
                    padding=theme.SPACING_XL,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Aún no hay búsquedas registradas.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
            ]
        else:
            self._list.controls = [self._build_row(item) for item in items]
        try:
            self._page.update()
        except Exception:
            # `did_mount` puede dispararse antes de que la vista esté ligada
            # a la página; en ese caso `update()` rebota y lo ignoramos.
            pass

    def _build_row(self, item: HistoryItem) -> ft.Control:
        engine_label = "Anna's" if item.search_by.startswith("annas:") else "Libgen"
        clean_by = item.search_by.split(":")[-1]
        by_label = "Autor" if clean_by == "author" else "Título"

        return ft.Card(
            elevation=0,
            content=ft.Container(
                padding=theme.SPACING_MD,
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.HISTORY, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Container(width=theme.SPACING_SM),
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(item.query, weight=ft.FontWeight.W_500),
                                ft.Text(
                                    f"{engine_label} · {by_label} · {item.results_count} resultado(s) · {_fmt_date(item.searched_at)}",
                                    size=theme.TEXT_CAPTION,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                        ),
                        ft.IconButton(
                            icon=ft.Icons.REPLAY,
                            tooltip="Repetir búsqueda",
                            on_click=lambda _, q=item.query, b=item.search_by: self.on_repeat_search(q, b),
                        ),
                    ],
                ),
            ),
        )

    def _on_clear(self, _: ft.ControlEvent) -> None:
        self._history.clear()
        show_toast(self._page, "Historial limpiado")
        self.refresh()


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        local = dt.astimezone()
        return local.strftime("%d %b %Y · %H:%M")
    except ValueError:
        return iso
