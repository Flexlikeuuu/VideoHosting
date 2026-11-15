import asyncio
import json
import logging
import os
import shutil
import tempfile
import uuid

from arq.connections import RedisSettings
from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.storage import get_s3_client
from app.models.enums import VideoStatus
from app.models.video import Video

logger = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO)


async def get_video_duration(file_path: str) -> int:
    """Use ffprobe to extract duration in seconds."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe error: {stderr.decode()}")
    try:
        return int(float(stdout.decode().strip()))
    except Exception:
        return 0


async def transcode_to_faststart_mp4(input_path: str, output_path: str) -> None:
    """Transcode video to H.264 / AAC MP4 with faststart flag for instant web streaming."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg transcode error: {stderr.decode()[:500]}")


async def generate_thumbnail(input_path: str, output_path: str, at_second: int = 2) -> None:
    """Extract frame at at_second (or 00:00:01) as JPEG thumbnail."""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"00:00:{at_second:02d}",
        "-i",
        input_path,
        "-vframes",
        "1",
        "-q:v",
        "2",
        output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        # Fallback to second 0
        cmd[2] = "00:00:00"
        proc2 = await asyncio.create_subprocess_exec(*cmd)
        await proc2.communicate()


async def process_video(ctx: dict, video_id_str: str) -> str:
    """Background task: download raw video, transcode to H.264/AAC, generate thumb, upload."""
    video_id = uuid.UUID(video_id_str)
    logger.info(f"Starting processing for video {video_id}")

    tmp_dir = tempfile.mkdtemp(prefix=f"video_{video_id}_")
    try:
        async with async_session_factory() as session:
            video = await session.get(Video, video_id)
            if not video or not video.raw_object_key:
                logger.error(f"Video {video_id} not found or no raw_key")
                return f"Video {video_id} not found"

            raw_key = video.raw_object_key
            custom_thumb_key = video.thumbnail_object_key

        local_raw = os.path.join(tmp_dir, "raw_video.bin")
        local_processed = os.path.join(tmp_dir, "processed.mp4")
        local_thumb = os.path.join(tmp_dir, "thumb.jpg")

        # 1. Download raw file from S3
        async with get_s3_client() as s3:
            raw_obj = await s3.get_object(
                Bucket=settings.MINIO_VIDEOS_BUCKET, Key=raw_key
            )
            with open(local_raw, "wb") as f:
                async for chunk in raw_obj["Body"].iter_chunks():
                    f.write(chunk)

        # 2. Extract metadata
        duration = await get_video_duration(local_raw)

        # 3. Transcode to faststart mp4
        await transcode_to_faststart_mp4(local_raw, local_processed)

        # 4. Generate thumbnail if not provided
        thumbnail_key = custom_thumb_key
        if not thumbnail_key:
            thumb_sec = min(2, max(0, duration - 1))
            await generate_thumbnail(local_raw, local_thumb, at_second=thumb_sec)
            if os.path.exists(local_thumb) and os.path.getsize(local_thumb) > 0:
                thumbnail_key = f"thumbnails/{video_id}.jpg"
                async with get_s3_client() as s3:
                    with open(local_thumb, "rb") as f:
                        await s3.put_object(
                            Bucket=settings.MINIO_THUMBNAILS_BUCKET,
                            Key=thumbnail_key,
                            Body=f.read(),
                            ContentType="image/jpeg",
                        )

        # 5. Upload processed mp4 to S3
        processed_key = f"processed/{video_id}.mp4"
        async with get_s3_client() as s3:
            with open(local_processed, "rb") as f:
                await s3.put_object(
                    Bucket=settings.MINIO_VIDEOS_BUCKET,
                    Key=processed_key,
                    Body=f.read(),
                    ContentType="video/mp4",
                )

        # 6. Update database record to 'ready'
        async with async_session_factory() as session:
            await session.execute(
                update(Video)
                .where(Video.id == video_id)
                .values(
                    status=VideoStatus.READY,
                    duration_seconds=duration,
                    processed_object_key=processed_key,
                    thumbnail_object_key=thumbnail_key,
                    error_message=None,
                )
            )
            await session.commit()

        logger.info(f"Video {video_id} processed successfully to ready status")
        return f"Video {video_id} ready"

    except Exception as exc:
        logger.exception(f"Error processing video {video_id}: {exc}")
        async with async_session_factory() as session:
            await session.execute(
                update(Video)
                .where(Video.id == video_id)
                .values(
                    status=VideoStatus.FAILED,
                    error_message=str(exc)[:500],
                )
            )
            await session.commit()
        return f"Video {video_id} failed: {exc}"
    finally:
        # Guaranteed cleanup of local temp files
        shutil.rmtree(tmp_dir, ignore_errors=True)


class WorkerSettings:
    """Arq worker configuration for background video processing."""

    functions = [process_video]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 4
    job_timeout = 1800
