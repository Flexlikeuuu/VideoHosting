import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import VideoStatus, VideoVisibility

if TYPE_CHECKING:
    from app.models.community import Comment, Report, VideoReaction
    from app.models.playlist import PlaylistItem
    from app.models.user import User


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[VideoStatus] = mapped_column(
        String(32), default=VideoStatus.UPLOADING, nullable=False
    )
    visibility: Mapped[VideoVisibility] = mapped_column(
        String(32), default=VideoVisibility.PUBLIC, nullable=False
    )
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    views_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_object_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processed_object_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    thumbnail_object_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="videos")
    access_list: Mapped[list["VideoAccess"]] = relationship(
        "VideoAccess", back_populates="video", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="video", cascade="all, delete-orphan"
    )
    reactions: Mapped[list["VideoReaction"]] = relationship(
        "VideoReaction", back_populates="video", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="video", cascade="all, delete-orphan"
    )
    playlist_items: Mapped[list["PlaylistItem"]] = relationship(
        "PlaylistItem", back_populates="video", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("duration_seconds >= 0", name="chk_video_duration_non_negative"),
        Index(
            "ix_videos_public_feed",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
            postgresql_where=(
                (status == VideoStatus.READY)
                & (visibility == VideoVisibility.PUBLIC)
                & (is_hidden.is_(False))
            ),
        ),
        Index(
            "ix_videos_owner_created",
            "owner_id",
            "created_at",
        ),
    )


class VideoAccess(Base):
    __tablename__ = "video_access_list"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video: Mapped["Video"] = relationship("Video", back_populates="access_list")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    grantor: Mapped["User"] = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        UniqueConstraint("video_id", "user_id", name="uq_video_access_video_user"),
    )
