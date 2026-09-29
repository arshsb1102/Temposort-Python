from __future__ import annotations

import json
from uuid import uuid4
from typing import Any

import redis

from app.core.environment import settings


class RedisService:
    def __init__(self, url: str | None = None) -> None:
        self.url = url or settings.redis_url
        self.client = redis.Redis.from_url(
            self.url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except redis.RedisError:
            return False

    async def ping_async(self) -> bool:
        return self.ping()

    def acquire_lock(self, key: str, ttl_seconds: int = 300) -> str | None:
        token = uuid4().hex
        if self.client.set(key, token, nx=True, ex=ttl_seconds):
            return token
        return None

    def release_lock(self, key: str, token: str) -> bool:
        result = self.client.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
            1,
            key,
            token,
        )
        return bool(result)

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

    def queue_length(self, queue: str = "default") -> int:
        return int(self.client.llen(queue))

    async def close(self) -> None:
        self.client.close()


redis_service = RedisService()
cache_service = redis_service

__all__ = ["redis_service", "cache_service", "RedisService"]
