import pytest

from app.utils import net
from app.utils.net import BlockedUrlError, validate_public_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.0.0.1:8000/admin",
        "https://10.0.0.5/",
        "http://192.168.1.10/",
        "http://172.16.0.1/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata (link-local)
        "http://0.0.0.0/",
        "http://[::1]/",  # IPv6 loopback
        "http://[::ffff:169.254.169.254]/",  # IPv4-mapped metadata endpoint
        "http://[::ffff:127.0.0.1]/",  # IPv4-mapped loopback
    ],
)
def test_validate_blocks_internal_ip_literals(url):
    with pytest.raises(BlockedUrlError):
        validate_public_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/resource",
        "gopher://example.com/",
        "//example.com/no-scheme",
    ],
)
def test_validate_blocks_non_http_schemes(url):
    with pytest.raises(BlockedUrlError):
        validate_public_url(url)


def test_validate_allows_public_ip_literal():
    # Public, routable address — must not raise (no DNS needed for a literal).
    validate_public_url("https://1.1.1.1/")


def test_validate_blocks_private_after_dns_resolution(monkeypatch):
    def fake_getaddrinfo(host, *args, **kwargs):
        return [(None, None, None, "", ("10.1.2.3", 0))]

    monkeypatch.setattr(net.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(BlockedUrlError):
        validate_public_url("http://internal.example.com/")


def test_validate_allows_public_after_dns_resolution(monkeypatch):
    def fake_getaddrinfo(host, *args, **kwargs):
        return [(None, None, None, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(net.socket, "getaddrinfo", fake_getaddrinfo)
    validate_public_url("http://example.com/")


def test_validate_blocks_if_any_resolved_ip_is_internal(monkeypatch):
    # A host that resolves to both a public and a private IP must be rejected (DNS rebinding).
    def fake_getaddrinfo(host, *args, **kwargs):
        return [
            (None, None, None, "", ("93.184.216.34", 0)),
            (None, None, None, "", ("127.0.0.1", 0)),
        ]

    monkeypatch.setattr(net.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(BlockedUrlError):
        validate_public_url("http://rebind.example.com/")
