"""Diálogo con barra de progreso para descargas en curso.

Maneja dos modos: determinado (cuando el servidor envía Content-Length) e
indeterminado (cuando no lo hace). La instancia se reutiliza entre updates
para no parpadear.
"""
from __future__ import annotations

import flet as ft

from libbot.ui import theme


class ProgressDialog:
    def __init__(self, page: ft.Page, filename: str) -> None:
        self._page = page
        self._filename_text = ft.Text(
            filename,
            size=theme.TEXT_BODY,
            weight=ft.FontWeight.W_500,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._bar = ft.ProgressBar(value=None, expand=True)
        self._stats = ft.Text("Iniciando…", size=theme.TEXT_CAPTION, color=ft.Colors.ON_SURFACE_VARIANT)

        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Descargando"),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    tight=True,
                    spacing=theme.SPACING_SM,
                    controls=[self._filename_text, self._bar, self._stats],
                ),
            ),
        )

    def show(self) -> None:
        self._page.show_dialog(self._dialog)

    def close(self) -> None:
        self._page.pop_dialog()

    def update_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            self._bar.value = downloaded / total
            pct = int((downloaded / total) * 100)
            self._stats.value = f"{pct}% — {_fmt_bytes(downloaded)} de {_fmt_bytes(total)}"
        else:
            self._bar.value = None
            self._stats.value = f"{_fmt_bytes(downloaded)} descargados"
        self._page.update()


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} GB"
