"""Persistencia en SQLite (stdlib, sin servidor).

Cada llamada abre y cierra su propia conexión. SQLite es rápido
suficiente en open/close que esto vale la pena: nos evita por completo
los problemas de thread-affinity cuando la UI dispara búsquedas y
descargas en hilos distintos.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from libbot.config import APP_DATA_DIR, DB_PATH, ensure_app_dirs

_SCHEMA = """
CREATE TABLE IF NOT EXISTS favorites (
    book_id    TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    author     TEXT NOT NULL DEFAULT '',
    publisher  TEXT NOT NULL DEFAULT '',
    year       TEXT NOT NULL DEFAULT '',
    language   TEXT NOT NULL DEFAULT '',
    pages      TEXT NOT NULL DEFAULT '',
    size       TEXT NOT NULL DEFAULT '',
    extension  TEXT NOT NULL DEFAULT '',
    mirror_1   TEXT NOT NULL DEFAULT '',
    mirror_2   TEXT NOT NULL DEFAULT '',
    mirror_3   TEXT NOT NULL DEFAULT '',
    mirror_4   TEXT NOT NULL DEFAULT '',
    mirror_5   TEXT NOT NULL DEFAULT '',
    source     TEXT NOT NULL DEFAULT 'Libgen',
    added_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_favorites_added_at
    ON favorites(added_at DESC);

CREATE TABLE IF NOT EXISTS history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    query          TEXT NOT NULL,
    search_by      TEXT NOT NULL,
    results_count  INTEGER NOT NULL,
    searched_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_searched_at
    ON history(searched_at DESC);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
"""

_SEED_SETTINGS = [
    # Cadena vacía: usar `DEFAULT_DOWNLOAD_DIR`.
    ("download_dir", ""),
    ("theme", "system"),
]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    # `check_same_thread=False` permite que hilos de trabajo (búsquedas,
    # descargas) reciban su propia conexión sin chocar con la chequeo
    # estricto de SQLite. La conexión vive solo dentro del `with`,
    # nunca se comparte entre hilos.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Crea las carpetas, aplica el esquema y migra los JSON legacy si los hay.

    Idempotente: seguro de llamar en cada arranque.
    """
    ensure_app_dirs()

    # PRAGMA WAL tiene que aplicarse antes del primer write y sobrevive a
    # la conexión, por eso usamos una conexión "cruda" sin pasar por el
    # context manager (que comitea al final).
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        for key, value in _SEED_SETTINGS:
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()

    _migrate_legacy_json()


def _migrate_legacy_json() -> None:
    # Lee los JSON de la versión vieja (webapp Docker) y los vuelca a SQLite
    # la primera vez. Si la tabla destino ya tiene registros no toca nada,
    # y al terminar archiva los archivos como `.migrated` para no
    # reprocesarlos.
    legacy_dir = Path.cwd() / "data"
    favs_json = legacy_dir / "favorites.json"
    hist_json = legacy_dir / "history.json"

    if favs_json.exists():
        _migrate_favorites(favs_json)
    if hist_json.exists():
        _migrate_history(hist_json)


def _migrate_favorites(path: Path) -> None:
    with get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]
        if existing > 0:
            return
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(items, list):
            return

        for item in items:
            book_id = (item.get("ID") or "").strip()
            if not book_id:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO favorites
                (book_id, title, author, publisher, year, language, pages,
                 size, extension, mirror_1, mirror_2, mirror_3, mirror_4,
                 mirror_5, source, added_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    book_id,
                    item.get("Title", ""),
                    item.get("Author", ""),
                    item.get("Publisher", ""),
                    item.get("Year", ""),
                    item.get("Language", ""),
                    item.get("Pages", ""),
                    item.get("Size", ""),
                    item.get("Extension", ""),
                    item.get("Mirror_1", ""),
                    item.get("Mirror_2", ""),
                    item.get("Mirror_3", ""),
                    item.get("Mirror_4", ""),
                    item.get("Mirror_5", ""),
                    item.get("Source", "Libgen"),
                    item.get("added") or now_utc_iso(),
                ),
            )

    _archive_migrated(path)


def _migrate_history(path: Path) -> None:
    with get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        if existing > 0:
            return
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(items, list):
            return

        for item in items:
            query = (item.get("query") or "").strip()
            if not query:
                continue
            conn.execute(
                """
                INSERT INTO history(query, search_by, results_count, searched_at)
                VALUES (?,?,?,?)
                """,
                (
                    query,
                    item.get("by", "title"),
                    int(item.get("results", 0)),
                    item.get("date") or now_utc_iso(),
                ),
            )

    _archive_migrated(path)


def _archive_migrated(path: Path) -> None:
    try:
        target = path.with_suffix(path.suffix + ".migrated")
        if target.exists():
            target.unlink()
        path.rename(target)
    except OSError:
        # Si no podemos archivar el JSON tampoco es grave: la próxima
        # corrida verá que la tabla ya tiene registros y saltará la
        # importación sin duplicar nada.
        pass


__all__ = [
    "APP_DATA_DIR",
    "DB_PATH",
    "get_connection",
    "init_db",
    "now_utc_iso",
]
