"""Cliente Libgen con reintentos."""
from __future__ import annotations

import time
from typing import Literal

# El parche reemplaza métodos de clase de libgen_api en tiempo de import,
# así que tiene que cargarse antes de instanciar LibgenSearch.
from . import libgen_patch  # noqa: F401
from libgen_api import LibgenSearch

SearchType = Literal["title", "author"]


class BookSearcher:
    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        self._client = LibgenSearch()
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def search(self, query: str, by: SearchType = "title") -> list[dict]:
        if not query.strip():
            return []

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                if by == "author":
                    return self._client.search_author(query)
                return self._client.search_title(query)
            except Exception as exc:
                # libgen-api lanza tipos heterogéneos según el fallo,
                # cualquiera de ellos es reintentable.
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay * attempt)

        raise ConnectionError(
            f"No se pudo conectar con Libgen tras {self._max_retries} intentos: {last_error}"
        )

    def resolve_download_links(self, book: dict) -> dict[str, str]:
        try:
            return self._client.resolve_download_links(book)
        except Exception as exc:
            raise RuntimeError(f"No se pudieron resolver los enlaces: {exc}") from exc
