"""Vista de favoritos guardados, con descarga directa y eliminación."""
from __future__ import annotations

from pathlib import Path

import flet as ft

from libbot.models import Book, FavoriteItem
from libbot.services.download_service import DownloadService
from libbot.services.favorites_service import FavoritesService
from libbot.ui import theme
from libbot.ui.components.book_card import BookCard
from libbot.ui.components.mirrors_dialog import show_mirrors_dialog
from libbot.ui.components.progress_dialog import ProgressDialog
from libbot.ui.components.toast import show_toast


class FavoritesView(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        favorites_service: FavoritesService,
        download_service: DownloadService,
    ) -> None:
        super().__init__(expand=True, padding=theme.SPACING_LG)
        self._page = page
        self._favorites = favorites_service
        self._download = download_service

        self._title = ft.Text("Favoritos", size=theme.TEXT_TITLE, weight=ft.FontWeight.BOLD)
        self._counter = ft.Text("", color=ft.Colors.ON_SURFACE_VARIANT)
        self._list = ft.Column(
            spacing=theme.SPACING_MD,
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
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Recargar",
                            on_click=lambda _: self.refresh(),
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
        # Reflejamos cambios hechos desde Search al volver a la vista.
        self.refresh()

    def refresh(self) -> None:
        items = self._favorites.list()
        self._counter.value = f"{len(items)} libro(s) guardados"
        if not items:
            self._list.controls = [
                ft.Container(
                    padding=theme.SPACING_XL,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Aún no tienes favoritos. Marca un libro desde la vista de búsqueda.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
            ]
        else:
            self._list.controls = [self._build_card(item) for item in items]
        try:
            self._page.update()
        except Exception:
            # `did_mount` puede dispararse antes de que la vista esté ligada
            # a la página; en ese caso `update()` rebota y lo ignoramos.
            pass

    def _build_card(self, item: FavoriteItem) -> ft.Control:
        # FavoriteItem hereda de Book, así que es compatible directamente.
        return BookCard(
            book=item,
            is_favorite=True,
            on_toggle_favorite=self._remove,
            on_download=self._start_download,
            on_show_mirrors=self._show_mirrors,
            show_remove=True,
        )

    def _remove(self, book: Book) -> None:
        self._favorites.remove(book.ID)
        show_toast(self._page, "Quitado de favoritos")
        self.refresh()

    def _start_download(self, book: Book) -> None:
        # Botón "Descargar": directo al primer mirror disponible.
        try:
            mirrors = self._download.resolve_links(book)
        except RuntimeError as e:
            show_toast(self._page, str(e), error=True)
            return

        if not mirrors:
            show_toast(self._page, "No hay mirrors disponibles.", error=True)
            return

        first_url = next(iter(mirrors.values()))
        self._download_with_mirror(book, first_url)

    def _show_mirrors(self, book: Book) -> None:
        # Botón "Mirrors": modal para elegir mirror manualmente.
        try:
            mirrors = self._download.resolve_links(book)
        except RuntimeError as e:
            show_toast(self._page, str(e), error=True)
            return

        if not mirrors:
            show_toast(self._page, "No hay mirrors disponibles.", error=True)
            return

        show_mirrors_dialog(
            self._page,
            mirrors,
            on_pick=lambda url: self._download_with_mirror(book, url),
        )

    def _download_with_mirror(self, book: Book, mirror_url: str) -> None:
        suggested = f"{book.Title or 'libro'}.{book.Extension or 'bin'}"
        progress = ProgressDialog(self._page, suggested)
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
