"""Modal con la lista de mirrors disponibles para descargar un libro."""
from __future__ import annotations

from typing import Callable

import flet as ft

from libbot.ui import theme


def show_mirrors_dialog(
    page: ft.Page,
    mirrors: dict[str, str],
    on_pick: Callable[[str], None],
) -> None:
    """Muestra un AlertDialog con los mirrors. Llama `on_pick(url)` al elegir."""

    def pick(url: str) -> None:
        page.pop_dialog()
        on_pick(url)

    options = [
        ft.ListTile(
            leading=ft.Icon(ft.Icons.LINK),
            title=ft.Text(name),
            subtitle=ft.Text(
                url,
                size=theme.TEXT_CAPTION,
                color=ft.Colors.ON_SURFACE_VARIANT,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            on_click=lambda _, u=url: pick(u),
        )
        for name, url in mirrors.items()
    ]

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Elige un mirror"),
        content=ft.Container(
            width=520,
            content=ft.Column(controls=options, tight=True, spacing=0),
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dialog)
