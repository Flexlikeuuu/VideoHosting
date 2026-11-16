#!/usr/bin/env python3
"""
Seed script for YouTube Clone MVP.
Populates PostgreSQL and MinIO with test users, videos (generated via FFmpeg),
thumbnails, comments, reactions, subscriptions, playlists, access grants, and moderation reports.

Idempotent: safe to run multiple times without duplicating data or failing.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure root backend dir is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.core.storage import get_s3_client
from app.models.community import Comment, Report, Subscription, VideoReaction
from app.models.enums import ReportStatus, UserRole, VideoStatus, VideoVisibility
from app.models.playlist import Playlist, PlaylistItem
from app.models.user import User
from app.models.video import Video, VideoAccess

DEFAULT_PASSWORD = "Password123!"

SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "role": UserRole.ADMIN,
        "channel_name": "Admin Channel",
        "channel_description": "Официальный канал администратора платформы YouTube Clone",
    },
    {
        "username": "moderator",
        "email": "moderator@example.com",
        "role": UserRole.MODERATOR,
        "channel_name": "Moderator Channel",
        "channel_description": "Служба модерации контента и рассмотрения жалоб",
    },
    {
        "username": "creator",
        "email": "creator@example.com",
        "role": UserRole.USER,
        "channel_name": "Tech Creator",
        "channel_description": "Канал о веб-разработке, микросервисах, Docker и архитектуре",
    },
    {
        "username": "viewer",
        "email": "viewer@example.com",
        "role": UserRole.USER,
        "channel_name": "Casual Viewer",
        "channel_description": "Любитель качественного видеоконтента и технологий",
    },
]

SEED_VIDEOS = [
    {
        "title": "Tech Review: Cloud Architecture 2026",
        "description": "Обзор современных архитектурных паттернов для highload видеохостингов: S3, Nginx Range-стриминг и асинхронные воркеры.",
        "color": "navy",
        "duration": 4,
        "visibility": VideoVisibility.PUBLIC,
        "views_count": 1420,
        "likes_count": 56,
        "dislikes_count": 1,
    },
    {
        "title": "Coding Live: Video Streaming with FastAPI & Nginx",
        "description": "Пошаговое написание сервиса стриминга видео на FastAPI с раздачей через X-Accel-Redirect и поддержкой HTTP 206 Partial Content.",
        "color": "darkgreen",
        "duration": 5,
        "visibility": VideoVisibility.PUBLIC,
        "views_count": 3890,
        "likes_count": 210,
        "dislikes_count": 4,
    },
    {
        "title": "DevOps & Docker Compose: Production Ubuntu Deployment",
        "description": "Развертывание полного стека (PostgreSQL 16, Redis 7, MinIO, Nginx, Celery/Arq) на чистом сервере Ubuntu одной командой.",
        "color": "indigo",
        "duration": 3,
        "visibility": VideoVisibility.PUBLIC,
        "views_count": 940,
        "likes_count": 78,
        "dislikes_count": 0,
    },
    {
        "title": "Game Highlights & Speedrun World Records",
        "description": "Самые захватывающие моменты прохождений игр на максимальной скорости и секретные техники управления.",
        "color": "maroon",
        "duration": 4,
        "visibility": VideoVisibility.PUBLIC,
        "views_count": 6200,
        "likes_count": 412,
        "dislikes_count": 15,
    },
    {
        "title": "Private Vlog: Creator Backstage & Unreleased Footage",
        "description": "Эксклюзивные закулисные материалы и черновики. Видео доступно только по закрытому списку доступа (для зрителя viewer).",
        "color": "teal",
        "duration": 3,
        "visibility": VideoVisibility.PRIVATE,
        "views_count": 18,
        "likes_count": 3,
        "dislikes_count": 0,
    },
    {
        "title": "Controversial Video: Questionable Content",
        "description": "Видеоролик с провокационным содержанием для демонстрации функционала жалоб и панели модератора.",
        "color": "darkred",
        "duration": 3,
        "visibility": VideoVisibility.PUBLIC,
        "views_count": 310,
        "likes_count": 8,
        "dislikes_count": 34,
    },
]


def generate_media_files(color: str, duration: int) -> tuple[bytes, bytes]:
    """Generate a valid MP4 video and a JPEG thumbnail using FFmpeg."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "out.mp4")
        thumb_path = os.path.join(tmpdir, "thumb.jpg")

        # Generate video with test color and audio sine wave
        cmd_video = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=1280x720:d={duration}:r=30",
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
            "-b:a",
            "128k",
            "-shortest",
            video_path,
        ]
        subprocess.run(
            cmd_video, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )

        # Generate thumbnail at 1s
        cmd_thumb = [
            "ffmpeg",
            "-y",
            "-ss",
            "00:00:01",
            "-i",
            video_path,
            "-vframes",
            "1",
            "-q:v",
            "2",
            thumb_path,
        ]
        subprocess.run(
            cmd_thumb, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )

        with open(video_path, "rb") as vf:
            video_bytes = vf.read()
        with open(thumb_path, "rb") as tf:
            thumb_bytes = tf.read()

        return video_bytes, thumb_bytes


async def seed_users(session: AsyncSession) -> dict[str, User]:
    """Ensure all seed users exist with known passwords and roles."""
    users_by_username = {}
    password_hash = hash_password(DEFAULT_PASSWORD)

    for u_data in SEED_USERS:
        result = await session.execute(
            select(User).where(User.username == u_data["username"])
        )
        user = result.scalars().first()
        if not user:
            user = User(
                username=u_data["username"],
                email=u_data["email"],
                password_hash=password_hash,
                role=u_data["role"],
                channel_name=u_data["channel_name"],
                channel_description=u_data["channel_description"],
            )
            session.add(user)
            await session.flush()
            print(f"  [+] Created user: {user.username} (role={user.role})")
        else:
            # Ensure email, role and channel name are set
            user.email = u_data["email"]
            user.role = u_data["role"]
            user.channel_name = u_data["channel_name"]
            user.channel_description = u_data["channel_description"]
            user.password_hash = password_hash
            await session.flush()
            print(f"  [=] Updated user: {user.username} (role={user.role})")
        users_by_username[user.username] = user

    await session.commit()
    return users_by_username


async def seed_subscriptions(
    session: AsyncSession, users: dict[str, User]
) -> None:
    """Ensure viewer is subscribed to creator."""
    viewer = users["viewer"]
    creator = users["creator"]

    result = await session.execute(
        select(Subscription).where(
            Subscription.subscriber_id == viewer.id,
            Subscription.channel_id == creator.id,
        )
    )
    if not result.scalars().first():
        sub = Subscription(subscriber_id=viewer.id, channel_id=creator.id)
        session.add(sub)
        await session.commit()
        print(f"  [+] Subscribed {viewer.username} to {creator.username}")
    else:
        print(f"  [=] Subscription {viewer.username} -> {creator.username} exists")


async def seed_videos_and_media(
    session: AsyncSession, users: dict[str, User]
) -> list[Video]:
    """Generate videos and upload to S3."""
    creator = users["creator"]
    seeded_videos = []

    async with get_s3_client() as s3:
        for v_meta in SEED_VIDEOS:
            res = await session.execute(
                select(Video).where(
                    Video.owner_id == creator.id,
                    Video.title == v_meta["title"],
                )
            )
            video = res.scalars().first()

            if not video:
                print(f"  [*] Generating media for '{v_meta['title']}'...")
                video_bytes, thumb_bytes = generate_media_files(
                    v_meta["color"], v_meta["duration"]
                )
                vid_id = uuid.uuid4()
                raw_key = f"raw/{vid_id}.mp4"
                proc_key = f"processed/{vid_id}.mp4"
                thumb_key = f"thumbnails/{vid_id}.jpg"

                # Upload to S3
                await s3.put_object(
                    Bucket=settings.MINIO_VIDEOS_BUCKET,
                    Key=raw_key,
                    Body=video_bytes,
                    ContentType="video/mp4",
                )
                await s3.put_object(
                    Bucket=settings.MINIO_VIDEOS_BUCKET,
                    Key=proc_key,
                    Body=video_bytes,
                    ContentType="video/mp4",
                )
                await s3.put_object(
                    Bucket=settings.MINIO_THUMBNAILS_BUCKET,
                    Key=thumb_key,
                    Body=thumb_bytes,
                    ContentType="image/jpeg",
                )

                video = Video(
                    id=vid_id,
                    owner_id=creator.id,
                    title=v_meta["title"],
                    description=v_meta["description"],
                    status=VideoStatus.READY,
                    visibility=v_meta["visibility"],
                    duration_seconds=v_meta["duration"],
                    views_count=v_meta["views_count"],
                    likes_count=v_meta["likes_count"],
                    dislikes_count=v_meta["dislikes_count"],
                    raw_object_key=raw_key,
                    processed_object_key=proc_key,
                    thumbnail_object_key=thumb_key,
                )
                session.add(video)
                await session.flush()
                print(f"  [+] Created video: '{video.title}' (ID: {video.id})")
            else:
                print(f"  [=] Video '{video.title}' already exists (ID: {video.id})")

            seeded_videos.append(video)

    await session.commit()
    return seeded_videos


async def seed_private_access(
    session: AsyncSession, videos: list[Video], users: dict[str, User]
) -> None:
    """Grant viewer access to the private video."""
    private_video = next((v for v in videos if v.visibility == VideoVisibility.PRIVATE), None)
    if not private_video:
        return

    viewer = users["viewer"]
    creator = users["creator"]

    res = await session.execute(
        select(VideoAccess).where(
            VideoAccess.video_id == private_video.id,
            VideoAccess.user_id == viewer.id,
        )
    )
    if not res.scalars().first():
        grant = VideoAccess(
            video_id=private_video.id,
            user_id=viewer.id,
            granted_by=creator.id,
        )
        session.add(grant)
        await session.commit()
        print(f"  [+] Granted access for '{viewer.username}' to private video '{private_video.title}'")
    else:
        print(f"  [=] Access grant for '{viewer.username}' already exists")


async def seed_social_interactions(
    session: AsyncSession, videos: list[Video], users: dict[str, User]
) -> None:
    """Add comments and reactions."""
    viewer = users["viewer"]
    admin = users["admin"]

    comments_data = [
        (videos[0].id, viewer.id, "Отличный обзор архитектуры! Все разложено по полочкам."),
        (videos[1].id, viewer.id, "Стриминг через Nginx X-Accel-Redirect работает молниеносно!"),
        (videos[2].id, admin.id, "Запуск в Docker Compose проверен. Отличная работа!"),
        (videos[0].id, admin.id, "Отличное качество H.264 и быстрая загрузка превью."),
    ]

    for vid_id, author_id, content in comments_data:
        res = await session.execute(
            select(Comment).where(
                Comment.video_id == vid_id,
                Comment.author_id == author_id,
                Comment.content == content,
            )
        )
        if not res.scalars().first():
            comment = Comment(
                video_id=vid_id,
                author_id=author_id,
                content=content,
            )
            session.add(comment)
            print(f"  [+] Added comment to video {vid_id}: '{content[:30]}...'")

    # Reactions
    reactions_data = [
        (videos[0].id, viewer.id, 1),
        (videos[1].id, viewer.id, 1),
        (videos[2].id, viewer.id, 1),
        (videos[5].id, viewer.id, -1),
    ]

    for vid_id, u_id, val in reactions_data:
        res = await session.execute(
            select(VideoReaction).where(
                VideoReaction.video_id == vid_id,
                VideoReaction.user_id == u_id,
            )
        )
        if not res.scalars().first():
            reaction = VideoReaction(
                video_id=vid_id,
                user_id=u_id,
                value=val,
            )
            session.add(reaction)
            print(f"  [+] Added reaction (val={val}) from user {u_id} to video {vid_id}")

    await session.commit()


async def seed_playlist(
    session: AsyncSession, videos: list[Video], users: dict[str, User]
) -> None:
    """Create a demo playlist with multiple videos."""
    creator = users["creator"]
    playlist_title = "Курс: Fullstack & DevOps с нуля"

    res = await session.execute(
        select(Playlist).where(
            Playlist.owner_id == creator.id,
            Playlist.title == playlist_title,
        )
    )
    playlist = res.scalars().first()

    if not playlist:
        playlist = Playlist(
            owner_id=creator.id,
            title=playlist_title,
            description="Подборка обучающих видеоматериалов по архитектуре, стримингу и деплою.",
            is_public=True,
        )
        session.add(playlist)
        await session.flush()

        for idx, vid in enumerate(videos[:3]):
            item = PlaylistItem(
                playlist_id=playlist.id,
                video_id=vid.id,
                position=idx,
            )
            session.add(item)

        await session.commit()
        print(f"  [+] Created playlist '{playlist_title}' with 3 items")
    else:
        print(f"  [=] Playlist '{playlist_title}' already exists")


async def seed_reports(
    session: AsyncSession, videos: list[Video], users: dict[str, User]
) -> None:
    """Create active pending reports for moderator panel review."""
    controversial_video = next((v for v in videos if "Controversial" in v.title), videos[-1])
    viewer = users["viewer"]
    admin = users["admin"]

    reports_data = [
        (controversial_video.id, viewer.id, "Спам, кликбейт и вводящее в заблуждение описание видео."),
        (controversial_video.id, admin.id, "Подозрительное содержание, требуется экспертная проверка модератором."),
    ]

    for vid_id, reporter_id, reason in reports_data:
        res = await session.execute(
            select(Report).where(
                Report.video_id == vid_id,
                Report.reporter_id == reporter_id,
                Report.reason == reason,
            )
        )
        if not res.scalars().first():
            rep = Report(
                video_id=vid_id,
                reporter_id=reporter_id,
                reason=reason,
                status=ReportStatus.PENDING,
            )
            session.add(rep)
            print(f"  [+] Created pending report for video {vid_id} from reporter {reporter_id}")

    await session.commit()


async def main() -> None:
    print("==================================================")
    print("🚀 Starting YouTube Clone Database & S3 Seeding...")
    print("==================================================")

    async with async_session_factory() as session:
        print("\n[Step 1/6] Seeding Users...")
        users = await seed_users(session)

        print("\n[Step 2/6] Seeding Subscriptions...")
        await seed_subscriptions(session, users)

        print("\n[Step 3/6] Seeding Videos & Media (FFmpeg + S3)...")
        videos = await seed_videos_and_media(session, users)

        print("\n[Step 4/6] Seeding Private Access Grants...")
        await seed_private_access(session, videos, users)

        print("\n[Step 5/6] Seeding Social Interactions (Comments & Reactions)...")
        await seed_social_interactions(session, videos, users)

        print("\n[Step 6/6] Seeding Playlist & Moderation Reports...")
        await seed_playlist(session, videos, users)
        await seed_reports(session, videos, users)

    print("\n==================================================")
    print("✅ Seeding completed successfully!")
    print(f"🔑 Test credentials: password is '{DEFAULT_PASSWORD}' for all accounts:")
    print("   - admin@youtube.local / admin (Role: ADMIN)")
    print("   - moderator@youtube.local / moderator (Role: MODERATOR)")
    print("   - creator@youtube.local / creator (Role: USER / Content Author)")
    print("   - viewer@youtube.local / viewer (Role: USER / Regular Viewer)")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
