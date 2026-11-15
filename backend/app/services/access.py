import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.enums import UserRole, VideoStatus, VideoVisibility
from app.models.user import User
from app.models.video import Video
from app.repositories.user import UserRepository
from app.repositories.video import VideoRepository
from app.schemas.video import VideoAccessResponse, VideoAccessUserResponse


class VideoAccessService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.video_repo = VideoRepository(session)
        self.user_repo = UserRepository(session)

    async def can_view_video(
        self, video: Video, user: User | None
    ) -> tuple[bool, str | None]:
        """
        Evaluate if a user (or anonymous viewer) has permission to view the video.
        Returns (has_access, rejection_reason).

        Rules:
        1. Ready + Public + not hidden -> visible to anyone.
        2. Hidden by moderator -> visible only to owner and moderators/admins.
        3. Private -> visible only to owner, users in video_access_list, or moderators/admins
           (if the video has a pending report under moderation).
        4. Uploading/Processing/Failed -> visible only to owner and admins.
        """
        is_owner = bool(user and user.id == video.owner_id)
        is_moderator_or_admin = bool(
            user and user.role in (UserRole.MODERATOR, UserRole.ADMIN)
        )

        # Video is hidden by moderator
        if video.is_hidden:
            if is_owner or is_moderator_or_admin:
                return True, None
            return False, "Видео скрыто модератором"

        # In-flight statuses
        if video.status != VideoStatus.READY:
            if is_owner or (user and user.role == UserRole.ADMIN):
                return True, None
            return False, "Видео находится в обработке или недоступно"

        # Public ready video
        if video.visibility == VideoVisibility.PUBLIC:
            return True, None

        # Private video checks
        if video.visibility == VideoVisibility.PRIVATE:
            if not user:
                return False, "Приватное видео доступно только авторизованным пользователям"

            if is_owner:
                return True, None

            # Check if user has explicit access grant
            if await self.video_repo.has_access_grant(video.id, user.id):
                return True, None

            # Moderators/admins can view private video ONLY if there is a pending report
            if is_moderator_or_admin:
                has_reports = await self.video_repo.has_pending_reports(video.id)
                if has_reports:
                    return True, None

            return False, "Доступ к приватному видео ограничен владельцем"

        return False, "Доступ запрещен"

    async def grant_access(
        self, video_id: uuid.UUID, owner_user: User, identifier: str
    ) -> VideoAccessResponse:
        """Owner grants access to a private video to another user by username or email."""
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        if video.owner_id != owner_user.id and owner_user.role != UserRole.ADMIN:
            raise ForbiddenException("Только владелец может управлять доступом к видео")

        target_user = await self.user_repo.get_by_identifier(identifier)
        if not target_user:
            raise NotFoundException("Пользователь не найден")

        if target_user.id == video.owner_id:
            raise BadRequestException("Владелец уже имеет доступ к своему видео")

        if await self.video_repo.has_access_grant(video.id, target_user.id):
            raise BadRequestException("Доступ этому пользователю уже предоставлен")

        access = await self.video_repo.grant_access(
            video_id=video.id,
            user_id=target_user.id,
            granted_by=owner_user.id,
        )
        await self.session.commit()

        return VideoAccessResponse(
            id=access.id,
            video_id=access.video_id,
            user=VideoAccessUserResponse.model_validate(target_user),
            created_at=access.created_at,
        )

    async def revoke_access(
        self, video_id: uuid.UUID, owner_user: User, user_id: uuid.UUID
    ) -> None:
        """Owner revokes access to a private video."""
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        if video.owner_id != owner_user.id and owner_user.role != UserRole.ADMIN:
            raise ForbiddenException("Только владелец может управлять доступом к видео")

        deleted = await self.video_repo.revoke_access(video_id, user_id)
        if not deleted:
            raise NotFoundException("Запись доступа не найдена")

        await self.session.commit()

    async def list_access(
        self, video_id: uuid.UUID, owner_user: User
    ) -> list[VideoAccessResponse]:
        """Owner lists users granted access to the private video."""
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            raise NotFoundException("Видео не найдено")

        if video.owner_id != owner_user.id and owner_user.role != UserRole.ADMIN:
            raise ForbiddenException("Только владелец может просматривать список доступа")

        grants = await self.video_repo.list_access(video_id)
        return [
            VideoAccessResponse(
                id=g.id,
                video_id=g.video_id,
                user=VideoAccessUserResponse.model_validate(g.user),
                created_at=g.created_at,
            )
            for g in grants
        ]
