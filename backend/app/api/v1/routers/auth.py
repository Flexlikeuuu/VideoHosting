from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.core.exceptions import RateLimitException
from app.core.rate_limit import auth_rate_limiter
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    """Attach httpOnly cookies for access and refresh tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear session cookies upon logout."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создает пользователя с ролью 'user', выдает токены и устанавливает httpOnly cookies.",
)
async def register(
    req: UserRegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    allowed, _ = await auth_rate_limiter.is_allowed(f"register:{client_ip}")
    if not allowed:
        raise RateLimitException("Слишком много попыток регистрации. Подождите минуту.")

    service = AuthService(db)
    token_resp, raw_refresh = await service.register(req)
    _set_auth_cookies(response, token_resp.access_token, raw_refresh)
    return token_resp


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Авторизация пользователя (логин)",
    description="Проверяет пароль через Argon2id, выдает JWT и защищает от брутфорса через Redis rate-limit.",
)
async def login(
    req: UserLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    allowed, _ = await auth_rate_limiter.is_allowed(
        f"login:{client_ip}:{req.username_or_email}"
    )
    if not allowed:
        raise RateLimitException("Слишком много попыток входа. Попробуйте через минуту.")

    service = AuthService(db)
    token_resp, raw_refresh = await service.login(req)
    _set_auth_cookies(response, token_resp.access_token, raw_refresh)
    return token_resp


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление пары токенов",
    description="Ротация refresh-токена из httpOnly cookie и выпуск нового access_token.",
)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    service = AuthService(db)
    token_resp, new_raw_refresh = await service.refresh(refresh_token)
    _set_auth_cookies(response, token_resp.access_token, new_raw_refresh)
    return token_resp


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход из системы (logout)",
    description="Отзывает текущую сессию в БД и очищает httpOnly cookies.",
)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    service = AuthService(db)
    await service.logout(refresh_token)
    _clear_auth_cookies(response)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получение профиля текущего пользователя",
    description="Возвращает данные авторизованного пользователя и его роль (user/moderator/admin).",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
