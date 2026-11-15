import uuid
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.core.queue import enqueue_video_processing
from app.core.storage import get_s3_client
from app.core.validators import is_valid_image_header, is_valid_video_header
from app.models.enums import VideoStatus, VideoVisibility
from app.models.user import User
from app.models.video import Video
from app.repositories.video import VideoRepository
from app.schemas.video import VideoBaseResponse


class MediaService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.video_repo = VideoRepository(session)

    async def upload_video(
        self,
        owner: User,
        title: str,
        description: str | None,
        visibility: VideoVisibility,
        video_file: UploadFile,
        thumbnail_file: UploadFile | None = None,
    ) -> VideoBaseResponse:
        """
        Validate magic bytes and stream file directly to MinIO without loading into RAM.
        """
        # 1. Read first chunk to validate magic bytes
        first_chunk = await video_file.read(1024)
        if not is_valid_video_header(first_chunk):
            raise BadRequestException(
                "Недопустимый формат файла. Разрешены только видео (MP4, WebM, MKV, MOV)"
            )

        video_id = uuid.uuid4()
        raw_key = f"raw/{video_id}.bin"
        thumbnail_key = None

        # 2. If thumbnail provided, validate and upload it
        if thumbnail_file and thumbnail_file.filename:
            thumb_header = await thumbnail_file.read(1024)
            if not is_valid_image_header(thumb_header):
                raise BadRequestException(
                    "Недопустимый формат превью. Разрешены только JPEG, PNG, WebP"
                )
            thumbnail_key = f"thumbnails/{video_id}_custom.jpg"

            async with get_s3_client() as s3:
                # Stream custom thumbnail
                async def thumb_stream():
                    yield thumb_header
                    while chunk := await thumbnail_file.read(64 * 1024):
                        yield chunk

                # Upload thumbnail
                # Since thumbnail is small, read into bytes or multipart
                thumb_body = thumb_header + await thumbnail_file.read()
                await s3.put_object(
                    Bucket=settings.MINIO_THUMBNAILS_BUCKET,
                    Key=thumbnail_key,
                    Body=thumb_body,
                    ContentType=thumbnail_file.content_type or "image/jpeg",
                )

        # 3. Stream raw video to MinIO using multipart upload
        max_bytes = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
        total_size = len(first_chunk)

        async with get_s3_client() as s3:
            mpu = await s3.create_multipart_upload(
                Bucket=settings.MINIO_VIDEOS_BUCKET,
                Key=raw_key,
                ContentType=video_file.content_type or "video/mp4",
            )
            upload_id = mpu["UploadId"]
            parts = []
            part_number = 1

            current_part_data = bytearray(first_chunk)
            min_part_size = 5 * 1024 * 1024  # S3 5MB minimum per part

            try:
                while chunk := await video_file.read(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > max_bytes:
                        raise BadRequestException(
                            f"Размер файла превышает лимит {settings.MAX_VIDEO_SIZE_MB} МБ"
                        )
                    current_part_data.extend(chunk)

                    if len(current_part_data) >= min_part_size:
                        part_res = await s3.upload_part(
                            Bucket=settings.MINIO_VIDEOS_BUCKET,
                            Key=raw_key,
                            PartNumber=part_number,
                            UploadId=upload_id,
                            Body=bytes(current_part_data),
                        )
                        parts.append({"PartNumber": part_number, "ETag": part_res["ETag"]})
                        part_number += 1
                        current_part_data.clear()

                # Upload remaining part
                if current_part_data:
                    part_res = await s3.upload_part(
                        Bucket=settings.MINIO_VIDEOS_BUCKET,
                        Key=raw_key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=bytes(current_part_data),
                    )
                    parts.append({"PartNumber": part_number, "ETag": part_res["ETag"]})

                await s3.complete_multipart_upload(
                    Bucket=settings.MINIO_VIDEOS_BUCKET,
                    Key=raw_key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
            except Exception:
                await s3.abort_multipart_upload(
                    Bucket=settings.MINIO_VIDEOS_BUCKET,
                    Key=raw_key,
                    UploadId=upload_id,
                )
                raise

        # 4. Save video record in database with status 'processing'
        video = Video(
            id=video_id,
            owner_id=owner.id,
            title=title,
            description=description,
            status=VideoStatus.PROCESSING,
            visibility=visibility,
            raw_object_key=raw_key,
            thumbnail_object_key=thumbnail_key,
        )
        await self.video_repo.create(video)
        await self.session.commit()
        await self.session.refresh(video)

        # 5. Enqueue processing task
        await enqueue_video_processing(str(video_id))

        return VideoBaseResponse.model_validate(video)
