import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, get_optional_user, require_role
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, NotFoundException, RateLimitException
from app.core.rate_limit import upload_rate_limiter
from app.core.s3_urls import generate_internal_presigned_url
from app.models.enums import UserRole, VideoVisibility
from app.models.user import User
from app.repositories.video import VideoRepository
from app.schemas.video import GrantAccessRequest, VideoAccessResponse, VideoBaseResponse
from app.services.access import VideoAccessService
from app.services.media import MediaService

router = APIRouter(prefix="/videos", tags=["Videos & Access Control"])


@router.post(
    "/upload",
    response_model=VideoBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузка видео и опционального превью",
    description=(
        "Принимает видеофайл через multipart/form-data. Проверяет магические байты видеоконтейнера "
        "(MP4/WebM/MKV/MOV), лимит размера и стримит файл напрямую в MinIO без буферизации в RAM. "
        "Создает запись в БД и отправляет задачу в очередь воркера FFmpeg."
    ),
)
async def upload_video(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    description: Annotated[str | None, Form()] = None,
    visibility: Annotated[VideoVisibility, Form()] = VideoVisibility.PUBLIC,
    video: UploadFile = File(..., description="Видеофайл"),
    thumbnail: UploadFile | None = File(None, description="Опциональное превью (JPEG, PNG, WebP)"),
) -> VideoBaseResponse:
    # Rate limit check on uploads
    allowed, _ = await upload_rate_limiter.is_allowed(f"upload:{current_user.id}")
    if not allowed:
        raise RateLimitException("Превышен лимит загрузок видео. Попробуйте позже.")

    media_service = MediaService(db)
    return await media_service.upload_video(
        owner=current_user,
        title=title,
        description=description,
        visibility=visibility,
        video_file=video,
        thumbnail_file=thumbnail,
    )


@router.get(
    "/{video_id}/verify-access",
    summary="Внутренняя проверка прав доступа для Nginx auth_request",
    description="Возвращает 200 OK при наличии доступа или 403 Forbidden.",
)
async def verify_video_access(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> Response:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_id(video_id)
    if not video:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    access_service = VideoAccessService(db)
    can_view, _ = await access_service.can_view_video(video, current_user)
    if not can_view:
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    return Response(status_code=status.HTTP_200_OK)


@router.get(
    "/{video_id}/stream",
    summary="Стриминг видео с поддержкой HTTP Range и проверкой прав доступа",
    description=(
        "Проверяет права доступа к видео. При успехе возвращает заголовок X-Accel-Redirect "
        "для мгновенной раздачи через Nginx с поддержкой Range-запросов (206 Partial Content)."
    ),
)
async def stream_video(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> Response:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_id(video_id)
    if not video:
        raise NotFoundException("Видео не найдено")

    access_service = VideoAccessService(db)
    can_view, reason = await access_service.can_view_video(video, current_user)
    if not can_view:
        raise ForbiddenException(reason or "Доступ запрещен")

    key = video.processed_object_key or video.raw_object_key
    if not key:
        raise NotFoundException("Медиафайл видео не готов")

    # Generate presigned S3 URL valid for 300 seconds (for Nginx internal fetch)
    presigned = await generate_internal_presigned_url(settings.MINIO_VIDEOS_BUCKET, key, expires_in=300)
    # Extract path and query after endpoint: e.g. /videos/processed/...?...
    s3_subpath = presigned.replace(settings.MINIO_ENDPOINT, "")

    headers = {
        "X-Accel-Redirect": f"/_internal_s3{s3_subpath}",
        "Content-Type": "video/mp4",
    }
    return Response(content=b"", status_code=status.HTTP_200_OK, headers=headers)


@router.get(
    "/{video_id}/thumbnail",
    summary="Отдача превью видео с поддержкой X-Accel-Redirect",
)
async def get_video_thumbnail(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> Response:
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_id(video_id)
    if not video or not video.thumbnail_object_key:
        raise NotFoundException("Превью не найдено")

    access_service = VideoAccessService(db)
    can_view, _ = await access_service.can_view_video(video, current_user)
    if not can_view:
        raise ForbiddenException("Доступ к превью ограничен")

    presigned = await generate_internal_presigned_url(
        settings.MINIO_THUMBNAILS_BUCKET, video.thumbnail_object_key, expires_in=300
    )
    s3_subpath = presigned.replace(settings.MINIO_ENDPOINT, "")

    headers = {
        "X-Accel-Redirect": f"/_internal_s3{s3_subpath}",
        "Content-Type": "image/jpeg",
    }
    return Response(content=b"", status_code=status.HTTP_200_OK, headers=headers)


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
