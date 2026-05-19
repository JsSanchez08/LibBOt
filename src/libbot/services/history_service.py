"""Historial de búsquedas con cap automático de 50 registros."""
from __future__ import annotations

from libbot.config import MAX_HISTORY
from libbot.db import get_connection, now_utc_iso
from libbot.models import HistoryItem


class HistoryService:
    def add(self, query: str, by: str, n_results: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO history(query, search_by, results_count, searched_at)
                VALUES (?, ?, ?, ?)
                """,
                (query, by, n_results, now_utc_iso()),
            )
            # Conserva solo los MAX_HISTORY más recientes. El subquery
            # protege contra borrar todo cuando hay menos de N registros.
            conn.execute(
                """
                DELETE FROM history
                WHERE id NOT IN (
                    SELECT id FROM history
                    ORDER BY searched_at DESC
                    LIMIT ?
                )
                """,
                (MAX_HISTORY,),
            )

    def list(self) -> list[HistoryItem]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT query, search_by, results_count, searched_at
                FROM history
                ORDER BY searched_at DESC
                """
            ).fetchall()
        return [
            HistoryItem(
                query=r["query"],
                search_by=r["search_by"],
                results_count=r["results_count"],
                searched_at=r["searched_at"],
            )
            for r in rows
        ]

    def clear(self) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM history")
