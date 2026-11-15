import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user import UserRepository


async def get_optional_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token_cookie: Annotated[str | None, Cookie(alias="access_token")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """Extract authenticated user if access token is present in cookie or Authorization header."""
    token: str | None = None
    if access_token_cookie:
        token = access_token_cookie
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError):
        return None

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        return None

    return user


async def get_current_user(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> User:
    """Enforce authentication, raising 401 Unauthorized if anonymous."""
    if not user:
        raise UnauthorizedException("Необходима авторизация")
    return user


def require_role(*roles: UserRole):
    """Enforce RBAC role requirements."""

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise ForbiddenException("Недостаточно прав доступа для данной роли")
        return current_user

    return role_checker
