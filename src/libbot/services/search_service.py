"""Orquesta búsquedas en Libgen y Anna's Archive y las registra en historial."""
from __future__ import annotations

from typing import Literal

from libbot.core.annas import AnnasSearch
from libbot.core.search import BookSearcher
from libbot.models import Book
from libbot.services.history_service import HistoryService

SearchBy = Literal["title", "author"]

# Las búsquedas reales rara vez pasan de 100 caracteres. Topamos en 200
# para cortar payloads pensados solo para abusar de los mirrors.
MAX_QUERY_LEN = 200


class SearchService:
    def __init__(self, history: HistoryService) -> None:
        self._libgen = BookSearcher()
        self._annas = AnnasSearch()
        self._history = history

    def search_libgen(self, query: str, by: SearchBy = "title") -> list[Book]:
        query = self._clean(query)
        raw = self._libgen.search(query, by=by)
        self._history.add(query, by, len(raw))
        return [Book(**self._normalize(b)) for b in raw]

    def search_annas(self, query: str, by: SearchBy = "title") -> list[Book]:
        query = self._clean(query)
        raw = self._annas.search(query, by=by)
        self._history.add(query, f"annas:{by}", len(raw))
        return [Book(**self._normalize(b)) for b in raw]

    @staticmethod
    def _clean(query: str) -> str:
        cleaned = " ".join(query.split())
        if len(cleaned) < 2:
            raise ValueError("La búsqueda debe tener al menos 2 caracteres.")
        if len(cleaned) > MAX_QUERY_LEN:
            raise ValueError(f"La búsqueda excede {MAX_QUERY_LEN} caracteres.")
        return cleaned

    @staticmethod
    def _normalize(raw: dict) -> dict:
        # Solo nos quedamos con los campos que Book conoce. Los scrapers
        # añaden campos internos (p. ej. `_sources_tag`) que harían fallar
        # la validación de Pydantic con `extra="forbid"`.
        keys = {
            "ID", "Title", "Author", "Publisher", "Year", "Language",
            "Pages", "Size", "Extension",
            "Mirror_1", "Mirror_2", "Mirror_3", "Mirror_4", "Mirror_5",
            "Source",
        }
        return {k: (raw.get(k, "") or "") for k in keys}
