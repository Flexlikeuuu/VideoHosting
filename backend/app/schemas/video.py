from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VideoStatus, VideoVisibility
from app.schemas.auth import UserResponse


class GrantAccessRequest(BaseModel):
    username_or_email: str = Field(
        ..., description="Логин или Email пользователя, которому выдается доступ"
    )


class VideoAccessUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    channel_name: str


class VideoAccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    user: VideoAccessUserResponse
    created_at: datetime


class VideoBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    status: VideoStatus
    visibility: VideoVisibility
    is_hidden: bool
    hidden_reason: str | None = None
    duration_seconds: int | None = None
    views_count: int
    likes_count: int
    dislikes_count: int
    thumbnail_object_key: str | None = None
    created_at: datetime
    owner: UserResponse
