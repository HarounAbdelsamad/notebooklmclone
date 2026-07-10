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
    """Verify a Clerk-issued RS256 JWT and return its claims. Raises on failure.

    Fails closed in production: issuer and audience MUST be configured there, so the
    issuer/audience checks can never be silently skipped. Dev/local stays flexible (both
    optional) to ease running against a test tenant.
    """
    if settings.is_production and (not settings.clerk_issuer or not settings.clerk_audience):
        raise RuntimeError(
            "CLERK_ISSUER and CLERK_AUDIENCE must be configured in production to verify tokens"
        )

    require = ["exp", "iat", "sub"]
    decode_kwargs: dict = {"algorithms": ["RS256"]}
    if settings.clerk_issuer:
        decode_kwargs["issuer"] = settings.clerk_issuer
        require.append("iss")
    if settings.clerk_audience:
        decode_kwargs["audience"] = settings.clerk_audience
        require.append("aud")
    decode_kwargs["options"] = {"require": require}

    signing_key = _client().get_signing_key_from_jwt(token)
    return jwt.decode(token, signing_key.key, **decode_kwargs)
