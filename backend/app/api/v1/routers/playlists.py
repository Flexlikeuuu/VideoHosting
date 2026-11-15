import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, get_optional_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.social import (
    PlaylistAddVideoRequest,
    PlaylistCreateRequest,
    PlaylistResponse,
)
from app.services.social import SocialService

router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.post(
    "",
    response_model=PlaylistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание нового плейлиста",
)
async def create_playlist(
    req: PlaylistCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlaylistResponse:
    service = SocialService(db)
    return await service.create_playlist(current_user, req.title, req.description, req.is_public)


@router.get(
    "/{playlist_id}",
    response_model=PlaylistResponse,
    summary="Получение плейлиста с входящими в него видео",
)
async def get_playlist(
    playlist_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> PlaylistResponse:
    service = SocialService(db)
    return await service.get_playlist(playlist_id, current_user)


@router.post(
    "/{playlist_id}/videos",
    response_model=PlaylistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавление видео в плейлист",
)
async def add_video_to_playlist(
    playlist_id: uuid.UUID,
    req: PlaylistAddVideoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlaylistResponse:
    service = SocialService(db)
    return await service.add_video_to_playlist(playlist_id, req.video_id, current_user)


@router.delete(
    "/{playlist_id}/videos/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление видео из плейлиста",
)
async def remove_video_from_playlist(
    playlist_id: uuid.UUID,
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    service = SocialService(db)
    await service.remove_video_from_playlist(playlist_id, video_id, current_user)


@router.delete(
    "/{playlist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление плейлиста",
)
async def delete_playlist(
    playlist_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    service = SocialService(db)
    await service.delete_playlist(playlist_id, current_user)
