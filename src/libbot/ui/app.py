"""Shell de la app: NavigationRail lateral más la vista activa.

Compone los servicios en un único grafo de dependencias y los inyecta a
cada vista. Las vistas se construyen una sola vez y se conservan vivas
al cambiar de pestaña, así no perdemos queries en curso ni scroll.
"""
from __future__ import annotations

import flet as ft

from libbot.config import ICON_PATH
from libbot.services.download_service import DownloadService
from libbot.services.favorites_service import FavoritesService
from libbot.services.history_service import HistoryService
from libbot.services.search_service import SearchService
from libbot.services.settings_service import SettingsService
from libbot.ui import theme
from libbot.ui.views.favorites_view import FavoritesView
from libbot.ui.views.history_view import HistoryView
from libbot.ui.views.home_view import HomeView
from libbot.ui.views.search_view import SearchView
from libbot.ui.views.settings_view import SettingsView


class LibBOtApp:
    def __init__(self, page: ft.Page) -> None:
        self._page = page

        self._settings = SettingsService()
        self._history = HistoryService()
        self._favorites = FavoritesService()
        self._search = SearchService(self._history)
        self._download = DownloadService(self._settings)

        self._configure_page()

        self._search_view = SearchView(page, self._search, self._download, self._favorites)
        self._history_view = HistoryView(page, self._history)
        # El botón "Repetir" del historial salta a Search precargando el query.
        self._history_view.on_repeat_search = self._repeat_search

        self._views: dict[int, ft.Control] = {
            0: HomeView(on_go_search=lambda: self._select(1)),
            1: self._search_view,
            2: FavoritesView(page, self._favorites, self._download),
            3: self._history_view,
            4: SettingsView(page, self._settings),
        }

        self._rail = self._build_rail()
        self._body = ft.Container(content=self._views[0], expand=True)

    def mount(self) -> None:
        self._page.add(
            ft.Row(
                controls=[
                    self._rail,
                    ft.VerticalDivider(width=1),
                    self._body,
                ],
                expand=True,
                spacing=0,
            )
        )

    def _configure_page(self) -> None:
        self._page.title = "LibBOt"
        self._page.theme = theme.build_theme()
        self._page.theme_mode = _theme_mode_from(self._settings.get_theme())
        self._page.window.width = 1200
        self._page.window.height = 780
        self._page.window.min_width = 900
        self._page.window.min_height = 600
        # El icono del .exe lo embebe PyInstaller, pero la ventana que dibuja
        # Flutter no lo hereda; hay que asignarlo a mano para que aparezca
        # en la barra de título y en la barra de tareas.
        if ICON_PATH.exists():
            self._page.window.icon = str(ICON_PATH)
        self._page.padding = 0

    def _build_rail(self) -> ft.NavigationRail:
        return ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=180,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Inicio",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SEARCH_OUTLINED,
                    selected_icon=ft.Icons.SEARCH,
                    label="Buscar",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.STAR_BORDER,
                    selected_icon=ft.Icons.STAR,
                    label="Favoritos",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY_OUTLINED,
                    selected_icon=ft.Icons.HISTORY,
                    label="Historial",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Ajustes",
                ),
            ],
            on_change=self._on_rail_change,
        )

    def _on_rail_change(self, e: ft.ControlEvent) -> None:
        self._select(int(e.control.selected_index))

    def _select(self, index: int) -> None:
        self._rail.selected_index = index
        self._body.content = self._views[index]
        self._page.update()

    def _repeat_search(self, query: str, by: str) -> None:
        self._select(1)
        self._search_view.trigger_search(query, by)


def _theme_mode_from(value: str) -> ft.ThemeMode:
    return {
        "system": ft.ThemeMode.SYSTEM,
        "light": ft.ThemeMode.LIGHT,
        "dark": ft.ThemeMode.DARK,
    }.get(value, ft.ThemeMode.SYSTEM)
