import os
import subprocess
import tempfile
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.core.storage import get_s3_client
from app.main import app
from app.models.enums import UserRole, VideoStatus, VideoVisibility
from app.models.user import User
from app.models.video import Video
from app.worker import process_video


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limits():
    """Reset rate limiter keys between tests so automated tests don't trip limits."""
    from app.core.redis import get_redis_client
    redis = get_redis_client()
    try:
        keys = await redis.keys("rate_limit:*")
        if keys:
            await redis.delete(*keys)
    except Exception:
        pass
    finally:
        await redis.aclose()


def generate_tiny_test_mp4(filepath: str, duration: int = 1):
    """Generate a valid, tiny MP4 video file with ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=blue:s=320x240:d={duration}:r=25",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-shortest",
        filepath,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


@pytest.mark.asyncio
async def test_security_upload_validation_magic_bytes(client: AsyncClient):
    """
    Test security validation against malicious / fake video uploads:
    - Text files or shell scripts renamed to .mp4 must be rejected with 400 Bad Request.
    - Executables or garbage bytes must be rejected with 400 Bad Request.
    """
    suffix = uuid.uuid4().hex[:6]
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"hacker_{suffix}@example.com",
            "username": f"hacker_{suffix}",
            "password": "Password123!",
            "channel_name": "Security Channel",
        },
    )
    assert reg_resp.status_code == 201

    # 1. Attempt to upload a bash script disguised as video.mp4
    fake_script = b"#!/bin/bash\nrm -rf /\necho 'malicious script'"
    resp_script = await client.post(
        "/api/v1/videos/upload",
        data={"title": "Script attack", "visibility": "public"},
        files={"video": ("evil.mp4", fake_script, "video/mp4")},
    )
    assert resp_script.status_code == 400
    assert "Недопустимый формат файла" in resp_script.json().get("detail", "")

    # 2. Attempt to upload Windows executable disguised as video.mp4 (MZ header)
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    resp_exe = await client.post(
        "/api/v1/videos/upload",
        data={"title": "Exe attack", "visibility": "public"},
        files={"video": ("payload.mp4", fake_exe, "video/mp4")},
    )
    assert resp_exe.status_code == 400
    assert "Недопустимый формат файла" in resp_exe.json().get("detail", "")

    # 3. Attempt to upload arbitrary text/garbage
    fake_txt = b"Hello world, this is a plain text file pretending to be video!"
    resp_txt = await client.post(
        "/api/v1/videos/upload",
        data={"title": "Text attack", "visibility": "public"},
        files={"video": ("notes.mp4", fake_txt, "video/mp4")},
    )
    assert resp_txt.status_code == 400
    assert "Недопустимый формат файла" in resp_txt.json().get("detail", "")


@pytest.mark.asyncio
async def test_security_moderation_rbac_forbidden_for_regular_user(client: AsyncClient):
    """
    Test RBAC boundaries: regular user cannot access moderation queue,
    cannot resolve reports, and cannot unhide videos. Expects 403 Forbidden.
    """
    suffix = uuid.uuid4().hex[:6]
    # Register as normal user (role=user)
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"viewer_{suffix}@example.com",
            "username": f"viewer_{suffix}",
            "password": "Password123!",
            "channel_name": "Viewer Channel",
        },
    )
    assert reg_resp.status_code == 201

    random_id = str(uuid.uuid4())

    # 1. Attempt to view moderation reports queue
    rep_resp = await client.get("/api/v1/moderation/reports")
    assert rep_resp.status_code == 403
    assert "Недостаточно прав" in rep_resp.json().get("detail", "")

    # 2. Attempt to resolve report
    res_resp = await client.post(
        f"/api/v1/moderation/reports/{random_id}/resolve",
        json={"action": "hide", "comment": "Unauthorized action"},
    )
    assert res_resp.status_code == 403

    # 3. Attempt to unhide video
    unhide_resp = await client.post(f"/api/v1/moderation/videos/{random_id}/unhide")
    assert unhide_resp.status_code == 403


@pytest.mark.asyncio
async def test_security_private_video_access_control_and_revocation(client: AsyncClient):
    """
    Test IDOR and access controls on private videos:
    - User B cannot view or stream User A's private video.
    - User A can grant access to User B.
    - User B can now access the video.
    - User A revokes access -> User B is blocked again (403).
    """
    s_a = uuid.uuid4().hex[:6]
    s_b = uuid.uuid4().hex[:6]

    # User A (Owner)
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"own_{s_a}@example.com",
            "username": f"own_{s_a}",
            "password": "Password123!",
            "channel_name": "Owner Channel",
        },
    )
    cookies_a = dict(reg_a.cookies)

    # User B (Viewer)
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"view_{s_b}@example.com",
            "username": f"view_{s_b}",
            "password": "Password123!",
            "channel_name": "Viewer Channel",
        },
    )
    cookies_b = dict(reg_b.cookies)
    user_b_id = reg_b.json()["user"]["id"]

    # 1. User A creates private video in DB
    video_id = uuid.uuid4()
    async with async_session_factory() as session:
        vid = Video(
            id=video_id,
            owner_id=uuid.UUID(reg_a.json()["user"]["id"]),
            title="Super Confidential Strategy",
            description="Private company materials",
            status=VideoStatus.READY,
            visibility=VideoVisibility.PRIVATE,
            duration_seconds=12,
            processed_object_key=f"processed/{video_id}.mp4",
        )
        session.add(vid)
        await session.commit()

    # 2. User B tries to view -> 403 Forbidden
    client.cookies.clear()
    for k, v in cookies_b.items():
        client.cookies.set(k, v)
    view_resp = await client.get(f"/api/v1/videos/{video_id}")
    assert view_resp.status_code == 403

    # 3. User B tries to verify access for stream -> 403 Forbidden
    verify_resp = await client.get(f"/api/v1/videos/{video_id}/verify-access")
    assert verify_resp.status_code == 403

    # 4. User A grants access to User B
    client.cookies.clear()
    for k, v in cookies_a.items():
        client.cookies.set(k, v)
    grant_resp = await client.post(
        f"/api/v1/videos/{video_id}/access",
        json={"username_or_email": f"view_{s_b}"},
    )
    assert grant_resp.status_code == 201

    # 5. User B can now view
    client.cookies.clear()
    for k, v in cookies_b.items():
        client.cookies.set(k, v)
    view_ok = await client.get(f"/api/v1/videos/{video_id}")
    assert view_ok.status_code == 200
    assert view_ok.json()["title"] == "Super Confidential Strategy"

    # 6. User A revokes access
    client.cookies.clear()
    for k, v in cookies_a.items():
        client.cookies.set(k, v)
    revoke_resp = await client.delete(f"/api/v1/videos/{video_id}/access/{user_b_id}")
    assert revoke_resp.status_code == 204

    # 7. User B is blocked again
    client.cookies.clear()
    for k, v in cookies_b.items():
        client.cookies.set(k, v)
    view_blocked = await client.get(f"/api/v1/videos/{video_id}")
    assert view_blocked.status_code == 403


@pytest.mark.asyncio
async def test_e2e_primary_journey(client: AsyncClient):
    """
    Full End-to-End Test of Primary Happy Path:
    1. Register new user.
    2. Upload real MP4 video generated with FFmpeg.
    3. Run background transcode worker task -> status 'ready'.
    4. Access video stream endpoint (X-Accel-Redirect header with Presigned URL).
    5. Second user registers and likes the video -> verify likes count is 1.
    6. Second user adds a comment -> verify comments list.
    7. Register view -> verify views count.
    """
    suffix = uuid.uuid4().hex[:6]
    creator_name = f"e2e_creator_{suffix}"

    # 1. Register creator
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{creator_name}@example.com",
            "username": creator_name,
            "password": "Password123!",
            "channel_name": "E2E Channel",
        },
    )
    assert reg_resp.status_code == 201
    creator_cookies = dict(reg_resp.cookies)

    # 2. Generate and upload a real MP4 video
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        mp4_path = tf.name

    try:
        generate_tiny_test_mp4(mp4_path, duration=2)

        with open(mp4_path, "rb") as vf:
            upload_resp = await client.post(
                "/api/v1/videos/upload",
                data={
                    "title": "E2E Masterpiece",
                    "description": "Full end-to-end integration test video",
                    "visibility": "public",
                },
                files={"video": ("test_clip.mp4", vf, "video/mp4")},
            )
        assert upload_resp.status_code == 201
        video_data = upload_resp.json()
        video_id = video_data["id"]
        assert video_data["status"] in ("uploading", "processing")

        # 3. Process video via Arq worker function
        worker_ctx = {}
        await process_video(worker_ctx, str(video_id))

        # Verify status is now 'ready'
        status_resp = await client.get(f"/api/v1/videos/{video_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "ready"
        assert status_resp.json()["duration_seconds"] is not None
        assert status_resp.json()["thumbnail_object_key"] is not None

        # 4. Stream endpoint provides X-Accel-Redirect to Nginx for internal S3 streaming
        stream_resp = await client.get(f"/api/v1/videos/{video_id}/stream")
        assert stream_resp.status_code == 200
        assert "X-Accel-Redirect" in stream_resp.headers
        assert "Accept-Ranges" in stream_resp.headers
        assert stream_resp.headers["Accept-Ranges"] == "bytes"

        # 5. Second user registers and likes the video
        viewer_name = f"e2e_viewer_{suffix}"
        client.cookies.clear()
        reg_v = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{viewer_name}@example.com",
                "username": viewer_name,
                "password": "Password123!",
                "channel_name": "E2E Viewer",
            },
        )
        assert reg_v.status_code == 201

        react_resp = await client.post(
            f"/api/v1/videos/{video_id}/react",
            json={"value": 1},
        )
        assert react_resp.status_code == 200
        assert react_resp.json()["likes_count"] == 1
        assert react_resp.json()["user_reaction"] == 1

        # 6. Second user adds a comment
        comment_resp = await client.post(
            f"/api/v1/videos/{video_id}/comments",
            json={"content": "Incredible production quality! 10/10"},
        )
        assert comment_resp.status_code == 201
        assert comment_resp.json()["content"] == "Incredible production quality! 10/10"

        # 7. Register view (with Redis deduplication)
        view_resp = await client.post(f"/api/v1/videos/{video_id}/view")
        assert view_resp.status_code == 200

        # Verify final video state
        final_video_resp = await client.get(f"/api/v1/videos/{video_id}")
        final_video = final_video_resp.json()
        assert final_video["likes_count"] == 1
        assert final_video["views_count"] == 1

        # Verify comments list
        comments_list_resp = await client.get(f"/api/v1/videos/{video_id}/comments")
        comments_list = comments_list_resp.json()
        assert len(comments_list) == 1
        assert comments_list[0]["content"] == "Incredible production quality! 10/10"

    finally:
        if os.path.exists(mp4_path):
            os.remove(mp4_path)
