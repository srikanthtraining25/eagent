"""
Delegate Sub-Workflow — delegates tasks to external A2A agents.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.activities.a2a_activities import (
        get_a2a_task_status,
        send_a2a_task,
    )
    from app.core.config import get_settings


# Terminal A2A task statuses
TERMINAL_STATUSES = {"completed", "failed", "canceled"}


@workflow.defn(name="DelegateSubWorkflow")
class DelegateSubWorkflow:
    """
    Child workflow that delegates tasks to external A2A agents.

    Flow:
    1. Sends task to external agent via tasks/send
    2. Polls tasks/get until terminal status
    3. Returns the result
    """

    @workflow.run
    async def run(
        self, agent_url: str, message: str, context_id: str = ""
    ) -> str:
        settings = get_settings()
        timeout = timedelta(
            seconds=settings.temporal.activity_start_to_close_timeout
        )

        # Step 1: Send task to external agent
        task = await workflow.execute_activity(
            send_a2a_task,
            args=[agent_url, message, context_id or None],
            start_to_close_timeout=timeout,
        )

        task_id = task.get("id")
        status = task.get("status", "")

        workflow.logger.info(
            f"A2A task sent: id={task_id}, status={status}"
        )

        # Step 2: Poll until completed (if not already done)
        poll_count = 0
        max_polls = 30  # Configurable max polls

        while status not in TERMINAL_STATUSES and poll_count < max_polls:
            # Wait before polling
            await asyncio.sleep(2)

            task = await workflow.execute_activity(
                get_a2a_task_status,
                args=[agent_url, task_id],
                start_to_close_timeout=timeout,
            )

            status = task.get("status", "")
            poll_count += 1

            workflow.logger.info(
                f"A2A task poll #{poll_count}: status={status}"
            )

        # Step 3: Extract and return result
        if status == "completed":
            artifacts = task.get("artifacts", [])
            if artifacts:
                # Extract text from first artifact's parts
                parts = artifacts[0].get("parts", [])
                for part in parts:
                    if part.get("kind") == "text":
                        return part.get("text", "")

                return str(artifacts[0])

            return "Task completed but no artifacts returned."

        elif status == "failed":
            return f"External agent task failed: {task.get('error', 'Unknown error')}"

        else:
            return f"External agent task did not complete. Final status: {status}"
