from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта")
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Логин (буквы, цифры, дефис, подчеркивание)",
    )
    password: str = Field(
        ..., min_length=6, max_length=128, description="Пароль пользователя"
    )
    channel_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Отображаемое имя канала (по умолчанию равно username)",
    )


class UserLoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Логин или Email пользователя")
    password: str = Field(..., description="Пароль пользователя")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: str
    role: UserRole
    channel_name: str
    channel_description: str | None = None
    avatar_key: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Короткоживущий JWT-токен")
    token_type: str = Field(default="bearer")
    user: UserResponse
