import uuid
from datetime import datetime, timezone
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import RefreshToken


class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        now = datetime.now(timezone.utc)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def revoke(self, token_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
