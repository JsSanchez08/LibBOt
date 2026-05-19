"""Filtros sobre los resultados de búsqueda."""
from __future__ import annotations


def filter_results(
    results: list[dict],
    extensions: list[str] | None = None,
    languages: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    filtered = results

    if extensions:
        exts_lower = {e.lower().lstrip(".") for e in extensions}
        filtered = [b for b in filtered if b.get("Extension", "").lower() in exts_lower]

    if languages:
        langs_lower = {l.lower() for l in languages}
        filtered = [b for b in filtered if b.get("Language", "").lower() in langs_lower]

    if year_from is not None or year_to is not None:
        filtered = [b for b in filtered if _year_in_range(b.get("Year", ""), year_from, year_to)]

    return filtered


def _year_in_range(year_str: str, year_from: int | None, year_to: int | None) -> bool:
    try:
        year = int(year_str)
    except (TypeError, ValueError):
        return False
    if year_from is not None and year < year_from:
        return False
    if year_to is not None and year > year_to:
        return False
    return True


def available_extensions(results: list[dict]) -> list[str]:
    exts = {b.get("Extension", "").lower() for b in results if b.get("Extension")}
    return sorted(e for e in exts if e)


def available_languages(results: list[dict]) -> list[str]:
    langs = {b.get("Language", "") for b in results if b.get("Language")}
    return sorted(l for l in langs if l)
