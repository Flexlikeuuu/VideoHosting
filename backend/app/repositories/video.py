import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.community import Report
from app.models.enums import ReportStatus
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
