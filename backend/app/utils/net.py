"""Network-safety helpers: SSRF guard for outbound HTTP fetches.

User-supplied URLs (e.g. the ``url`` document source) must not be allowed to reach internal
infrastructure — loopback, private ranges, link-local (which covers the cloud metadata endpoint
``169.254.169.254``), reserved, or unspecified addresses — nor non-HTTP schemes. Redirects are
followed manually so a public URL cannot bounce into an internal address.
"""

import ipaddress
import socket

import httpx

_ALLOWED_SCHEMES = {"http", "https"}
_DEFAULT_USER_AGENT = "NotebookLM-clone/0.1 (+https://example.com)"


class BlockedUrlError(ValueError):
    """Raised when a URL is rejected by the SSRF guard."""


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # Normalize IPv4-mapped (``::ffff:a.b.c.d``) and 6to4 (``2002::/16``) IPv6 addresses to the
    # embedded IPv4 before classifying. Python < 3.13 does not delegate is_private/is_loopback/…
    # to the mapped IPv4, so ``::ffff:169.254.169.254`` would otherwise bypass the guard.
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped or ip.sixtofour
        if mapped is not None:
            ip = mapped
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    )


def _resolve_host(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Return all IPs a host resolves to (or the literal itself if it is an IP)."""
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise BlockedUrlError(f"Could not resolve host: {host}") from exc
    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        addr = info[4][0]
        # Strip an IPv6 zone/scope id if present (e.g. "fe80::1%eth0").
        addr = addr.split("%", 1)[0]
        ips.append(ipaddress.ip_address(addr))
    if not ips:
        raise BlockedUrlError(f"Could not resolve host: {host}")
    return ips


def validate_public_url(url: str) -> None:
    """Raise :class:`BlockedUrlError` unless ``url`` is an http(s) URL that resolves only to
    public, routable IP addresses."""
    parsed = httpx.URL(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise BlockedUrlError(f"Unsupported URL scheme: {parsed.scheme or '(none)'}")
    host = parsed.host
    if not host:
        raise BlockedUrlError("URL has no host")
    for ip in _resolve_host(host):
        if _ip_is_blocked(ip):
            raise BlockedUrlError(f"URL resolves to a non-public address: {ip}")


def safe_get(
    url: str,
    *,
    timeout: float = 30.0,
    max_redirects: int = 5,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Fetch ``url`` with the SSRF guard applied to every hop.

    Auto-redirects are disabled; each redirect target is re-validated before it is fetched, so a
    public URL cannot redirect into an internal address.
    """
    request_headers = {"User-Agent": _DEFAULT_USER_AGENT}
    if headers:
        request_headers.update(headers)

    current = url
    with httpx.Client(follow_redirects=False, timeout=timeout, headers=request_headers) as client:
        for _ in range(max_redirects + 1):
            validate_public_url(current)
            resp = client.get(current)
            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    return resp
                current = str(resp.url.join(location))
                continue
            return resp
    raise BlockedUrlError("Too many redirects")
