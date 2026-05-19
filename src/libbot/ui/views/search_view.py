"""Vista de búsqueda: barra, motor, filtros, paginación.

Búsquedas y descargas se ejecutan con `page.run_thread` para no congelar
la UI durante las peticiones HTTP. `page.update()` es thread-safe en Flet,
así que los workers pueden tocar la pantalla directamente.
"""
from __future__ import annotations

import math
from pathlib import Path

import flet as ft

from libbot.core.filters import (
    available_extensions,
    available_languages,
    filter_results,
)
from libbot.models import Book
from libbot.services.download_service import DownloadService
from libbot.services.favorites_service import FavoritesService
from libbot.services.search_service import SearchService
from libbot.ui import theme
from libbot.ui.components.book_card import BookCard
from libbot.ui.components.engine_selector import Engine, EngineSelector
from libbot.ui.components.filters_panel import FiltersPanel, FilterState
from libbot.ui.components.mirrors_dialog import show_mirrors_dialog
from libbot.ui.components.progress_dialog import ProgressDialog
from libbot.ui.components.search_bar import LibBOtSearchBar
from libbot.ui.components.toast import show_toast

PAGE_SIZE = 10


class SearchView(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        search_service: SearchService,
        download_service: DownloadService,
        favorites_service: FavoritesService,
    ) -> None:
        super().__init__(expand=True, padding=theme.SPACING_LG)
        self._page = page
        self._search = search_service
        self._download = download_service
        self._favorites = favorites_service

        self._engine: Engine = "annas"
        self._results: list[Book] = []
        self._filter_state = FilterState()
        self._current_page = 1
        self._show_filters = False

        self._search_bar = LibBOtSearchBar(on_submit=self._on_search)
        self._engine_selector = EngineSelector(on_change=self._on_engine_change)

        self._status = ft.Text("", color=ft.Colors.ON_SURFACE_VARIANT, size=theme.TEXT_BODY)
        self._spinner = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)

        self._filters_toggle = ft.TextButton(
            content="Filtros",
            icon=ft.Icons.TUNE,
            visible=False,
            on_click=lambda _: self._toggle_filters(),
        )

        self._filters_container = ft.Container(visible=False)

        self._results_list = ft.Column(
            spacing=theme.SPACING_MD,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self._pagination = ft.Row(
            visible=False,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=theme.SPACING_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.content = ft.Column(
            expand=True,
            spacing=theme.SPACING_MD,
            controls=[
                self._search_bar,
                ft.Row(
                    controls=[
                        self._engine_selector,
                        self._spinner,
                        self._status,
                        ft.Container(expand=True),
                        self._filters_toggle,
                    ],
                    spacing=theme.SPACING_MD,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._filters_container,
                ft.Divider(),
                self._results_list,
                self._pagination,
            ],
        )

    def trigger_search(self, query: str, by: str) -> None:
        """Permite relanzar una búsqueda desde la vista de Historial."""
        self._engine = "annas" if by.startswith("annas:") else "libgen"
        self._engine_selector.selected = [self._engine]
        clean_by = by.split(":")[-1]
        self._search_bar.set_query(query)
        self._page.update()
        self._on_search(query, clean_by)  # type: ignore[arg-type]

    def _on_engine_change(self, engine: Engine) -> None:
        self._engine = engine

    def _on_search(self, query: str, by: str) -> None:
        self._set_busy(True, f"Buscando «{query}»…")
        self._results_list.controls.clear()
        self._pagination.visible = False
        self._filters_toggle.visible = False
        self._filters_container.visible = False
        self._show_filters = False
        self._filter_state = FilterState()
        self._current_page = 1
        self._page.update()

        def worker() -> None:
            try:
                if self._engine == "annas":
                    results = self._search.search_annas(query, by=by)  # type: ignore[arg-type]
                else:
                    results = self._search.search_libgen(query, by=by)  # type: ignore[arg-type]
            except ValueError as e:
                self._set_busy(False, "")
                show_toast(self._page, str(e), error=True)
                return
            except ConnectionError as e:
                self._set_busy(False, "")
                show_toast(self._page, str(e), error=True)
                return
            except Exception as e:  # noqa: BLE001
                self._set_busy(False, "")
                show_toast(self._page, f"Error inesperado: {e}", error=True)
                return

            self._results = results
            self._render_all()
            self._set_busy(False, self._status_text())

        self._page.run_thread(worker)

    def _toggle_filters(self) -> None:
        self._show_filters = not self._show_filters
        self._filters_container.visible = self._show_filters
        self._filters_toggle.content = "Ocultar filtros" if self._show_filters else "Filtros"
        if self._show_filters:
            self._rebuild_filters_panel()
        self._page.update()

    def _rebuild_filters_panel(self) -> None:
        raw = [b.model_dump() for b in self._results]
        self._filters_container.content = FiltersPanel(
            state=self._filter_state,
            available_extensions=available_extensions(raw),
            available_languages=available_languages(raw),
            on_change=self._on_filter_change,
            on_reset=self._on_filter_reset,
        )

    def _on_filter_change(self, new_state: FilterState) -> None:
        self._filter_state = new_state
        self._current_page = 1
        if self._show_filters:
            self._rebuild_filters_panel()
        self._render_results()
        self._status.value = self._status_text()
        self._page.update()

    def _on_filter_reset(self) -> None:
        self._filter_state = FilterState()
        self._current_page = 1
        if self._show_filters:
            self._rebuild_filters_panel()
        self._render_results()
        self._status.value = self._status_text()
        self._page.update()

    def _filtered(self) -> list[Book]:
        if not self._results:
            return []
        raw = [b.model_dump() for b in self._results]
        year_from = _parse_int_or_none(self._filter_state.year_from)
        year_to = _parse_int_or_none(self._filter_state.year_to)
        filtered = filter_results(
            raw,
            extensions=self._filter_state.extensions or None,
            languages=self._filter_state.languages or None,
            year_from=year_from,
            year_to=year_to,
        )
        return [Book(**self._strip(b)) for b in filtered]

    @staticmethod
    def _strip(raw: dict) -> dict:
        # Pydantic con `extra="forbid"` rebota campos privados de los scrapers.
        return {k: v for k, v in raw.items() if not k.startswith("_") and k != "Edit"}

    def _status_text(self) -> str:
        filtered_count = len(self._filtered())
        total = len(self._results)
        if filtered_count == total:
            return f"{total} resultado(s)"
        return f"{filtered_count} de {total} resultado(s) tras filtrar"

    def _render_all(self) -> None:
        self._filters_toggle.visible = bool(self._results)
        self._render_results()

    def _render_results(self) -> None:
        items = self._filtered()

        if not items:
            self._results_list.controls = [
                ft.Container(
                    padding=theme.SPACING_XL,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "No hay resultados que coincidan con los filtros."
                        if self._results else
                        "No se encontraron libros para esa búsqueda.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
            ]
            self._pagination.visible = False
            self._page.update()
            return

        total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
        if self._current_page > total_pages:
            self._current_page = total_pages

        start = (self._current_page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = items[start:end]

        cards: list[ft.Control] = []
        for book in page_items:
            cards.append(
                BookCard(
                    book=book,
                    is_favorite=self._favorites.exists(book.ID),
                    on_toggle_favorite=self._toggle_favorite,
                    on_download=self._start_download,
                    on_show_mirrors=self._show_mirrors,
                )
            )
        self._results_list.controls = cards

        if total_pages > 1:
            self._pagination.controls = [
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    tooltip="Página anterior",
                    disabled=self._current_page <= 1,
                    on_click=lambda _: self._go_to_page(self._current_page - 1),
                ),
                ft.Text(
                    f"Página {self._current_page} de {total_pages}",
                    size=theme.TEXT_BODY,
                ),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    tooltip="Página siguiente",
                    disabled=self._current_page >= total_pages,
                    on_click=lambda _: self._go_to_page(self._current_page + 1),
                ),
            ]
            self._pagination.visible = True
        else:
            self._pagination.visible = False

        self._page.update()

    def _go_to_page(self, page_num: int) -> None:
        self._current_page = max(1, page_num)
        self._render_results()
        # Cambiar de página vuelve al inicio de la lista para no dejar al
        # usuario en mitad del scroll de la página anterior.
        self._results_list.scroll_to(offset=0, duration=200)

    def _toggle_favorite(self, book: Book) -> None:
        if self._favorites.exists(book.ID):
            self._favorites.remove(book.ID)
            show_toast(self._page, "Quitado de favoritos")
        else:
            added = self._favorites.add(book)
            if added:
                show_toast(self._page, "Agregado a favoritos")
            else:
                show_toast(self._page, "Ya estaba en favoritos", error=True)
        self._render_results()

    def _start_download(self, book: Book) -> None:
        # Botón "Descargar": va al primer mirror disponible sin preguntar.
        try:
            mirrors = self._download.resolve_links(book)
        except RuntimeError as e:
            show_toast(self._page, str(e), error=True)
            return

        if not mirrors:
            show_toast(self._page, "Este libro no tiene mirrors disponibles.", error=True)
            return

        first_url = next(iter(mirrors.values()))
        self._download_with_mirror(book, first_url)

    def _show_mirrors(self, book: Book) -> None:
        # Botón "Mirrors": deja al usuario elegir manualmente.
        try:
            mirrors = self._download.resolve_links(book)
        except RuntimeError as e:
            show_toast(self._page, str(e), error=True)
            return

        if not mirrors:
            show_toast(self._page, "Este libro no tiene mirrors disponibles.", error=True)
            return

        show_mirrors_dialog(
            self._page,
            mirrors,
            on_pick=lambda url: self._download_with_mirror(book, url),
        )

    def _download_with_mirror(self, book: Book, mirror_url: str) -> None:
        suggested_name = f"{book.Title or 'libro'}.{book.Extension or 'bin'}"
        progress = ProgressDialog(self._page, suggested_name)
        progress.show()

        def worker() -> None:
            try:
                path: Path = self._download.download(
                    book=book,
                    mirror_url=mirror_url,
                    progress_cb=progress.update_progress,
                )
            except Exception as e:  # noqa: BLE001
                progress.close()
                show_toast(self._page, f"Falló la descarga: {e}", error=True)
                return

            progress.close()
            show_toast(self._page, f"Guardado en {path}")

        self._page.run_thread(worker)

    def _set_busy(self, busy: bool, status: str) -> None:
        self._spinner.visible = busy
        self._status.value = status
        self._search_bar.set_busy(busy)
        self._page.update()


def _parse_int_or_none(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
