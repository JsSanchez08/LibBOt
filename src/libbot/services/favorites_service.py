"""CRUD de favoritos con dedup por book_id y cap automático de 500."""
from __future__ import annotations

from libbot.config import MAX_FAVORITES
from libbot.db import get_connection, now_utc_iso
from libbot.models import Book, FavoriteItem


class FavoritesService:
    def add(self, book: Book) -> bool:
        """Devuelve False si ya existía o si el libro no trae ID."""
        book_id = (book.ID or "").strip()
        if not book_id:
            return False

        with get_connection() as conn:
            existing = conn.execute(
                "SELECT 1 FROM favorites WHERE book_id = ?", (book_id,)
            ).fetchone()
            if existing:
                return False

            conn.execute(
                """
                INSERT INTO favorites
                (book_id, title, author, publisher, year, language, pages,
                 size, extension, mirror_1, mirror_2, mirror_3, mirror_4,
                 mirror_5, source, added_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    book_id,
                    book.Title,
                    book.Author,
                    book.Publisher,
                    book.Year,
                    book.Language,
                    book.Pages,
                    book.Size,
                    book.Extension,
                    book.Mirror_1,
                    book.Mirror_2,
                    book.Mirror_3,
                    book.Mirror_4,
                    book.Mirror_5,
                    book.Source,
                    now_utc_iso(),
                ),
            )

            # Al sobrepasar MAX_FAVORITES descartamos los más viejos.
            conn.execute(
                """
                DELETE FROM favorites
                WHERE book_id NOT IN (
                    SELECT book_id FROM favorites
                    ORDER BY added_at DESC
                    LIMIT ?
                )
                """,
                (MAX_FAVORITES,),
            )
        return True

    def list(self) -> list[FavoriteItem]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM favorites
                ORDER BY added_at DESC
                """
            ).fetchall()
        return [self._row_to_favorite(r) for r in rows]

    def remove(self, book_id: str) -> bool:
        if not book_id:
            return False
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM favorites WHERE book_id = ?", (book_id,)
            )
            return cursor.rowcount > 0

    def exists(self, book_id: str) -> bool:
        if not book_id:
            return False
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM favorites WHERE book_id = ?", (book_id,)
            ).fetchone()
        return row is not None

    @staticmethod
    def _row_to_favorite(row) -> FavoriteItem:
        return FavoriteItem(
            ID=row["book_id"],
            Title=row["title"],
            Author=row["author"],
            Publisher=row["publisher"],
            Year=row["year"],
            Language=row["language"],
            Pages=row["pages"],
            Size=row["size"],
            Extension=row["extension"],
            Mirror_1=row["mirror_1"],
            Mirror_2=row["mirror_2"],
            Mirror_3=row["mirror_3"],
            Mirror_4=row["mirror_4"],
            Mirror_5=row["mirror_5"],
            Source=row["source"],
            added_at=row["added_at"],
        )
