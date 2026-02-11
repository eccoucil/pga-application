"""Supabase client connections."""

from supabase import AsyncClient, Client, create_async_client, create_client

from app.config import get_settings

# Singleton instances
_client: Client | None = None
_async_client: AsyncClient | None = None


def get_supabase_client() -> Client:
    """Get synchronous Supabase client (cached singleton)."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
    return _client


def get_async_supabase_client() -> AsyncClient:
    """Get async Supabase client (cached singleton)."""
    global _async_client
    if _async_client is None:
        settings = get_settings()
        # Note: create_async_client is synchronous but returns async client
        import asyncio

        async def _create():
            return await create_async_client(
                settings.supabase_url,
                settings.supabase_service_key,
            )

        # Check if we're in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - schedule creation
            raise RuntimeError("Use get_async_supabase_client_async in async context")
        except RuntimeError:
            # Not in event loop - safe to create
            _async_client = asyncio.run(_create())

    return _async_client


async def get_async_supabase_client_async() -> AsyncClient:
    """Get async Supabase client in async context."""
    global _async_client
    if _async_client is None:
        settings = get_settings()
        _async_client = await create_async_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
    return _async_client


def reset_clients() -> None:
    """Reset clients for testing."""
    global _client, _async_client
    _client = None
    _async_client = None
