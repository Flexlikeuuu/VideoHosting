import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.main import app
from app.models.enums import UserRole, VideoStatus, VideoVisibility
from app.models.user import User
from app.models.video import Video


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_auth_registration_and_login_flow(client: AsyncClient):
    suffix = uuid.uuid4().hex[:6]
    username = f"user_{suffix}"
    email = f"user_{suffix}@example.com"
    password = "StrongPassword123!"

    # 1. Registration
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "channel_name": f"Channel of {username}",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    reg_data = reg_resp.json()
    assert reg_data["user"]["username"] == username
    assert reg_data["user"]["role"] == "user"
    assert "access_token" in reg_data
    assert "access_token" in reg_resp.cookies
    assert "refresh_token" in reg_resp.cookies

    # 2. Duplicate registration returns 409
    dup_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
        },
    )
    assert dup_resp.status_code == 409

    # 3. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.cookies

    # 4. Profile /me with cookie
    me_resp = await client.get("/api/v1/auth/me", cookies=login_resp.cookies)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == username

    # 5. Invalid credentials return 401
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_rbac_protection(client: AsyncClient):
    suffix = uuid.uuid4().hex[:6]

    async with async_session_factory() as session:
        norm_user = User(
            email=f"norm_{suffix}@example.com",
            username=f"norm_{suffix}",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            channel_name="Norm",
        )
        mod_user = User(
            email=f"mod_{suffix}@example.com",
            username=f"mod_{suffix}",
            password_hash=hash_password("password"),
            role=UserRole.MODERATOR,
            channel_name="Mod",
        )
        session.add_all([norm_user, mod_user])
        await session.commit()

    # Anonymous user gets 401
    anon_resp = await client.get("/api/v1/videos/moderation/test-role-protected")
    assert anon_resp.status_code == 401

    # Regular user gets 403 Forbidden
    login_norm = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": norm_user.username, "password": "password"},
    )
    norm_resp = await client.get(
        "/api/v1/videos/moderation/test-role-protected",
        cookies=login_norm.cookies,
    )
    assert norm_resp.status_code == 403

    # Moderator gets 200 OK
    login_mod = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": mod_user.username, "password": "password"},
    )
    mod_resp = await client.get(
        "/api/v1/videos/moderation/test-role-protected",
        cookies=login_mod.cookies,
    )
    assert mod_resp.status_code == 200


@pytest.mark.asyncio
async def test_private_video_access_control_and_grant_flow(client: AsyncClient):
    suffix = uuid.uuid4().hex[:6]

    # Users: Owner, Friend, Stranger
    owner = User(
        email=f"owner_{suffix}@example.com",
        username=f"owner_{suffix}",
        password_hash=hash_password("password"),
        role=UserRole.USER,
        channel_name="Owner Channel",
    )
    friend = User(
        email=f"friend_{suffix}@example.com",
        username=f"friend_{suffix}",
        password_hash=hash_password("password"),
        role=UserRole.USER,
        channel_name="Friend Channel",
    )
    stranger = User(
        email=f"stranger_{suffix}@example.com",
        username=f"stranger_{suffix}",
        password_hash=hash_password("password"),
        role=UserRole.USER,
        channel_name="Stranger Channel",
    )

    async with async_session_factory() as session:
        session.add_all([owner, friend, stranger])
        await session.commit()
        await session.refresh(owner)
        await session.refresh(friend)
        await session.refresh(stranger)

        private_video = Video(
            owner_id=owner.id,
            title="Secret Video",
            description="Very secret",
            status=VideoStatus.READY,
            visibility=VideoVisibility.PRIVATE,
            is_hidden=False,
        )
        session.add(private_video)
        await session.commit()
        await session.refresh(private_video)
        video_id = private_video.id

    # 1. Anonymous request to private video returns 403 Forbidden
    anon_resp = await client.get(f"/api/v1/videos/{video_id}")
    assert anon_resp.status_code == 403

    # 2. Stranger request returns 403 Forbidden
    stranger_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": stranger.username, "password": "password"},
    )
    stranger_resp = await client.get(
        f"/api/v1/videos/{video_id}",
        cookies=stranger_login.cookies,
    )
    assert stranger_resp.status_code == 403

    # 3. Owner request returns 200 OK
    owner_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": owner.username, "password": "password"},
    )
    owner_resp = await client.get(
        f"/api/v1/videos/{video_id}",
        cookies=owner_login.cookies,
    )
    assert owner_resp.status_code == 200

    # 4. Stranger cannot grant access to someone else's video (403 Forbidden)
    bad_grant = await client.post(
        f"/api/v1/videos/{video_id}/access",
        json={"username_or_email": stranger.username},
        cookies=stranger_login.cookies,
    )
    assert bad_grant.status_code == 403

    # 5. Owner grants access to friend
    grant_resp = await client.post(
        f"/api/v1/videos/{video_id}/access",
        json={"username_or_email": friend.username},
        cookies=owner_login.cookies,
    )
    assert grant_resp.status_code == 201

    # 6. Friend can now view the private video (200 OK)
    friend_login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": friend.username, "password": "password"},
    )
    friend_resp = await client.get(
        f"/api/v1/videos/{video_id}",
        cookies=friend_login.cookies,
    )
    assert friend_resp.status_code == 200

    # 7. Owner revokes access from friend
    revoke_resp = await client.delete(
        f"/api/v1/videos/{video_id}/access/{friend.id}",
        cookies=owner_login.cookies,
    )
    assert revoke_resp.status_code == 204

    # 8. Friend loses access (403 Forbidden)
    friend_after_revoke = await client.get(
        f"/api/v1/videos/{video_id}",
        cookies=friend_login.cookies,
    )
    assert friend_after_revoke.status_code == 403
