import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, get_optional_user, require_role
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.video import VideoRepository
from app.schemas.video import GrantAccessRequest, VideoAccessResponse, VideoBaseResponse
from app.services.access import VideoAccessService

router = APIRouter(prefix="/videos", tags=["Videos & Access Control"])


@router.get(
    "/{video_id}",
    response_model=VideoBaseResponse,
    summary="Просмотр информации о видео с проверкой прав",
    description=(
        "Возвращает метаданные видео. Публичные готовые видео доступны всем. "
        "Приватные видео доступны только владельцу, пользователям из списка доступа "
        "или модератору/админу при наличии жалобы."
    ),
    responses={
        200: {"description": "Метаданные видео"},
        403: {"description": "Доступ запрещен (private видео / IDOR)"},
        404: {"description": "Видео не найдено"},
    },
)
async def get_video(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> VideoBaseResponse:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_id(video_id)
    if not video:
        raise NotFoundException("Видео не найдено")

    access_service = VideoAccessService(db)
    can_view, reason = await access_service.can_view_video(video, current_user)
    if not can_view:
        raise ForbiddenException(reason or "Доступ запрещен")

    return VideoBaseResponse.model_validate(video)


@router.post(
    "/{video_id}/access",
    response_model=VideoAccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Предоставление доступа к приватному видео",
    description="Владелец видео может выдать право просмотра по логину или email пользователя.",
    responses={
        201: {"description": "Доступ успешно предоставлен"},
        400: {"description": "Некорректный запрос (например, попытка выдать доступ себе)"},
        403: {"description": "Только владелец может управлять доступом"},
        404: {"description": "Видео или целевой пользователь не найдены"},
    },
)
async def grant_video_access(
    video_id: uuid.UUID,
    req: GrantAccessRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VideoAccessResponse:
    access_service = VideoAccessService(db)
    return await access_service.grant_access(video_id, current_user, req.username_or_email)


@router.delete(
    "/{video_id}/access/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отзыв доступа к приватному видео",
    description="Владелец видео отзывает право просмотра у конкретного пользователя.",
    responses={
        204: {"description": "Доступ успешно отозван"},
        403: {"description": "Только владелец может отзывать доступ"},
        404: {"description": "Запись доступа не найдена"},
    },
)
async def revoke_video_access(
    video_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    access_service = VideoAccessService(db)
    await access_service.revoke_access(video_id, current_user, user_id)


@router.get(
    "/{video_id}/access",
    response_model=list[VideoAccessResponse],
    summary="Список пользователей с доступом к приватному видео",
    description="Доступен только владельцу видео или администратору.",
)
async def list_video_access(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[VideoAccessResponse]:
    access_service = VideoAccessService(db)
    return await access_service.list_access(video_id, current_user)


@router.get(
    "/moderation/test-role-protected",
    summary="Тестовый эндпоинт для проверки RBAC (только moderator и admin)",
    dependencies=[Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))],
)
async def test_moderator_access():
    return {"message": "Доступ разрешен: роль модератора или администратора подтверждена"}
