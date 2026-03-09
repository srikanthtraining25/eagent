"""
FastA2A Storage implementation backed by Redis.

Persists A2A task state and conversation context.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisStorage:
    """
    Redis-backed storage for FastA2A.

    Implements the fasta2a.Storage interface:
    - Task storage: save/load A2A tasks by task_id
    - Context storage: save/load conversation context by context_id
    """

    def __init__(self, redis_url: str | None = None):
        settings = get_settings()
        self._redis_url = redis_url or settings.redis.connection_url
        self._client: aioredis.Redis | None = None
        self._task_prefix = "a2a:task:"
        self._context_prefix = "a2a:context:"

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                self._redis_url, decode_responses=True
            )
        return self._client

    # ---- Task Storage ----

    async def save_task(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Save an A2A task by ID."""
        client = await self._get_client()
        key = f"{self._task_prefix}{task_id}"
        await client.set(key, json.dumps(task_data))
        logger.debug("Task saved", task_id=task_id)

    async def load_task(self, task_id: str) -> dict[str, Any] | None:
        """Load an A2A task by ID. Returns None if not found."""
        client = await self._get_client()
        key = f"{self._task_prefix}{task_id}"
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None

    async def update_task_status(
        self, task_id: str, status: str, artifacts: list[Any] | None = None
    ) -> None:
        """Update task status and optionally add artifacts."""
        task = await self.load_task(task_id)
        if task:
            task["status"] = status
            if artifacts:
                task["artifacts"] = artifacts
            await self.save_task(task_id, task)
            logger.debug("Task status updated", task_id=task_id, status=status)

    async def delete_task(self, task_id: str) -> None:
        """Delete a task by ID."""
        client = await self._get_client()
        key = f"{self._task_prefix}{task_id}"
        await client.delete(key)

    # ---- Context Storage ----

    async def save_context(
        self, context_id: str, context_data: dict[str, Any]
    ) -> None:
        """Save conversation context by context_id."""
        client = await self._get_client()
        key = f"{self._context_prefix}{context_id}"
        await client.set(key, json.dumps(context_data))
        logger.debug("Context saved", context_id=context_id)

    async def load_context(self, context_id: str) -> dict[str, Any] | None:
        """Load conversation context. Returns None if not found."""
        client = await self._get_client()
        key = f"{self._context_prefix}{context_id}"
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None

    # ---- Lifecycle ----

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
