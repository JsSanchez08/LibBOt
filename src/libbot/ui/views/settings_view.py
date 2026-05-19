"""Vista de ajustes: carpeta de descargas + tema."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import flet as ft

from libbot import __version__
from libbot.services.settings_service import SettingsService
from libbot.ui import theme
from libbot.ui.components.toast import show_toast


class SettingsView(ft.Container):
    def __init__(self, page: ft.Page, settings_service: SettingsService) -> None:
        super().__init__(expand=True, padding=theme.SPACING_LG)
        self._page = page
        self._settings = settings_service

        # En Flet 0.85 FilePicker es un service control (no widget visual),
        # por eso se registra en `page.services` y no en `page.overlay`.
        self._folder_picker = ft.FilePicker()
        page.services.append(self._folder_picker)

        self._download_dir_field = ft.TextField(
            value=str(self._settings.get_download_dir()),
            label="Carpeta de descargas",
            read_only=True,
            expand=True,
        )

        self._theme_dropdown = ft.Dropdown(
            label="Tema",
            value=self._settings.get_theme(),
            options=[
                ft.DropdownOption(key="system", text="Sistema"),
                ft.DropdownOption(key="light", text="Claro"),
                ft.DropdownOption(key="dark", text="Oscuro"),
            ],
            on_select=self._on_theme_change,
            width=240,
        )

        self.content = ft.Column(
            expand=True,
            spacing=theme.SPACING_LG,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text("Ajustes", size=theme.TEXT_TITLE, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                self._section_download(),
                self._section_theme(),
                self._section_about(),
                self._section_legal(),
            ],
        )

    def _section_download(self) -> ft.Control:
        return ft.Column(
            spacing=theme.SPACING_SM,
            controls=[
                ft.Text("Descargas", size=theme.TEXT_HEADING, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Carpeta donde se guardan los libros descargados.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    size=theme.TEXT_BODY,
                ),
                ft.Row(
                    controls=[
                        self._download_dir_field,
                        ft.FilledTonalButton(
                            content="Cambiar…",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=self._on_pick_dir,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.LAUNCH,
                            tooltip="Abrir carpeta",
                            on_click=lambda _: self._open_current_dir(),
                        ),
                    ],
                    spacing=theme.SPACING_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        )

    def _section_theme(self) -> ft.Control:
        return ft.Column(
            spacing=theme.SPACING_SM,
            controls=[
                ft.Text("Apariencia", size=theme.TEXT_HEADING, weight=ft.FontWeight.W_600),
                self._theme_dropdown,
            ],
        )

    def _section_about(self) -> ft.Control:
        return ft.Column(
            spacing=theme.SPACING_SM,
            controls=[
                ft.Text("Acerca de", size=theme.TEXT_HEADING, weight=ft.FontWeight.W_600),
                ft.Row(
                    spacing=theme.SPACING_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            "LibBOt",
                            size=theme.TEXT_BODY,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            border_radius=10,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            content=ft.Text(
                                f"v{__version__}",
                                size=theme.TEXT_CAPTION,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.ON_PRIMARY_CONTAINER,
                            ),
                        ),
                    ],
                ),
                ft.Text(
                    "Buscador y descargador de libros para escritorio.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    size=theme.TEXT_BODY,
                ),
                ft.Text(
                    "Fuentes: Library Genesis · Anna's Archive",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    size=theme.TEXT_CAPTION,
                ),
                ft.Text(
                    "© 2026 JsSanchez08 · Licencia Apache 2.0",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    size=theme.TEXT_CAPTION,
                ),
                ft.Text(
                    spans=[
                        ft.TextSpan(
                            "github.com/JsSanchez08",
                            url="https://github.com/JsSanchez08",
                            style=ft.TextStyle(
                                color=ft.Colors.PRIMARY,
                                decoration=ft.TextDecoration.UNDERLINE,
                            ),
                        ),
                    ],
                    size=theme.TEXT_CAPTION,
                ),
            ],
        )

    def _section_legal(self) -> ft.Control:
        return ft.Container(
            padding=theme.SPACING_MD,
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            content=ft.Column(
                spacing=theme.SPACING_SM,
                controls=[
                    ft.Row(
                        spacing=theme.SPACING_SM,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=18,
                                    color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(
                                "Aviso legal",
                                size=theme.TEXT_HEADING,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                    ),
                    ft.Text(
                        "LibBOt es un cliente que consulta los catálogos públicos de "
                        "Library Genesis y Anna's Archive y descarga archivos "
                        "directamente desde los mirrors al sistema del usuario. "
                        "El autor no aloja, mantiene ni distribuye ningún contenido.",
                        size=theme.TEXT_BODY,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text(
                        "La responsabilidad legal del uso recae exclusivamente sobre "
                        "el usuario final, que debe respetar la legislación de "
                        "propiedad intelectual aplicable en su jurisdicción.",
                        size=theme.TEXT_BODY,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text(
                        "Software entregado \"tal cual\", sin garantías de ningún "
                        "tipo, conforme a la licencia Apache 2.0.",
                        size=theme.TEXT_CAPTION,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                ],
            ),
        )

    async def _on_pick_dir(self, _: ft.ControlEvent) -> None:
        # `get_directory_path` es async en Flet 0.85; sin `await` devolvería
        # una coroutine y `Path()` reventaría más abajo.
        result = await self._folder_picker.get_directory_path(
            dialog_title="Elige la carpeta de descargas",
        )
        if not result:
            return
        new_path = Path(result)
        self._settings.set_download_dir(new_path)
        self._download_dir_field.value = str(new_path)
        self._download_dir_field.update()
        show_toast(self._page, "Carpeta de descargas actualizada")

    def _on_theme_change(self, _: ft.ControlEvent) -> None:
        value = self._theme_dropdown.value or "system"
        self._settings.set_theme(value)  # type: ignore[arg-type]
        self._page.theme_mode = {
            "system": ft.ThemeMode.SYSTEM,
            "light": ft.ThemeMode.LIGHT,
            "dark": ft.ThemeMode.DARK,
        }[value]
        self._page.update()
        show_toast(self._page, "Tema actualizado")

    def _open_current_dir(self) -> None:
        path = self._settings.get_download_dir()
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as e:
            show_toast(self._page, f"No se pudo abrir la carpeta: {e}", error=True)
