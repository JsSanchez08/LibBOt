"""Resolución de mirrors y descarga al sistema de archivos del usuario."""
from __future__ import annotations

from pathlib import Path

from libbot.core.annas import AnnasSearch
from libbot.core.downloader import BookDownloader, ProgressCallback
from libbot.core.search import BookSearcher
from libbot.core.url_guard import UnsafeURLError, assert_safe_external_url
from libbot.models import Book
from libbot.services.settings_service import SettingsService


class DownloadService:
    def __init__(self, settings: SettingsService) -> None:
        self._downloader = BookDownloader()
        # Cada Book carga su `Source` y aquí despachamos al resolver del
        # motor correcto.
        self._libgen = BookSearcher()
        self._annas = AnnasSearch()
        self._settings = settings

    def resolve_links(self, book: Book) -> dict[str, str]:
        # Cuando el libro viene de una búsqueda reciente trae Mirror_1..5
        # ya cargados y nos ahorramos un round-trip al motor.
        direct = self._mirrors_from_fields(book)
        if direct:
            return direct

        # Favoritos viejos o casos donde solo tenemos ID + Source.
        payload = book.model_dump()
        try:
            if (book.Source or "").lower().startswith("anna"):
                return self._annas.resolve_download_links(payload)
            return self._libgen.resolve_download_links(payload)
        except RuntimeError as e:
            raise RuntimeError(f"No se pudieron resolver los enlaces: {e}") from e

    def download(
        self,
        book: Book,
        mirror_url: str,
        progress_cb: ProgressCallback | None = None,
    ) -> Path:
        try:
            assert_safe_external_url(mirror_url)
        except UnsafeURLError as e:
            raise RuntimeError(f"URL no permitida: {e}") from e

        dest_dir = self._settings.get_download_dir()
        # `BookDownloader._extract_direct_link` re-valida la URL tras seguir
        # la página intermedia, así que aquí no repetimos esa verificación.
        return self._downloader.download(
            book=book.model_dump(),
            mirror_url=mirror_url,
            dest_dir=dest_dir,
            progress_cb=progress_cb,
        )

    @staticmethod
    def _mirrors_from_fields(book: Book) -> dict[str, str]:
        slots = [
            ("Mirror 1", book.Mirror_1),
            ("Mirror 2", book.Mirror_2),
            ("Mirror 3", book.Mirror_3),
            ("Mirror 4", book.Mirror_4),
            ("Mirror 5", book.Mirror_5),
        ]
        return {name: url for name, url in slots if url}
