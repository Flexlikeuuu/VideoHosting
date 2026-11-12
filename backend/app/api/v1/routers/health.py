from fastapi import APIRouter, Response, status

from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Проверка состояния системы",
    description=(
        "Проверяет подключение к PostgreSQL, Redis и MinIO (включая наличие бакетов "
        "`videos` и `thumbnails`). Возвращает 200 OK при полной работоспособности "
        "или 503 Service Unavailable, если хотя бы одна зависимость недоступна."
    ),
    responses={
        200: {"description": "Все зависимости доступны"},
        503: {"description": "Одна или несколько зависимостей недоступны", "model": HealthResponse},
    },
)
async def health_check(response: Response) -> HealthResponse:
    """Return health status of API and backing infrastructure services."""
    service = HealthService()
    is_healthy, payload = await service.check_all()
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload
