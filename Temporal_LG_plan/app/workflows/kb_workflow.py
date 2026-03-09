"""
KB Sub-Workflow — handles knowledge base queries.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.activities.agent_activities import run_kb_agent
    from app.core.config import get_settings


@workflow.defn(name="KBSubWorkflow")
class KBSubWorkflow:
    """
    Child workflow that processes KB (knowledge base) queries.

    Simply delegates to the run_kb_agent activity.
    """

    @workflow.run
    async def run(self, message: str, session_id: str) -> str:
        settings = get_settings()

        result = await workflow.execute_activity(
            run_kb_agent,
            args=[message, session_id],
            start_to_close_timeout=timedelta(
                seconds=settings.temporal.activity_start_to_close_timeout
            ),
        )

        return result
