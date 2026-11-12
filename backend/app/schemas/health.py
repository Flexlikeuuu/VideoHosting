from typing import Literal

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    """Health status of a single infrastructure dependency."""

    status: Literal["ok", "error"] = Field(..., description="Статус доступности сервиса")
    detail: str | None = Field(default=None, description="Детали ошибки при недоступности")


class HealthResponse(BaseModel):
    """Aggregated health check response for the API and its dependencies."""

    status: Literal["ok", "degraded"] = Field(..., description="Общий статус системы")
    services: dict[str, DependencyStatus] = Field(
        ...,
        description="Статусы зависимостей: postgres, redis, minio",
        examples=[
            {
                "postgres": {"status": "ok", "detail": None},
                "redis": {"status": "ok", "detail": None},
                "minio": {"status": "ok", "detail": None},
            }
        ],
    )
