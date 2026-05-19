"""SnackBar de feedback rápido (éxito o error)."""
from __future__ import annotations

import flet as ft

from libbot.ui import theme


def show_toast(page: ft.Page, message: str, *, error: bool = False) -> None:
    page.show_dialog(
        ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=theme.ERROR if error else theme.SUCCESS,
            duration=3500,
        )
    )
