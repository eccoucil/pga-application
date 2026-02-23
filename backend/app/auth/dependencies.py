"""Authentication dependencies for FastAPI."""

import logging

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Cache for JWKS to avoid fetching on every request
_jwks_cache: dict | None = None


async def _fetch_jwks(supabase_url: str) -> dict:
    """Fetch JWKS from Supabase."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


def _get_signing_key(token: str, jwks: dict) -> dict:
    """Get the signing key from JWKS that matches the token's kid."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise JWTError("Unable to find matching key in JWKS")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate Supabase JWT token.

    Supports both ES256 (Supabase Auth v2) and HS256 tokens.
    Fetches JWKS from Supabase for ES256 verification.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        Dict with user_id, email, and role from token

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    settings = get_settings()
    token = credentials.credentials

    try:
        # Check the algorithm in the token header
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")

        if alg == "ES256":
            # Supabase Auth v2 uses ES256 with JWKS
            jwks = await _fetch_jwks(settings.supabase_url)
            signing_key = _get_signing_key(token, jwks)

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            # Legacy HS256 with anon key
            payload = jwt.decode(
                token,
                settings.supabase_key,
                algorithms=["HS256"],
                audience="authenticated",
            )

        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role"),
        }
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.HTTPError as e:
        logger.error(f"JWKS fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )


async def verify_client_membership(client_id: str, user_id: str) -> dict:
    """Verify user is a member of the client organization. Returns membership record."""
    from app.db.supabase import get_async_supabase_client_async

    supabase = await get_async_supabase_client_async()
    result = await (
        supabase.table("client_members")
        .select("role")
        .eq("client_id", client_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=403, detail="Not a member of this client")
    return result.data[0]
