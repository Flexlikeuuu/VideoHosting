from arq.connections import RedisSettings

from app.core.config import settings


async def ping_worker(ctx: dict) -> str:
    """Placeholder background task verifying Arq worker execution."""
    return "pong"


class WorkerSettings:
    """Arq worker configuration for background video processing."""

    functions = [ping_worker]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 4
    job_timeout = 1800
