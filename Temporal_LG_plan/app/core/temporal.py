"""
Temporal client setup and helpers.
"""

from __future__ import annotations

from temporalio.client import Client

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level client cache
_client: Client | None = None


async def get_temporal_client() -> Client:
    """
    Get or create a Temporal client (singleton per process).

    Reads connection details from settings (TEMPORAL_HOST, TEMPORAL_PORT, TEMPORAL_NAMESPACE).
    """
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    logger.info(
        "Connecting to Temporal",
        server_url=settings.temporal.server_url,
        namespace=settings.temporal.namespace,
    )

    _client = await Client.connect(
        target_host=settings.temporal.server_url,
        namespace=settings.temporal.namespace,
    )

    logger.info("Temporal client connected")
    return _client


async def close_temporal_client() -> None:
    """Close the Temporal client connection."""
    global _client
    if _client is not None:
        # Temporal Python SDK doesn't have an explicit close,
        # but we clear the reference for clean shutdown.
        _client = None
        logger.info("Temporal client reference cleared")
