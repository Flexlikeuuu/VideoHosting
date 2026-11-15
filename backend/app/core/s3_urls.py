import asyncio
from datetime import timedelta

from app.core.config import settings
from app.core.storage import get_s3_client


async def generate_internal_presigned_url(
    bucket: str, key: str, expires_in: int = 300
) -> str:
    """Generate a presigned S3 GET URL for Nginx internal reverse-proxy."""
    async with get_s3_client() as s3:
        url = await s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
