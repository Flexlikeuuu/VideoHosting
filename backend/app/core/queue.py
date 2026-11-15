from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

_arq_pool = None


async def get_arq_pool():
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool


async def enqueue_video_processing(video_id: str) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job("process_video", video_id)
