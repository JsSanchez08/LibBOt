"""Validación anti-SSRF para las URLs externas que la app va a seguir.

Lista blanca de hosts más resolución DNS para rechazar IPs privadas o
loopback. Sin esto, alguien podría manipular un favorito guardado para
que la app golpee `http://localhost:8000/...` o la IP de metadatos del
proveedor cloud.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Match por sufijo: "libgen.li" acepta también "cdn.libgen.li".
ALLOWED_HOST_SUFFIXES: tuple[str, ...] = (
    "libgen.li",
    "libgen.la",
    "libgen.vg",
    "libgen.bz",
    "libgen.is",
    "libgen.rs",
    "libgen.gs",
    "libgen.pw",
    "libgen.lc",
    "annas-archive.gl",
    "annas-archive.org",
    "annas-archive.pk",
    "annas-archive.gd",
    "annas-archive.se",
    "annas-archive.li",
    "randombook.org",
    "z-lib.gd",
    "z-lib.gs",
    "z-lib.sk",
    "ipfs.io",
    "cloudflare-ipfs.com",
    "dweb.link",
)

ALLOWED_SCHEMES = frozenset({"http", "https"})


class UnsafeURLError(ValueError):
    """Se eleva cuando una URL no pasa el guard SSRF."""


def assert_safe_external_url(url: str) -> None:
    if not url or not isinstance(url, str):
        raise UnsafeURLError("URL vacía o inválida.")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"Esquema no permitido: '{parsed.scheme}'. Solo http/https.")

    host = (parsed.hostname or "").lower()
    if not host:
        raise UnsafeURLError("URL sin hostname.")

    if not any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES):
        raise UnsafeURLError(
            f"Host '{host}' no está en la lista de mirrors permitidos."
        )

    # IP literal -> validación directa. Hostname -> resolver y validar cada
    # registro porque un dominio externo puede resolver a IP privada (DNS rebind).
    try:
        _assert_safe_ip(ipaddress.ip_address(host))
        return
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise UnsafeURLError(f"No se pudo resolver '{host}': {e}")

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        _assert_safe_ip(ip)


def _assert_safe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise UnsafeURLError(f"IP no permitida: {ip} (red privada/local).")
