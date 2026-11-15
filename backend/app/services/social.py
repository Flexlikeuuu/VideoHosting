import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.redis import get_redis_client
from app.models.enums import ReportStatus, UserRole
from app.models.user import User
from app.repositories.social import SocialRepository
from app.repositories.user import UserRepository
from app.repositories.video import VideoRepository
from app.schemas.social import (
    ChannelProfileResponse,
    CommentResponse,
    PlaylistItemResponse,
    PlaylistResponse,
    ReactionResponse,
    ReportResponse,
    SubscriptionResponse,
)
from app.schemas.video import VideoBaseResponse


class SocialService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.social_repo = SocialRepository(session)
        self.video_repo = VideoRepository(session)
        self.user_repo = UserRepository(session)

    # --- View deduplication ---
    async def record_view(self, video_id: uuid.UUID, client_identifier: str) -> int:
        """Deduplicate views in Redis (TTL 60s per user/IP and video)."""
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        redis = get_redis_client()
        view_key = f"view:{video_id}:{client_identifier}"
        # Set NX with 60s expire
        is_new = await redis.set(view_key, "1", ex=60, nx=True)
        if is_new:
            return await self.social_repo.increment_views(video_id)
        return video.views_count

    # --- Reactions ---
    async def set_reaction(
        self, video_id: uuid.UUID, user: User, value: int
    ) -> ReactionResponse:
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        likes, dislikes = await self.social_repo.set_reaction(video_id, user.id, value)
        user_reaction = await self.social_repo.get_user_reaction(video_id, user.id)
        return ReactionResponse(
            likes_count=likes,
            dislikes_count=dislikes,
            user_reaction=user_reaction,
        )

    # --- Comments ---
    async def add_comment(
        self, video_id: uuid.UUID, author: User, content: str
    ) -> CommentResponse:
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        comment = await self.social_repo.create_comment(video_id, author.id, content)
        return CommentResponse.model_validate(comment)

    async def list_comments(self, video_id: uuid.UUID) -> list[CommentResponse]:
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        comments = await self.social_repo.list_comments(video_id)
        return [CommentResponse.model_validate(c) for c in comments]

    async def delete_comment(self, comment_id: uuid.UUID, user: User) -> None:
        comment = await self.social_repo.get_comment(comment_id)
        if not comment or comment.is_deleted:
            raise NotFoundException("Комментарий не найден")

        # Can delete if: author of comment, owner of the video, or moderator/admin
        is_comment_author = comment.author_id == user.id
        is_video_owner = comment.video.owner_id == user.id
        is_moderator = user.role in (UserRole.MODERATOR, UserRole.ADMIN)

        if not (is_comment_author or is_video_owner or is_moderator):
            raise ForbiddenException("Недостаточно прав для удаления комментария")

        await self.social_repo.delete_comment(comment_id)

    # --- Channels & Subscriptions ---
    async def get_channel_profile(
        self, username: str, current_user: User | None
    ) -> ChannelProfileResponse:
        channel_user = await self.user_repo.get_by_username(username)
        if not channel_user:
            raise NotFoundException("Канал не найден")

        is_owner = bool(current_user and current_user.id == channel_user.id)
        subs_count = await self.social_repo.get_subscribers_count(channel_user.id)
        is_sub = (
            await self.social_repo.is_subscribed(current_user.id, channel_user.id)
            if current_user
            else False
        )
        videos_count = await self.video_repo.count_channel_videos(
            channel_user.id, is_owner=is_owner
        )

        return ChannelProfileResponse(
            id=channel_user.id,
            username=channel_user.username,
            channel_name=channel_user.channel_name,
            channel_description=channel_user.channel_description,
            avatar_key=channel_user.avatar_key,
            subscribers_count=subs_count,
            is_subscribed=is_sub,
            videos_count=videos_count,
            created_at=channel_user.created_at,
        )

    async def toggle_subscription(
        self, username: str, subscriber: User
    ) -> SubscriptionResponse:
        channel_user = await self.user_repo.get_by_username(username)
        if not channel_user:
            raise NotFoundException("Канал не найден")

        if channel_user.id == subscriber.id:
            raise BadRequestException("Нельзя подписаться на собственный канал")

        is_sub = await self.social_repo.toggle_subscription(subscriber.id, channel_user.id)
        subs_count = await self.social_repo.get_subscribers_count(channel_user.id)
        return SubscriptionResponse(is_subscribed=is_sub, subscribers_count=subs_count)

    # --- Playlists ---
    async def create_playlist(
        self, owner: User, title: str, description: str | None, is_public: bool
    ) -> PlaylistResponse:
        pl = await self.social_repo.create_playlist(owner.id, title, description, is_public)
        pl_full = await self.social_repo.get_playlist(pl.id)
        return PlaylistResponse.model_validate(pl_full)

    async def get_playlist(
        self, playlist_id: uuid.UUID, user: User | None
    ) -> PlaylistResponse:
        pl = await self.social_repo.get_playlist(playlist_id)
        if not pl:
            raise NotFoundException("Плейлист не найден")

        if not pl.is_public:
            if not user or (user.id != pl.owner_id and user.role != UserRole.ADMIN):
                raise ForbiddenException("Плейлист является приватным")

        return PlaylistResponse.model_validate(pl)

    async def add_video_to_playlist(
        self, playlist_id: uuid.UUID, video_id: uuid.UUID, user: User
    ) -> PlaylistResponse:
        pl = await self.social_repo.get_playlist(playlist_id)
        if not pl:
            raise NotFoundException("Плейлист не найден")
        if pl.owner_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenException("Только владелец может добавлять видео в плейлист")

        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        await self.social_repo.add_to_playlist(playlist_id, video_id)
        pl_updated = await self.social_repo.get_playlist(playlist_id)
        return PlaylistResponse.model_validate(pl_updated)

    async def remove_video_from_playlist(
        self, playlist_id: uuid.UUID, video_id: uuid.UUID, user: User
    ) -> None:
        pl = await self.social_repo.get_playlist(playlist_id)
        if not pl:
            raise NotFoundException("Плейлист не найден")
        if pl.owner_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenException("Только владелец может удалять видео из плейлиста")

        deleted = await self.social_repo.remove_from_playlist(playlist_id, video_id)
        if not deleted:
            raise NotFoundException("Видео не найдено в плейлисте")

    async def delete_playlist(self, playlist_id: uuid.UUID, user: User) -> None:
        pl = await self.social_repo.get_playlist(playlist_id)
        if not pl:
            raise NotFoundException("Плейлист не найден")
        if pl.owner_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenException("Только владелец может удалить плейлист")

        await self.social_repo.delete_playlist(playlist_id)

    # --- Reports & Moderation ---
    async def create_report(
        self, video_id: uuid.UUID, reporter: User, reason: str
    ) -> ReportResponse:
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        rep = await self.social_repo.create_report(video_id, reporter.id, reason)
        return ReportResponse.model_validate(rep)

    async def list_reports(self, status_filter: ReportStatus | None) -> list[ReportResponse]:
        reports = await self.social_repo.list_reports(status_filter)
        return [ReportResponse.model_validate(r) for r in reports]

    async def resolve_report(
        self, report_id: uuid.UUID, moderator: User, action: str, comment: str | None
    ) -> ReportResponse:
        rep = await self.social_repo.resolve_report(report_id, moderator.id, action, comment)
        if not rep:
            raise NotFoundException("Жалоба не найдена")
        return ReportResponse.model_validate(rep)

    async def unhide_video(self, video_id: uuid.UUID) -> None:
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")
        await self.social_repo.unhide_video(video_id)
