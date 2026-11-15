import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str) -> User | None:
        """Find user by username or email."""
        stmt = select(User).where(
            or_(
                User.username == identifier,
                User.email == identifier.lower(),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
