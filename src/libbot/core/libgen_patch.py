"""Monkey-patch a libgen-api 1.0.0.

La librería de PyPI apunta a `gen.lib.rus.ec` (caído) y parsea un HTML
que Libgen ya no sirve. Importar este módulo reemplaza tres métodos
de clase con versiones que hablan con los mirrors vivos y entienden
la tabla `table-striped` de 9 columnas que se usa hoy.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from libgen_api import libgen_search, search_request

from libbot.config import USER_AGENT

WORKING_MIRRORS: list[str] = [
    "https://libgen.li",
    "https://libgen.la",
    "https://libgen.vg",
    "https://libgen.bz",
]

REQUEST_TIMEOUT = 20

# El título termina con `<categoría> <subcategoría> <id_numérico>`.
# Lo separamos para guardar el ID y dejar el título limpio.
_TITLE_TAIL_RE = re.compile(r"\s+[a-z]\s+[a-z]\s+(\d+)\s*$")


def _patched_get_search_page(self) -> requests.Response:
    query_parsed = "+".join(self.query.split(" "))
    column = "a" if self.search_type.lower() == "author" else "t"

    last_error: Exception | None = None
    for base in WORKING_MIRRORS:
        url = f"{base}/index.php?req={query_parsed}&columns%5B%5D={column}"
        try:
            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            response.raise_for_status()
            self._active_mirror = base
            return response
        except (requests.RequestException, requests.HTTPError) as exc:
            last_error = exc
            continue

    raise ConnectionError(
        f"Ningún mirror de Libgen respondió. Último error: {last_error}"
    )


def _patched_aggregate_request_data(self) -> list[dict]:
    response = self.get_search_page()
    soup = BeautifulSoup(response.text, "lxml")

    for i_tag in soup.find_all("i"):
        i_tag.decompose()

    table = soup.find("table", class_="table-striped")
    if table is None:
        # Fallback: si Libgen cambia la clase, la segunda tabla del HTML
        # es históricamente la de resultados.
        tables = soup.find_all("table")
        table = tables[1] if len(tables) > 1 else None
    if table is None:
        return []

    active_mirror = getattr(self, "_active_mirror", WORKING_MIRRORS[0])
    output: list[dict] = []

    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td", recursive=False)
        # Filas de cómics/colecciones colapsan columnas con colspan y vienen
        # con menos de 9 celdas. Las descartamos.
        if len(cells) != 9:
            continue

        title_cell, author_cell, pub_cell, year_cell, lang_cell, \
            pages_cell, size_cell, ext_cell, mirrors_cell = cells

        title_raw = title_cell.get_text(" ", strip=True)
        book_id = ""
        m = _TITLE_TAIL_RE.search(title_raw)
        if m:
            book_id = m.group(1)
            title_raw = _TITLE_TAIL_RE.sub("", title_raw).strip()

        mirror_urls: list[str] = []
        for a in mirrors_cell.find_all("a"):
            href = a.get("href", "")
            if not href:
                continue
            if href.startswith("/"):
                href = urljoin(active_mirror, href)
            mirror_urls.append(href)

        # Garantizamos 4 slots fijos para que el resto del código pueda
        # asumir Mirror_1..Mirror_4 sin ramificarse.
        while len(mirror_urls) < 4:
            mirror_urls.append("")

        output.append({
            "ID": book_id,
            "Title": title_raw,
            "Author": author_cell.get_text(" ", strip=True),
            "Publisher": pub_cell.get_text(" ", strip=True),
            "Year": year_cell.get_text(" ", strip=True),
            "Language": lang_cell.get_text(" ", strip=True),
            "Pages": pages_cell.get_text(" ", strip=True),
            "Size": size_cell.get_text(" ", strip=True),
            "Extension": ext_cell.get_text(" ", strip=True),
            "Mirror_1": mirror_urls[0],
            "Mirror_2": mirror_urls[1],
            "Mirror_3": mirror_urls[2],
            "Mirror_4": mirror_urls[3],
            "Mirror_5": "",
            "Source": "Libgen",
        })

    return output


def _patched_resolve_download_links(self, item: dict) -> dict[str, str]:
    candidates = [
        ("Libgen.li", item.get("Mirror_1", "")),
        ("Randombook", item.get("Mirror_2", "")),
        ("Anna's Archive", item.get("Mirror_3", "")),
        ("Libgen.pw", item.get("Mirror_4", "")),
    ]
    return {name: url for name, url in candidates if url}


search_request.SearchRequest.get_search_page = _patched_get_search_page
search_request.SearchRequest.aggregate_request_data = _patched_aggregate_request_data
libgen_search.LibgenSearch.resolve_download_links = _patched_resolve_download_links
