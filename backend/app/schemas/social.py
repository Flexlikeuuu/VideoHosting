from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportStatus, UserRole
from app.schemas.auth import UserResponse
from app.schemas.video import VideoBaseResponse


# --- Reactions ---
class ReactionRequest(BaseModel):
    value: int = Field(..., description="1 = like, -1 = dislike, 0 = remove reaction")


class ReactionResponse(BaseModel):
    likes_count: int
    dislikes_count: int
    user_reaction: int | None = None


# --- Comments ---
class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Текст комментария")


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    author: UserResponse
    content: str
    created_at: datetime
    updated_at: datetime


# --- Channels & Subscriptions ---
class ChannelProfileResponse(BaseModel):
    id: UUID
    username: str
    channel_name: str
    channel_description: str | None = None
    avatar_key: str | None = None
    subscribers_count: int
    is_subscribed: bool
    videos_count: int
    created_at: datetime


class SubscriptionResponse(BaseModel):
    is_subscribed: bool
    subscribers_count: int


# --- Playlists ---
class PlaylistCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150, description="Название плейлиста")
    description: str | None = Field(default=None, max_length=1000)
    is_public: bool = Field(default=True)


class PlaylistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    video: VideoBaseResponse
    added_at: datetime


class PlaylistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    is_public: bool
    owner: UserResponse
    items: list[PlaylistItemResponse] = []
    created_at: datetime
    updated_at: datetime


class PlaylistAddVideoRequest(BaseModel):
    video_id: UUID


# --- Reports & Moderation ---
class ReportCreateRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000, description="Причина жалобы")


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    reporter: UserResponse
    reason: str
    status: ReportStatus
    moderator: UserResponse | None = None
    moderator_comment: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class ResolveReportRequest(BaseModel):
    action: str = Field(
        ..., pattern="^(hide|dismiss)$", description="'hide' = скрыть видео, 'dismiss' = отклонить жалобу"
    )
    comment: str | None = Field(default=None, max_length=1000, description="Комментарий модератора")
