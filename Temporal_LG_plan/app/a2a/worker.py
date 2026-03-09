"""
FastA2A Worker that bridges A2A tasks to Temporal workflows.

This is the key adapter: FastA2A receives inbound A2A requests,
and this worker starts Temporal Orchestration Workflows for each task.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.temporal import get_temporal_client

logger = get_logger(__name__)


class TemporalA2AWorker:
    """
    FastA2A Worker that delegates task execution to Temporal.

    When FastA2A receives a tasks/send request, it calls this worker's
    run_task method, which starts a Temporal OrchestrationWorkflow.

    This bridges the A2A protocol to the Temporal orchestration layer.
    """

    def __init__(self):
        self._settings = get_settings()

    async def run_task(
        self,
        message: str,
        context_id: str | None = None,
        task_id: str | None = None,
    ) -> str:
        """
        Execute an A2A task by starting a Temporal workflow.

        Args:
            message: The user's message text
            context_id: A2A context ID for multi-turn conversations
            task_id: A2A task ID

        Returns:
            Result text from the completed workflow.
        """
        settings = self._settings
        client = await get_temporal_client()

        workflow_id = f"a2a-{task_id}" if task_id else f"a2a-{context_id}"

        logger.info(
            "Starting Temporal workflow for A2A task",
            workflow_id=workflow_id,
            task_id=task_id,
            context_id=context_id,
            message_preview=message[:80],
        )

        result = await client.execute_workflow(
            "OrchestrationWorkflow",
            args=[message, context_id or ""],
            id=workflow_id,
            task_queue=settings.temporal.task_queue,
        )

        logger.info(
            "Temporal workflow completed",
            workflow_id=workflow_id,
            result_preview=str(result)[:100],
        )

        return str(result)
