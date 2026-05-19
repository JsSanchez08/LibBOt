"""Modelos compartidos entre UI, servicios y persistencia."""
from __future__ import annotations

from pydantic import BaseModel


class Book(BaseModel):
    """Shape uniforme para libros de Libgen y Anna's Archive."""

    ID: str = ""
    Title: str = ""
    Author: str = ""
    Publisher: str = ""
    Year: str = ""
    Language: str = ""
    Pages: str = ""
    Size: str = ""
    Extension: str = ""
    Mirror_1: str = ""
    Mirror_2: str = ""
    Mirror_3: str = ""
    Mirror_4: str = ""
    Mirror_5: str = ""
    Source: str = "Libgen"


class FavoriteItem(Book):
    added_at: str = ""


class HistoryItem(BaseModel):
    query: str
    search_by: str
    results_count: int
    searched_at: str
