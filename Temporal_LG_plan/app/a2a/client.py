"""
A2A Client for outbound calls to external A2A-compliant agents.

Uses httpx for HTTP calls with JSON-RPC 2.0 protocol.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class A2AClient:
    """
    Client for calling external A2A agents via JSON-RPC 2.0.

    Methods:
        discover(base_url) — fetch Agent Card
        send_task(agent_url, message, context_id) — tasks/send
        get_task(agent_url, task_id) — tasks/get
        cancel_task(agent_url, task_id) — tasks/cancel
    """

    def __init__(
        self,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        settings = get_settings()
        self._timeout = timeout or settings.a2a.client_timeout
        self._max_retries = max_retries or settings.a2a.client_max_retries

    def _build_jsonrpc(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a JSON-RPC 2.0 request payload."""
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(uuid4()),
        }

    async def discover(self, base_url: str) -> dict[str, Any]:
        """
        Fetch an agent's Agent Card from /.well-known/agent.json.

        Args:
            base_url: Base URL of the agent (e.g., "http://agent.example.com")

        Returns:
            Agent Card dictionary.
        """
        url = f"{base_url.rstrip('/')}/.well-known/agent.json"
        logger.info("Discovering agent", url=url)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            card = response.json()

        logger.info(
            "Agent discovered",
            name=card.get("name"),
            skills=len(card.get("skills", [])),
        )
        return card

    async def send_task(
        self,
        agent_url: str,
        message: str,
        context_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a task to an external agent via tasks/send.

        Args:
            agent_url: A2A endpoint URL (e.g., "http://agent.example.com/a2a")
            message: Text message to send
            context_id: Optional context ID for multi-turn conversations

        Returns:
            Task object from the agent's response.
        """
        params: dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
            },
        }
        if context_id:
            params["contextId"] = context_id

        payload = self._build_jsonrpc("tasks/send", params)

        logger.info(
            "Sending A2A task",
            agent_url=agent_url,
            message_preview=message[:80],
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(agent_url, json=payload)
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            logger.error("A2A task error", error=result["error"])
            raise A2AClientError(result["error"])

        task = result.get("result", {})
        logger.info(
            "A2A task response",
            task_id=task.get("id"),
            status=task.get("status"),
        )
        return task

    async def get_task(
        self, agent_url: str, task_id: str
    ) -> dict[str, Any]:
        """
        Get the status of a task via tasks/get.

        Args:
            agent_url: A2A endpoint URL
            task_id: ID of the task to check

        Returns:
            Task object with current status.
        """
        payload = self._build_jsonrpc(
            "tasks/get", {"taskId": task_id}
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(agent_url, json=payload)
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            raise A2AClientError(result["error"])

        return result.get("result", {})

    async def cancel_task(
        self, agent_url: str, task_id: str
    ) -> dict[str, Any]:
        """
        Cancel a running task via tasks/cancel.

        Args:
            agent_url: A2A endpoint URL
            task_id: ID of the task to cancel

        Returns:
            Updated task object.
        """
        payload = self._build_jsonrpc(
            "tasks/cancel", {"taskId": task_id}
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(agent_url, json=payload)
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            raise A2AClientError(result["error"])

        return result.get("result", {})


class A2AClientError(Exception):
    """Raised when an A2A JSON-RPC call returns an error."""

    def __init__(self, error: dict[str, Any]):
        self.code = error.get("code", -1)
        self.message = error.get("message", "Unknown A2A error")
        self.data = error.get("data")
        super().__init__(f"A2A Error [{self.code}]: {self.message}")
