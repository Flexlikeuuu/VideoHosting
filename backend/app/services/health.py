import asyncio

from app.core.database import check_db_connection
from app.core.redis import check_redis_connection
from app.core.storage import check_storage_connection
from app.schemas.health import DependencyStatus, HealthResponse


class HealthService:
    """Service that checks connectivity to PostgreSQL, Redis, and MinIO."""

    async def check_all(self) -> tuple[bool, HealthResponse]:
        """Run all dependency checks concurrently and return (is_healthy, payload)."""
        (db_ok, db_err), (redis_ok, redis_err), (s3_ok, s3_err) = await asyncio.gather(
            check_db_connection(),
            check_redis_connection(),
            check_storage_connection(),
        )

        services = {
            "postgres": DependencyStatus(status="ok" if db_ok else "error", detail=db_err),
            "redis": DependencyStatus(status="ok" if redis_ok else "error", detail=redis_err),
            "minio": DependencyStatus(status="ok" if s3_ok else "error", detail=s3_err),
        }
        is_healthy = db_ok and redis_ok and s3_ok
        payload = HealthResponse(
            status="ok" if is_healthy else "degraded",
            services=services,
        )
        return is_healthy, payload
