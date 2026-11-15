from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, get_optional_user
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user import UserRepository
from app.repositories.video import VideoRepository
from app.schemas.social import ChannelProfileResponse, SubscriptionResponse
from app.schemas.video import VideoBaseResponse
from app.services.social import SocialService

router = APIRouter(prefix="/channels", tags=["Channels"])


@router.get(
    "/{username}",
    response_model=ChannelProfileResponse,
    summary="Профиль канала, подписчики и статус подписки",
)
async def get_channel_profile(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> ChannelProfileResponse:
    service = SocialService(db)
    return await service.get_channel_profile(username, current_user)


@router.get(
    "/{username}/videos",
    response_model=list[VideoBaseResponse],
    summary="Список видео канала (владельцу отображаются также private и hidden)",
)
async def get_channel_videos(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> list[VideoBaseResponse]:
    user_repo = UserRepository(db)
    channel_user = await user_repo.get_by_username(username)
    if not channel_user:
        raise NotFoundException("Канал не найден")

    is_owner = bool(current_user and current_user.id == channel_user.id)
    is_moderator = bool(current_user and current_user.role in (UserRole.MODERATOR, UserRole.ADMIN))

    video_repo = VideoRepository(db)
    videos = await video_repo.list_channel_videos(channel_user.id, is_owner=is_owner, is_moderator=is_moderator)
    return [VideoBaseResponse.model_validate(v) for v in videos]


@router.post(
    "/{username}/subscribe",
    response_model=SubscriptionResponse,
    summary="Подписаться / отписаться от канала (toggle)",
)
async def toggle_subscription(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SubscriptionResponse:
    service = SocialService(db)
    return await service.toggle_subscription(username, current_user)
