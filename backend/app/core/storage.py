import aioboto3
from botocore.config import Config

from app.core.config import settings

_s3_session = aioboto3.Session()


def get_s3_client():
    """Return an async S3 client context manager configured for MinIO."""
    return _s3_session.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
        region_name=settings.MINIO_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


async def check_storage_connection() -> tuple[bool, str | None]:
    """Verify MinIO connectivity and presence of required buckets."""
    try:
        async with get_s3_client() as client:
            for bucket in (settings.MINIO_VIDEOS_BUCKET, settings.MINIO_THUMBNAILS_BUCKET):
                await client.head_bucket(Bucket=bucket)
        return True, None
    except Exception as exc:
        return False, str(exc)
