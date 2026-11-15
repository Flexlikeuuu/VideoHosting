import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.token import TokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = TokenRepository(session)

    async def register(self, req: UserRegisterRequest) -> tuple[TokenResponse, str]:
        """Register a new user and issue tokens."""
        if await self.user_repo.get_by_email(req.email):
            raise ConflictException("Пользователь с таким email уже существует")
        if await self.user_repo.get_by_username(req.username):
            raise ConflictException("Пользователь с таким username уже существует")

        user = User(
            email=req.email.lower(),
            username=req.username,
            password_hash=hash_password(req.password),
            role=UserRole.USER,
            channel_name=req.channel_name or req.username,
        )
        await self.user_repo.create(user)
        await self.session.commit()
        await self.session.refresh(user)

        return await self._issue_session(user)

    async def login(self, req: UserLoginRequest) -> tuple[TokenResponse, str]:
        """Authenticate user and return (TokenResponse, raw_refresh_token)."""
        user = await self.user_repo.get_by_identifier(req.username_or_email)
        if not user or not verify_password(req.password, user.password_hash):
            raise UnauthorizedException("Неверный логин или пароль")

        if not user.is_active:
            raise UnauthorizedException("Аккаунт заблокирован")

        return await self._issue_session(user)

    async def refresh(self, raw_refresh_token: str | None) -> tuple[TokenResponse, str]:
        """Rotate refresh token and issue a new access token."""
        if not raw_refresh_token:
            raise UnauthorizedException("Refresh токен отсутствует")

        token_hash = hash_refresh_token(raw_refresh_token)
        token = await self.token_repo.get_valid_by_hash(token_hash)
        if not token:
            raise UnauthorizedException("Недействительный или отозванный refresh токен")

        user = await self.user_repo.get_by_id(token.user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("Пользователь не найден или не активен")

        # Revoke old token (rotation)
        await self.token_repo.revoke(token.id)
        # Issue new session
        token_resp, new_raw_refresh = await self._issue_session(user)
        return token_resp, new_raw_refresh

    async def logout(self, raw_refresh_token: str | None) -> None:
        """Revoke current refresh token session."""
        if raw_refresh_token:
            token_hash = hash_refresh_token(raw_refresh_token)
            token = await self.token_repo.get_valid_by_hash(token_hash)
            if token:
                await self.token_repo.revoke(token.id)
                await self.session.commit()

    async def _issue_session(self, user: User) -> tuple[TokenResponse, str]:
        raw_refresh = secrets.token_urlsafe(48)
        token_hash = hash_refresh_token(raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.token_repo.create(user.id, token_hash, expires_at)
        await self.session.commit()

        access_token = create_access_token(str(user.id), user.role)
        return (
            TokenResponse(
                access_token=access_token,
                user=UserResponse.model_validate(user),
            ),
            raw_refresh,
        )
