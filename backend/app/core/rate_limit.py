from redis.asyncio import Redis

from app.core.redis import get_redis_client


class RateLimiter:
    """Fixed-window rate limiter powered by Redis."""

    def __init__(self, key_prefix: str, max_requests: int, window_seconds: int):
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """Check if request is allowed. Returns (is_allowed, remaining_requests)."""
        redis: Redis = get_redis_client()
        key = f"rate_limit:{self.key_prefix}:{identifier}"
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, self.window_seconds)

        if current > self.max_requests:
            return False, 0
        return True, max(0, self.max_requests - current)


# 5 failed or total attempts per minute per IP/username for auth endpoints
auth_rate_limiter = RateLimiter(key_prefix="auth", max_requests=10, window_seconds=60)
# 10 video uploads per hour per user
upload_rate_limiter = RateLimiter(key_prefix="upload", max_requests=10, window_seconds=3600)
