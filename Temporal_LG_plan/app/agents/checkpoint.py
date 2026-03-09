"""
Redis checkpointer setup for LangGraph state persistence.
"""

from __future__ import annotations

from langgraph.checkpoint.redis import RedisSaver

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level checkpointer cache
_checkpointer: RedisSaver | None = None


def get_checkpointer() -> RedisSaver:
    """
    Get or create a Redis-backed LangGraph checkpointer (singleton).

    Uses REDIS_URL from settings.
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    settings = get_settings()
    redis_url = settings.redis.connection_url

    logger.info("Initializing Redis checkpointer", redis_url=redis_url)
    _checkpointer = RedisSaver.from_conn_string(redis_url)

    return _checkpointer
