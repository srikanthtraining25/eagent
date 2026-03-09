"""
Temporal Worker entry point.

Starts a Temporal worker that registers all workflows and activities.
"""

from __future__ import annotations

import asyncio

from temporalio.worker import Worker

from app.activities.a2a_activities import (
    discover_agent,
    get_a2a_task_status,
    send_a2a_task,
)
from app.activities.agent_activities import run_action_agent, run_kb_agent
from app.activities.classification import classify_intent
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.temporal import get_temporal_client
from app.workflows.action_workflow import ActionSubWorkflow
from app.workflows.delegate_workflow import DelegateSubWorkflow
from app.workflows.kb_workflow import KBSubWorkflow
from app.workflows.orchestrator import OrchestrationWorkflow

logger = get_logger(__name__)


async def run_worker() -> None:
    """Start the Temporal worker with all registered workflows and activities."""
    setup_logging()
    settings = get_settings()

    logger.info(
        "Starting Temporal worker",
        task_queue=settings.temporal.task_queue,
        temporal_server=settings.temporal.server_url,
    )

    client = await get_temporal_client()

    worker = Worker(
        client,
        task_queue=settings.temporal.task_queue,
        workflows=[
            OrchestrationWorkflow,
            KBSubWorkflow,
            ActionSubWorkflow,
            DelegateSubWorkflow,
        ],
        activities=[
            classify_intent,
            run_kb_agent,
            run_action_agent,
            send_a2a_task,
            get_a2a_task_status,
            discover_agent,
        ],
    )

    logger.info("Temporal worker started — waiting for tasks")
    await worker.run()


def main() -> None:
    """Entry point for `python -m app.main`."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
