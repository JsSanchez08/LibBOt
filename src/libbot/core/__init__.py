"""Lógica de dominio: scraping, descarga, filtros, validación.

Importar este paquete dispara el monkey-patch a libgen-api, que tiene
que aplicarse antes de instanciar `LibgenSearch` en cualquier otro módulo.
"""
from . import libgen_patch  # noqa: F401
