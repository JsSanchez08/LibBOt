"""Resolución de mirrors y descarga directa al disco."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests

from libbot.config import USER_AGENT

ProgressCallback = Callable[[int, int], None]
"""Firma `(downloaded_bytes, total_bytes)`. Cuando el servidor no envía
Content-Length, `total_bytes` llega en 0 y la UI debe mostrar barra
indeterminada."""

_BINARY_EXTS = (
    "pdf", "epub", "mobi", "djvu", "azw3", "chm",
    "fb2", "txt", "rar", "zip", "cbz", "cbr",
)
_CLOUDFLARE_MARKERS = (
    "checking your browser",
    "just a moment",
    "cf_chl",
    "cdn-cgi/challenge",
)


class BookDownloader:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def download(
        self,
        book: dict,
        mirror_url: str,
        dest_dir: Path,
        progress_cb: ProgressCallback | None = None,
    ) -> Path:
        """Descarga el archivo a `dest_dir` y devuelve el Path resultante.

        Lanza `RuntimeError` si el mirror devuelve HTML, Cloudflare o un
        archivo claramente inválido (< 1 KB).
        """
        direct_url = self._extract_direct_link(mirror_url)
        filename = self._build_filename(book, direct_url)
        target = dest_dir / filename
        self._stream_to_disk(direct_url, target, progress_cb)
        return target

    def _extract_direct_link(self, mirror_url: str) -> str:
        response = self.session.get(mirror_url, timeout=30, allow_redirects=True)
        response.raise_for_status()

        # Si el mirror ya respondió con binario no hay HTML que parsear.
        ct = (response.headers.get("content-type") or "").lower()
        if not any(x in ct for x in ("text/html", "text/plain", "application/xhtml")):
            return response.url

        html = response.text

        if any(s in html.lower() for s in _CLOUDFLARE_MARKERS):
            raise RuntimeError("El mirror está mostrando un challenge de Cloudflare.")

        exts_re = "|".join(_BINARY_EXTS)
        candidates = re.findall(
            rf'href=[\'"]([^\'"]+\.(?:{exts_re}))[\'"]',
            html,
            flags=re.IGNORECASE,
        )
        if candidates:
            return urljoin(response.url, candidates[0])

        get_match = re.search(
            r'href=[\'"]([^\'"]*(?:get\.php|/get/|cloudflare-ipfs|ipfs\.io|dweb\.link)[^\'"]*)[\'"]',
            html,
            flags=re.IGNORECASE,
        )
        if get_match:
            return urljoin(response.url, get_match.group(1))

        # Sin link directo identificable; devolvemos la URL original y dejamos
        # que el siguiente GET decida si hay binario.
        return mirror_url

    def _stream_to_disk(
        self,
        url: str,
        target: Path,
        progress_cb: ProgressCallback | None,
    ) -> None:
        with self.session.get(url, stream=True, timeout=60, allow_redirects=True) as r:
            r.raise_for_status()

            # Si el mirror sirve HTML cuando esperamos binario, cortamos antes
            # de tocar disco para no guardar una página de error con extensión
            # de libro.
            content_type = r.headers.get("content-type", "").lower()
            if "text/html" in content_type:
                raise RuntimeError(
                    "El mirror no contiene el archivo (devolvió HTML). "
                    "Prueba otro mirror desde el menú de mirrors."
                )

            total = int(r.headers.get("content-length", 0))
            downloaded = 0

            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb is not None:
                        progress_cb(downloaded, total)

            # Sin Content-Length y menos de 1 KB casi siempre es una página
            # de error disfrazada de binario. No vale la pena entregarla.
            if total == 0 and downloaded < 1024:
                try:
                    target.unlink()
                except OSError:
                    pass
                raise RuntimeError(
                    "El archivo descargado es demasiado pequeño (< 1 KB). "
                    "Probablemente el mirror devolvió una página de error."
                )

    @staticmethod
    def _build_filename(book: dict, url: str) -> str:
        title = book.get("Title", "libro")
        author = book.get("Author", "")
        ext = book.get("Extension", "").lower()
        if not ext:
            parsed = urlparse(url)
            ext = Path(parsed.path).suffix.lstrip(".") or "bin"

        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", f"{title} - {author}").strip()
        safe = re.sub(r"\s+", " ", safe)[:140]
        return f"{safe}.{ext}"
