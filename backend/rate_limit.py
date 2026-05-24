"""Rate limiting: in-memory by default; optional Redis when REDIS_URL is set."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, status

import config as app_config

logger = logging.getLogger(__name__)

_buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
_redis_client = None
_redis_checked = False


def _prune_buckets(now: float, window_seconds: int) -> None:
    window_start = now - window_seconds
    stale_keys = [key for key, hits in _buckets.items() if not hits or hits[-1] <= window_start]
    for key in stale_keys:
        _buckets.pop(key, None)


async def _redis_over_limit(redis_key: str, window_seconds: int, max_calls: int) -> bool:
    global _redis_client, _redis_checked
    if not _redis_checked:
        _redis_checked = True
        url = app_config.redis_url()
        if url:
            try:
                from redis.asyncio import Redis

                _redis_client = Redis.from_url(url, decode_responses=True)
                await _redis_client.ping()
                logger.info("Rate limiting using Redis")
            except Exception as exc:
                logger.warning("REDIS_URL set but Redis unavailable, using in-memory limits: %s", exc)
                _redis_client = None
    if _redis_client is None:
        return False

    count = await _redis_client.incr(redis_key)
    if count == 1:
        await _redis_client.expire(redis_key, window_seconds)
    return count > max_calls


def rate_limit(max_calls: int, window_seconds: int = 60):
    async def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        path = request.url.path
        key = (client, path)
        redis_key = f"rl:{client}:{path}"

        if await _redis_over_limit(redis_key, window_seconds, max_calls):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        now = time.monotonic()
        window_start = now - window_seconds
        hits = [t for t in _buckets[key] if t > window_start]
        if len(hits) >= max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
        hits.append(now)
        _buckets[key] = hits
        if len(_buckets) > 5000:
            _prune_buckets(now, window_seconds)

    return Depends(dependency)


auth_login_limit = rate_limit(20, 60)
submit_limit = rate_limit(30, 60)
form_read_limit = rate_limit(120, 60)
admin_read_limit = rate_limit(60, 60)
admin_write_limit = rate_limit(30, 60)
