"""Cliente HTTP para Anna's Archive.

Prefiere siempre la ruta `libgen.li/ads.php` usando el mismo MD5 para
evitar la espera de Anna's. Solo si Libgen no lo sirve cae al
`slow_download` de Anna's.
"""
from __future__ import annotations

import re
from typing import Literal
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup, Tag

from libbot.config import USER_AGENT

SearchType = Literal["title", "author"]

# Anna's rota dominios con cierta frecuencia, los probamos en este orden.
ANNAS_MIRRORS: list[str] = [
    "https://annas-archive.gl",
    "https://annas-archive.pk",
    "https://annas-archive.gd",
]

REQUEST_TIMEOUT = 25

_TECH_SEPARATOR = "·"
_FORMAT_RE = re.compile(r"^(pdf|epub|mobi|djvu|azw3|cbz|cbr|fb2|txt|chm|rtf|doc|docx)$", re.I)
_SIZE_RE = re.compile(r"^\d+(?:\.\d+)?\s*(?:kb|mb|gb)$", re.I)
_YEAR_RE = re.compile(r"^\d{4}$")
_LANG_RE = re.compile(r"^[A-Za-zÀ-ÿ ]+\s*\[[a-z]{2,3}\]$")


class AnnasSearch:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._active_mirror = ANNAS_MIRRORS[0]

    def search(self, query: str, by: SearchType = "title") -> list[dict]:
        """Resultados con el mismo shape que `LibgenSearch` para que el
        resto del código trate ambos motores de forma intercambiable.
        """
        if not query.strip():
            return []

        base_params = "content=book_nonfiction,book_fiction,book_unknown"
        # El buscador de Anna's es full-text. El prefijo `author:` lo sesga
        # hacia el campo de autor sin perder el matching general.
        q = ("author:" + query) if by == "author" else query
        params = f"q={quote_plus(q)}&{base_params}"

        html = self._fetch_search(params)
        if html is None:
            raise ConnectionError("Anna's Archive no respondió desde ningún dominio espejo.")

        return self._parse_search_html(html)

    def _fetch_search(self, params: str) -> str | None:
        last_error: Exception | None = None
        for base in ANNAS_MIRRORS:
            try:
                resp = self.session.get(
                    f"{base}/search?{params}",
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True,
                )
                resp.raise_for_status()
                # Algunos dominios espejo están parqueados y devuelven HTML
                # sin marcas de Anna's. Sin esto, parsearíamos una página
                # de ads y devolveríamos resultados falsos.
                if "annas-archive" not in resp.text.lower() and "aarecord" not in resp.text.lower():
                    continue
                self._active_mirror = base
                return resp.text
            except (requests.RequestException, requests.HTTPError) as exc:
                last_error = exc
                continue
        if last_error:
            raise ConnectionError(f"Último error contactando Anna's: {last_error}")
        return None

    def _parse_search_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("div.js-aarecord-list-outer > div.flex.pt-3.pb-3.border-b")

        results: list[dict] = []
        for card in cards:
            book = self._parse_card(card)
            if book:
                results.append(book)
        return results

    @staticmethod
    def _parse_card(card: Tag) -> dict | None:
        title_a = card.select_one("a.js-vim-focus[href*='/md5/']")
        if not title_a:
            return None

        href = title_a.get("href", "")
        md5_match = re.search(r"/md5/([0-9a-f]{32})", href)
        if not md5_match:
            return None
        md5 = md5_match.group(1)

        title = title_a.get_text(" ", strip=True)

        # Anna's marca autor y editorial con iconos MDI en el span anidado;
        # diferenciamos por la clase del icono.
        author = ""
        publisher = ""
        for a in card.find_all("a"):
            inner = a.find("span")
            if not inner:
                continue
            icon_class = " ".join(inner.get("class", []))
            text = a.get_text(" ", strip=True)
            if "user-edit" in icon_class and not author:
                author = text
            elif "company" in icon_class and not publisher:
                publisher = text

        tech_div = card.select_one(
            "div.text-gray-800.font-semibold.text-sm.leading-\\[1\\.2\\]"
        )
        languages, extension, size, year = [], "", "", ""
        sources = ""
        if tech_div:
            parts = [p.strip() for p in tech_div.get_text(" ", strip=True).split(_TECH_SEPARATOR)]
            for p in parts:
                if not p:
                    continue
                if _LANG_RE.match(p):
                    languages.append(p)
                elif _FORMAT_RE.match(p):
                    extension = p.lower()
                elif _SIZE_RE.match(p):
                    size = p
                elif _YEAR_RE.match(p):
                    year = p
                elif "lgli" in p or "zlib" in p or "ia" in p.split("/"):
                    sources = p

        if not year and publisher:
            ym = re.search(r"\b(19\d{2}|20\d{2})\b", publisher)
            if ym:
                year = ym.group(1)

        return {
            "ID": md5,
            "Title": title,
            "Author": author,
            "Publisher": publisher,
            "Year": year,
            "Language": ", ".join(languages) if languages else "",
            "Pages": "",
            "Size": size,
            "Extension": extension,
            # Mirror_1 apunta a Libgen vía MD5: ruta rápida sin esperas que
            # BookDownloader ya sabe seguir.
            "Mirror_1": f"https://libgen.li/ads.php?md5={md5}",
            "Mirror_2": f"https://annas-archive.gl/md5/{md5}",
            "Mirror_3": f"https://annas-archive.gl/slow_download/{md5}/0/0",
            "Mirror_4": "",
            "Mirror_5": "",
            "Source": "Anna's Archive",
            "_sources_tag": sources,
        }

    def resolve_download_links(self, book: dict) -> dict[str, str]:
        """Mirrors ordenados de más rápido a más lento."""
        md5 = book.get("ID", "")
        if not md5:
            return {}

        return {
            "Libgen.li (rápido)": f"https://libgen.li/ads.php?md5={md5}",
            "Anna's Archive (info)": f"https://annas-archive.gl/md5/{md5}",
            "Anna's Slow (5 min espera)": f"https://annas-archive.gl/slow_download/{md5}/0/0",
        }
