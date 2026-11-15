import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.community import Report
from app.models.enums import ReportStatus, VideoStatus, VideoVisibility
from app.models.video import Video, VideoAccess


class VideoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, video_id: uuid.UUID) -> Video | None:
        stmt = (
            select(Video)
            .where(Video.id == video_id)
            .options(selectinload(Video.owner))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_feed(
        self, sort: str = "new", limit: int = 20, offset: int = 0
    ) -> Sequence[Video]:
        """Public feed: only ready + public + not hidden."""
        stmt = (
            select(Video)
            .where(
                Video.status == VideoStatus.READY,
                Video.visibility == VideoVisibility.PUBLIC,
                Video.is_hidden.is_(False),
            )
            .options(selectinload(Video.owner))
            .limit(limit)
            .offset(offset)
        )
        if sort == "popular":
            stmt = stmt.order_by(Video.views_count.desc(), Video.created_at.desc())
        else:
            stmt = stmt.order_by(Video.created_at.desc())

        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def search(self, query: str, limit: int = 20, offset: int = 0) -> Sequence[Video]:
        """Search videos by title or description."""
        search_pattern = f"%{query}%"
        stmt = (
            select(Video)
            .where(
                Video.status == VideoStatus.READY,
                Video.visibility == VideoVisibility.PUBLIC,
                Video.is_hidden.is_(False),
                or_(
                    Video.title.ilike(search_pattern),
                    Video.description.ilike(search_pattern),
                ),
            )
            .options(selectinload(Video.owner))
            .order_by(Video.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_channel_videos(
        self, channel_owner_id: uuid.UUID, is_owner: bool = False, is_moderator: bool = False
    ) -> Sequence[Video]:
        """List videos of a channel. Owner/moderator sees private and hidden as well."""
        stmt = select(Video).where(Video.owner_id == channel_owner_id).options(selectinload(Video.owner)).order_by(Video.created_at.desc())
        if not (is_owner or is_moderator):
            stmt = stmt.where(
                Video.status == VideoStatus.READY,
                Video.visibility == VideoVisibility.PUBLIC,
                Video.is_hidden.is_(False),
            )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def count_channel_videos(self, channel_owner_id: uuid.UUID, is_owner: bool = False) -> int:
        stmt = select(func.count(Video.id)).where(Video.owner_id == channel_owner_id)
        if not is_owner:
            stmt = stmt.where(
                Video.status == VideoStatus.READY,
                Video.visibility == VideoVisibility.PUBLIC,
                Video.is_hidden.is_(False),
            )
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def create(self, video: Video) -> Video:
        self.session.add(video)
        await self.session.flush()
        return video

    async def has_access_grant(
        self, video_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        stmt = select(VideoAccess.id).where(
            VideoAccess.video_id == video_id,
            VideoAccess.user_id == user_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def grant_access(
        self, video_id: uuid.UUID, user_id: uuid.UUID, granted_by: uuid.UUID
    ) -> VideoAccess:
        access = VideoAccess(
            video_id=video_id,
            user_id=user_id,
            granted_by=granted_by,
        )
        self.session.add(access)
        await self.session.flush()
        return access

    async def revoke_access(
        self, video_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        stmt = delete(VideoAccess).where(
            VideoAccess.video_id == video_id,
            VideoAccess.user_id == user_id,
        )
        res = await self.session.execute(stmt)
        return (res.rowcount or 0) > 0

    async def list_access(self, video_id: uuid.UUID) -> Sequence[VideoAccess]:
        stmt = (
            select(VideoAccess)
            .where(VideoAccess.video_id == video_id)
            .options(selectinload(VideoAccess.user))
            .order_by(VideoAccess.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def has_pending_reports(self, video_id: uuid.UUID) -> bool:
        stmt = select(Report.id).where(
            Report.video_id == video_id,
            Report.status == ReportStatus.PENDING,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None
