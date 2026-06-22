"""Supabase client singleton."""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import Settings, get_settings


class SupabaseConfigurationError(ValueError):
    """Raised when Supabase credentials are missing or invalid."""


def create_supabase_client(settings: Settings | None = None) -> Client:
    config = settings or get_settings()

    if not config.supabase_url.strip():
        raise SupabaseConfigurationError("SUPABASE_URL is not configured")
    if not config.supabase_service_key.strip():
        raise SupabaseConfigurationError("SUPABASE_SERVICE_KEY is not configured")

    return create_client(config.supabase_url.strip(), config.supabase_service_key.strip())


@lru_cache
def get_supabase_client() -> Client:
    return create_supabase_client(get_settings())


def clear_supabase_client_cache() -> None:
    get_supabase_client.cache_clear()


def check_connection(client: Client | None = None) -> bool:
    """Return True if Supabase is reachable."""
    try:
        db = client or get_supabase_client()
        db.table("reviews").select("id", count="exact").limit(1).execute()
        return True
    except SupabaseConfigurationError:
        return False
    except Exception:
        return False
