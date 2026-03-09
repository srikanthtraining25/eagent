"""
Orchestrator Workflow — main entry point for all requests.

Classifies intent and routes to the appropriate sub-workflow.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.activities.classification import classify_intent
    from app.core.config import get_settings
    from app.workflows.action_workflow import ActionSubWorkflow
    from app.workflows.delegate_workflow import DelegateSubWorkflow
    from app.workflows.kb_workflow import KBSubWorkflow


@workflow.defn(name="OrchestrationWorkflow")
class OrchestrationWorkflow:
    """
    Main orchestrator workflow.

    Flow:
    1. Classify the user's intent (KB / ACTION / DELEGATE)
    2. Route to the appropriate child workflow
    3. Return the result
    """

    @workflow.run
    async def run(self, message: str, session_id: str) -> str:
        settings = get_settings()
        timeout = timedelta(
            seconds=settings.temporal.activity_start_to_close_timeout
        )

        workflow.logger.info(
            f"Orchestration started: session={session_id}, "
            f"message_preview={message[:80]}"
        )

        # Step 1: Classify intent
        classification = await workflow.execute_activity(
            classify_intent,
            args=[message],
            start_to_close_timeout=timeout,
        )

        intent = classification.get("intent", "kb")
        workflow.logger.info(
            f"Intent classified: {intent} "
            f"(confidence={classification.get('confidence')})"
        )

        # Step 2: Route to sub-workflow
        if intent == "kb":
            result = await workflow.execute_child_workflow(
                KBSubWorkflow.run,
                args=[message, session_id],
                id=f"{workflow.info().workflow_id}-kb",
            )

        elif intent == "action":
            result = await workflow.execute_child_workflow(
                ActionSubWorkflow.run,
                args=[message, session_id],
                id=f"{workflow.info().workflow_id}-action",
            )

        elif intent == "delegate":
            agent_url = classification.get("delegate_agent_url", "")
            if not agent_url:
                result = (
                    "I'd like to delegate this to a specialist, but no "
                    "suitable external agent is available. Let me try to "
                    "help with what I know."
                )
                # Fallback to KB
                result = await workflow.execute_child_workflow(
                    KBSubWorkflow.run,
                    args=[message, session_id],
                    id=f"{workflow.info().workflow_id}-kb-fallback",
                )
            else:
                result = await workflow.execute_child_workflow(
                    DelegateSubWorkflow.run,
                    args=[agent_url, message, session_id],
                    id=f"{workflow.info().workflow_id}-delegate",
                )

        else:
            # Unknown intent — default to KB
            workflow.logger.warning(f"Unknown intent: {intent}, defaulting to KB")
            result = await workflow.execute_child_workflow(
                KBSubWorkflow.run,
                args=[message, session_id],
                id=f"{workflow.info().workflow_id}-kb-default",
            )

        workflow.logger.info(
            f"Orchestration completed: result_length={len(str(result))}"
        )

        return str(result)
