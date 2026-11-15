import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.community import Comment, Report, Subscription, VideoReaction
from app.models.enums import ReportStatus, VideoStatus, VideoVisibility
from app.models.playlist import Playlist, PlaylistItem
from app.models.user import User
from app.models.video import Video


class SocialRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- View Counter ---
    async def increment_views(self, video_id: uuid.UUID) -> int:
        stmt = (
            update(Video)
            .where(Video.id == video_id)
            .values(views_count=Video.views_count + 1)
            .returning(Video.views_count)
        )
        res = await self.session.execute(stmt)
        val = res.scalar_one_or_none()
        await self.session.commit()
        return val or 0

    # --- Reactions ---
    async def get_user_reaction(self, video_id: uuid.UUID, user_id: uuid.UUID) -> int | None:
        stmt = select(VideoReaction.value).where(
            VideoReaction.video_id == video_id,
            VideoReaction.user_id == user_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def set_reaction(self, video_id: uuid.UUID, user_id: uuid.UUID, value: int) -> tuple[int, int]:
        """Set, update, or remove (-1, 0, 1) reaction and atomically update video counts."""
        stmt = select(VideoReaction).where(
            VideoReaction.video_id == video_id,
            VideoReaction.user_id == user_id,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        old_val = existing.value if existing else 0
        new_val = value if value in (1, -1) else 0

        if old_val == new_val:
            # No change
            video = await self.session.get(Video, video_id)
            return (video.likes_count, video.dislikes_count) if video else (0, 0)

        # Update VideoReaction table
        if existing:
            if new_val == 0:
                await self.session.delete(existing)
            else:
                existing.value = new_val
        else:
            if new_val != 0:
                self.session.add(VideoReaction(video_id=video_id, user_id=user_id, value=new_val))

        # Calculate deltas
        likes_delta = (1 if new_val == 1 else 0) - (1 if old_val == 1 else 0)
        dislikes_delta = (1 if new_val == -1 else 0) - (1 if old_val == -1 else 0)

        update_stmt = (
            update(Video)
            .where(Video.id == video_id)
            .values(
                likes_count=func.greatest(0, Video.likes_count + likes_delta),
                dislikes_count=func.greatest(0, Video.dislikes_count + dislikes_delta),
            )
            .returning(Video.likes_count, Video.dislikes_count)
        )
        up_res = await self.session.execute(update_stmt)
        row = up_res.first()
        await self.session.commit()
        return (row[0], row[1]) if row else (0, 0)

    # --- Comments ---
    async def create_comment(self, video_id: uuid.UUID, author_id: uuid.UUID, content: str) -> Comment:
        comment = Comment(video_id=video_id, author_id=author_id, content=content)
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        stmt = select(Comment).where(Comment.id == comment.id).options(selectinload(Comment.author))
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def get_comment(self, comment_id: uuid.UUID) -> Comment | None:
        stmt = select(Comment).where(Comment.id == comment_id).options(selectinload(Comment.author), selectinload(Comment.video))
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_comments(self, video_id: uuid.UUID) -> Sequence[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.video_id == video_id, Comment.is_deleted.is_(False))
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def delete_comment(self, comment_id: uuid.UUID) -> bool:
        stmt = (
            update(Comment)
            .where(Comment.id == comment_id)
            .values(is_deleted=True)
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return (res.rowcount or 0) > 0

    # --- Subscriptions & Channels ---
    async def get_subscribers_count(self, channel_id: uuid.UUID) -> int:
        stmt = select(func.count(Subscription.id)).where(Subscription.channel_id == channel_id)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def is_subscribed(self, subscriber_id: uuid.UUID, channel_id: uuid.UUID) -> bool:
        stmt = select(Subscription.id).where(
            Subscription.subscriber_id == subscriber_id,
            Subscription.channel_id == channel_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def toggle_subscription(self, subscriber_id: uuid.UUID, channel_id: uuid.UUID) -> bool:
        """Returns True if subscribed, False if unsubscribed."""
        stmt = select(Subscription).where(
            Subscription.subscriber_id == subscriber_id,
            Subscription.channel_id == channel_id,
        )
        res = await self.session.execute(stmt)
        sub = res.scalar_one_or_none()
        if sub:
            await self.session.delete(sub)
            await self.session.commit()
            return False
        else:
            self.session.add(Subscription(subscriber_id=subscriber_id, channel_id=channel_id))
            await self.session.commit()
            return True

    # --- Playlists ---
    async def create_playlist(self, owner_id: uuid.UUID, title: str, description: str | None, is_public: bool) -> Playlist:
        pl = Playlist(owner_id=owner_id, title=title, description=description, is_public=is_public)
        self.session.add(pl)
        await self.session.commit()
        await self.session.refresh(pl)
        return pl

    async def get_playlist(self, playlist_id: uuid.UUID) -> Playlist | None:
        self.session.expire_all()
        stmt = (
            select(Playlist)
            .where(Playlist.id == playlist_id)
            .options(
                selectinload(Playlist.owner),
                selectinload(Playlist.items).selectinload(PlaylistItem.video).selectinload(Video.owner),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def add_to_playlist(self, playlist_id: uuid.UUID, video_id: uuid.UUID) -> PlaylistItem:
        # Get max position
        pos_stmt = select(func.coalesce(func.max(PlaylistItem.position), -1)).where(PlaylistItem.playlist_id == playlist_id)
        pos_res = await self.session.execute(pos_stmt)
        next_pos = (pos_res.scalar() or -1) + 1

        item = PlaylistItem(playlist_id=playlist_id, video_id=video_id, position=next_pos)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def remove_from_playlist(self, playlist_id: uuid.UUID, video_id: uuid.UUID) -> bool:
        stmt = delete(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.video_id == video_id,
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return (res.rowcount or 0) > 0

    async def delete_playlist(self, playlist_id: uuid.UUID) -> bool:
        stmt = delete(Playlist).where(Playlist.id == playlist_id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return (res.rowcount or 0) > 0

    # --- Reports & Moderation ---
    async def create_report(self, video_id: uuid.UUID, reporter_id: uuid.UUID, reason: str) -> Report:
        rep = Report(video_id=video_id, reporter_id=reporter_id, reason=reason, status=ReportStatus.PENDING)
        self.session.add(rep)
        await self.session.commit()
        await self.session.refresh(rep)
        stmt = select(Report).where(Report.id == rep.id).options(selectinload(Report.reporter))
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def list_reports(self, status: ReportStatus | None = None) -> Sequence[Report]:
        stmt = select(Report).options(selectinload(Report.reporter), selectinload(Report.moderator)).order_by(Report.created_at.desc())
        if status:
            stmt = stmt.where(Report.status == status)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def resolve_report(self, report_id: uuid.UUID, moderator_id: uuid.UUID, action: str, comment: str | None) -> Report | None:
        report = await self.session.get(Report, report_id)
        if not report:
            return None

        report.status = ReportStatus.RESOLVED if action == "hide" else ReportStatus.DISMISSED
        report.moderator_id = moderator_id
        report.moderator_comment = comment

        if action == "hide":
            await self.session.execute(
                update(Video)
                .where(Video.id == report.video_id)
                .values(is_hidden=True, hidden_reason=comment or f"Скрыто модератором по жалобе {report_id}")
            )

        await self.session.commit()
        stmt = select(Report).where(Report.id == report_id).options(selectinload(Report.reporter), selectinload(Report.moderator))
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def unhide_video(self, video_id: uuid.UUID) -> bool:
        stmt = update(Video).where(Video.id == video_id).values(is_hidden=False, hidden_reason=None)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return (res.rowcount or 0) > 0
