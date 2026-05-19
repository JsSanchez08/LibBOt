"""Configuración persistente del usuario (carpeta de descargas, tema)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from libbot.config import DEFAULT_DOWNLOAD_DIR
from libbot.db import get_connection

Theme = Literal["system", "light", "dark"]


class SettingsService:
    def get_download_dir(self) -> Path:
        raw = self._get("download_dir", "")
        path = Path(raw) if raw else DEFAULT_DOWNLOAD_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    def set_download_dir(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self._set("download_dir", str(path))

    def get_theme(self) -> Theme:
        value = self._get("theme", "system")
        if value not in ("system", "light", "dark"):
            return "system"
        return value  # type: ignore[return-value]

    def set_theme(self, value: Theme) -> None:
        self._set("theme", value)

    def _get(self, key: str, default: str) -> str:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return default
        return row["value"]

    def _set(self, key: str, value: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
