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
async def test_social_features_and_moderation_flow(client: AsyncClient):
    suffix = uuid.uuid4().hex[:6]

    # 1. Create users: author, viewer, moderator
    async with async_session_factory() as session:
        author = User(
            email=f"author_{suffix}@example.com",
            username=f"author_{suffix}",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            channel_name=f"Channel {suffix}",
            channel_description="Awesome videos",
        )
        viewer = User(
            email=f"viewer_{suffix}@example.com",
            username=f"viewer_{suffix}",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            channel_name=f"Viewer {suffix}",
        )
        moderator = User(
            email=f"mod_{suffix}@example.com",
            username=f"mod_{suffix}",
            password_hash=hash_password("password"),
            role=UserRole.MODERATOR,
            channel_name=f"Moderator {suffix}",
        )
        session.add_all([author, viewer, moderator])
        await session.commit()
        await session.refresh(author)
        await session.refresh(viewer)
        await session.refresh(moderator)

        # Create public ready video
        video = Video(
            owner_id=author.id,
            title="FastAPI & React Full Tutorial",
            description="Complete tutorial on building fullstack web applications",
            status=VideoStatus.READY,
            visibility=VideoVisibility.PUBLIC,
            is_hidden=False,
        )
        session.add(video)
        await session.commit()
        await session.refresh(video)
        video_id = video.id

    # Log in as viewer
    login_viewer = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": viewer.username, "password": "password"},
    )
    viewer_cookies = login_viewer.cookies

    # 2. Feed and Search
    feed_resp = await client.get("/api/v1/videos?sort=new")
    assert feed_resp.status_code == 200
    feed_ids = [v["id"] for v in feed_resp.json()]
    assert str(video_id) in feed_ids

    search_resp = await client.get("/api/v1/videos/search?q=Tutorial")
    assert search_resp.status_code == 200
    assert any(v["id"] == str(video_id) for v in search_resp.json())

    # 3. View recording with deduplication
    view1 = await client.post(f"/api/v1/videos/{video_id}/view", cookies=viewer_cookies)
    assert view1.status_code == 200
    cnt1 = view1.json()["views_count"]

    # Immediate second call within 60s window should be deduplicated
    view2 = await client.post(f"/api/v1/videos/{video_id}/view", cookies=viewer_cookies)
    assert view2.status_code == 200
    assert view2.json()["views_count"] == cnt1

    # 4. Reactions (like, change to dislike, remove)
    like_resp = await client.post(
        f"/api/v1/videos/{video_id}/react",
        json={"value": 1},
        cookies=viewer_cookies,
    )
    assert like_resp.status_code == 200
    assert like_resp.json()["likes_count"] >= 1
    assert like_resp.json()["user_reaction"] == 1

    dislike_resp = await client.post(
        f"/api/v1/videos/{video_id}/react",
        json={"value": -1},
        cookies=viewer_cookies,
    )
    assert dislike_resp.status_code == 200
    assert dislike_resp.json()["dislikes_count"] >= 1
    assert dislike_resp.json()["user_reaction"] == -1

    # 5. Comments
    comm_resp = await client.post(
        f"/api/v1/videos/{video_id}/comments",
        json={"content": "Great video!"},
        cookies=viewer_cookies,
    )
    assert comm_resp.status_code == 201
    comment_id = comm_resp.json()["id"]

    list_comm = await client.get(f"/api/v1/videos/{video_id}/comments")
    assert list_comm.status_code == 200
    assert any(c["id"] == comment_id for c in list_comm.json())

    # 6. Channel & Subscription
    chan_resp = await client.get(f"/api/v1/channels/{author.username}")
    assert chan_resp.status_code == 200
    assert chan_resp.json()["username"] == author.username

    sub_resp = await client.post(
        f"/api/v1/channels/{author.username}/subscribe",
        cookies=viewer_cookies,
    )
    assert sub_resp.status_code == 200
    assert sub_resp.json()["is_subscribed"] is True
    assert sub_resp.json()["subscribers_count"] == 1

    # Unsubscribe
    unsub_resp = await client.post(
        f"/api/v1/channels/{author.username}/subscribe",
        cookies=viewer_cookies,
    )
    assert unsub_resp.status_code == 200
    assert unsub_resp.json()["is_subscribed"] is False

    # 7. Playlist CRUD
    pl_resp = await client.post(
        "/api/v1/playlists",
        json={"title": "Favorites", "description": "My favorite videos", "is_public": True},
        cookies=viewer_cookies,
    )
    assert pl_resp.status_code == 201
    playlist_id = pl_resp.json()["id"]

    add_pl_video = await client.post(
        f"/api/v1/playlists/{playlist_id}/videos",
        json={"video_id": str(video_id)},
        cookies=viewer_cookies,
    )
    assert add_pl_video.status_code == 201
    assert len(add_pl_video.json()["items"]) == 1

    # 8. Report and Moderation flow
    rep_resp = await client.post(
        f"/api/v1/videos/{video_id}/report",
        json={"reason": "Inappropriate content"},
        cookies=viewer_cookies,
    )
    assert rep_resp.status_code == 201
    report_id = rep_resp.json()["id"]

    # Log in as moderator
    login_mod = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": moderator.username, "password": "password"},
    )
    mod_cookies = login_mod.cookies

    # Moderator views queue
    reports_queue = await client.get("/api/v1/moderation/reports", cookies=mod_cookies)
    assert reports_queue.status_code == 200
    assert any(r["id"] == report_id for r in reports_queue.json())

    # Moderator hides video
    resolve_resp = await client.post(
        f"/api/v1/moderation/reports/{report_id}/resolve",
        json={"action": "hide", "comment": "Violation of community standards"},
        cookies=mod_cookies,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"

    # Hidden video disappears from public feed
    hidden_feed = await client.get("/api/v1/videos")
    assert not any(v["id"] == str(video_id) for v in hidden_feed.json())

    # Unhide video
    unhide_resp = await client.post(
        f"/api/v1/moderation/videos/{video_id}/unhide",
        cookies=mod_cookies,
    )
    assert unhide_resp.status_code == 204

    # Video is back in feed
    restored_feed = await client.get("/api/v1/videos")
    assert any(v["id"] == str(video_id) for v in restored_feed.json())
