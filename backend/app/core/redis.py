import asyncio
from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool: ConnectionPool | None = None


def get_redis_client() -> Redis:
    """Return an async Redis client instance bound to current event loop."""
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis_client() -> None:
    """Placeholder for graceful shutdown."""
    pass


async def check_redis_connection() -> tuple[bool, str | None]:
    """Ping Redis to verify connectivity."""
    try:
        client = get_redis_client()
        await client.ping()
        return True, None
    except Exception as exc:
        return False, str(exc)
