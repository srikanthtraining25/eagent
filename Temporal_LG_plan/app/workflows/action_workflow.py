"""
Action Sub-Workflow — handles action requests with Human-in-the-Loop support.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.activities.agent_activities import run_action_agent
    from app.core.config import get_settings


@workflow.defn(name="ActionSubWorkflow")
class ActionSubWorkflow:
    """
    Child workflow that processes action requests.

    If the action requires human approval (sensitive tool), the workflow
    pauses and waits for an approval signal before completing.
    """

    def __init__(self) -> None:
        self._approved: bool = False
        self._approval_received: bool = False

    @workflow.signal(name="approve")
    async def approve(self, approved: bool = True) -> None:
        """Signal handler for human approval."""
        self._approved = approved
        self._approval_received = True
        workflow.logger.info(
            f"Approval signal received: approved={approved}"
        )

    @workflow.run
    async def run(self, message: str, session_id: str) -> str:
        settings = get_settings()

        # Run the action agent
        result = await workflow.execute_activity(
            run_action_agent,
            args=[message, session_id],
            start_to_close_timeout=timedelta(
                seconds=settings.temporal.activity_start_to_close_timeout
            ),
        )

        needs_approval = result.get("needs_approval", False)
        response = result.get("response", "")
        sensitive_tool = result.get("sensitive_tool")

        if needs_approval:
            workflow.logger.info(
                f"Waiting for approval — sensitive tool: {sensitive_tool}"
            )

            # Wait for approval signal (with timeout from config)
            try:
                await workflow.wait_condition(
                    lambda: self._approval_received,
                    timeout=timedelta(
                        seconds=settings.temporal.workflow_execution_timeout
                    ),
                )
            except asyncio.TimeoutError:
                return (
                    f"Action timed out waiting for approval. "
                    f"Sensitive tool: {sensitive_tool}"
                )

            if not self._approved:
                return (
                    f"Action was rejected. "
                    f"Sensitive tool: {sensitive_tool}"
                )

            workflow.logger.info("Action approved, proceeding")

        return response
