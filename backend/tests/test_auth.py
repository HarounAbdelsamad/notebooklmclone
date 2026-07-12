import pytest

from app.auth import clerk


def test_verify_token_fails_closed_without_issuer_in_production(monkeypatch):
    monkeypatch.setattr(clerk.settings, "environment", "production")
    monkeypatch.setattr(clerk.settings, "clerk_issuer", "")
    monkeypatch.setattr(clerk.settings, "clerk_audience", "https://api.example.com")
    with pytest.raises(RuntimeError):
        clerk.verify_token("a.b.c")


def test_verify_token_audience_optional_in_production(monkeypatch):
    # Audience is optional (Clerk's default session tokens carry no `aud`). With the issuer set and
    # audience blank, the production guard must NOT trip — failure comes later (JWKS fetch/decode),
    # here surfacing as the CLERK_JWKS_URL error rather than the fail-closed RuntimeError.
    monkeypatch.setattr(clerk.settings, "environment", "production")
    monkeypatch.setattr(clerk.settings, "clerk_issuer", "https://clerk.example.com")
    monkeypatch.setattr(clerk.settings, "clerk_audience", "")
    monkeypatch.setattr(clerk.settings, "clerk_jwks_url", "")
    with pytest.raises(RuntimeError, match="CLERK_JWKS_URL"):
        clerk.verify_token("a.b.c")


def test_verify_token_dev_does_not_require_issuer_audience(monkeypatch):
    # Outside production the production guard must not trip; failure comes later (JWKS/decode),
    # not from the fail-closed RuntimeError.
    monkeypatch.setattr(clerk.settings, "environment", "development")
    monkeypatch.setattr(clerk.settings, "clerk_issuer", "")
    monkeypatch.setattr(clerk.settings, "clerk_audience", "")
    monkeypatch.setattr(clerk.settings, "clerk_jwks_url", "")
    with pytest.raises(RuntimeError, match="CLERK_JWKS_URL"):
        clerk.verify_token("a.b.c")
