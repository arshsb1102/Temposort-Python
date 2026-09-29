from __future__ import annotations

import json
from typing import Any

import redis

from app.core.environment import settings


class RedisService:
    def __init__(self, url: str | None = None) -> None:
        self.url = url or settings.redis_url
        self.client = redis.Redis.from_url(self.url, decode_responses=True, socket_connect_timeout=2)

    def ping(self) -> bool:
        return bool(self.client.ping())

    async def ping_async(self) -> bool:
        return self.ping()

    def get_json(self, key: str, default: Any = None) -> Any:
        value = self.client.get(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    def set_json(self, key: str, value: Any, ttl: int | None = None) -> bool:
        payload = json.dumps(value, default=str)
        if ttl is not None:
            return bool(self.client.set(key, payload, ex=ttl))
        return bool(self.client.set(key, payload))

    def delete(self, key: str) -> bool:
        return bool(self.client.delete(key))

    async def close(self) -> None:
        self.client.close()


redis_service = RedisService()
cache_service = redis_service

__all__ = ["redis_service", "cache_service", "RedisService"]
