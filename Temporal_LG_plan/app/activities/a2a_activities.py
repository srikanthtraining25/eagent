"""
A2A Activities — Temporal Activities for outbound A2A calls to external agents.
"""

from __future__ import annotations

import asyncio
from typing import Any

from temporalio import activity

from app.a2a.client import A2AClient
from app.core.logging import get_logger

logger = get_logger(__name__)


@activity.defn(name="send_a2a_task")
async def send_a2a_task(
    agent_url: str,
    message: str,
    context_id: str | None = None,
) -> dict[str, Any]:
    """
    Temporal Activity — sends a task to an external A2A agent.

    Args:
        agent_url: The external agent's A2A endpoint URL
        message: Message to send
        context_id: Optional context ID for multi-turn

    Returns:
        Task object from the external agent.
    """
    client = A2AClient()

    logger.info(
        "Sending A2A task to external agent",
        agent_url=agent_url,
        message_preview=message[:80],
    )

    task = await client.send_task(agent_url, message, context_id)
    return task


@activity.defn(name="get_a2a_task_status")
async def get_a2a_task_status(
    agent_url: str,
    task_id: str,
) -> dict[str, Any]:
    """
    Temporal Activity — polls an external A2A agent for task status.

    Args:
        agent_url: The external agent's A2A endpoint URL
        task_id: Task ID to check

    Returns:
        Task object with current status.
    """
    client = A2AClient()

    logger.info(
        "Getting A2A task status",
        agent_url=agent_url,
        task_id=task_id,
    )

    task = await client.get_task(agent_url, task_id)
    return task


@activity.defn(name="discover_agent")
async def discover_agent(agent_base_url: str) -> dict[str, Any]:
    """
    Temporal Activity — discovers an external agent's capabilities.

    Args:
        agent_base_url: Base URL of the agent

    Returns:
        Agent Card dictionary.
    """
    client = A2AClient()

    logger.info("Discovering external agent", url=agent_base_url)

    card = await client.discover(agent_base_url)
    return card
