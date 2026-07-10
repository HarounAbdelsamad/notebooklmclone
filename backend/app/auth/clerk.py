"""Clerk JWT verification against the project's JWKS endpoint."""

import jwt
from jwt import PyJWKClient

from app.config import settings

_jwks_client: PyJWKClient | None = None


def _client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.clerk_jwks_url:
            raise RuntimeError("CLERK_JWKS_URL is not configured")
        # PyJWKClient fetches and caches signing keys.
        _jwks_client = PyJWKClient(settings.clerk_jwks_url, cache_keys=True)
    return _jwks_client


def verify_token(token: str) -> dict:
    """Verify a Clerk-issued RS256 JWT and return its claims. Raises on failure."""
    signing_key = _client().get_signing_key_from_jwt(token)
    decode_kwargs: dict = {
        "algorithms": ["RS256"],
        "options": {"require": ["exp", "iat", "sub"]},
    }
    if settings.clerk_issuer:
        decode_kwargs["issuer"] = settings.clerk_issuer
    if settings.clerk_audience:
        decode_kwargs["audience"] = settings.clerk_audience
    return jwt.decode(token, signing_key.key, **decode_kwargs)
