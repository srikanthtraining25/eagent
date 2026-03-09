"""
Agent Activities — Temporal Activities that invoke LangGraph agents in-process.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from temporalio import activity

from app.agents.checkpoint import get_checkpointer
from app.agents.kb_graph import build_kb_graph
from app.agents.action_graph import build_action_graph
from app.core.logging import get_logger

logger = get_logger(__name__)


@activity.defn(name="run_kb_agent")
async def run_kb_agent(message: str, session_id: str) -> str:
    """
    Temporal Activity — runs the LangGraph KB graph in-process.

    Args:
        message: User's query
        session_id: Session ID for checkpoint persistence

    Returns:
        Agent's response text.
    """
    logger.info(
        "Running KB agent",
        session_id=session_id,
        message_preview=message[:80],
    )

    checkpointer = get_checkpointer()
    graph = build_kb_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": session_id}}

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "context": {},
            "intent": "kb",
        },
        config,
    )

    response = result["messages"][-1].content
    logger.info(
        "KB agent completed",
        session_id=session_id,
        response_length=len(response),
    )
    return response


@activity.defn(name="run_action_agent")
async def run_action_agent(message: str, session_id: str) -> dict:
    """
    Temporal Activity — runs the LangGraph Action graph in-process.

    Args:
        message: User's request
        session_id: Session ID for checkpoint persistence

    Returns:
        Dict with keys: response (str), needs_approval (bool), sensitive_tool (str|None)
    """
    logger.info(
        "Running Action agent",
        session_id=session_id,
        message_preview=message[:80],
    )

    checkpointer = get_checkpointer()
    graph = build_action_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": session_id}}

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "context": {},
            "intent": "action",
        },
        config,
    )

    response = result["messages"][-1].content
    context = result.get("context", {})
    needs_approval = context.get("needs_approval", False)
    sensitive_tool = context.get("sensitive_tool")

    logger.info(
        "Action agent completed",
        session_id=session_id,
        needs_approval=needs_approval,
        sensitive_tool=sensitive_tool,
        response_length=len(response),
    )

    return {
        "response": response,
        "needs_approval": needs_approval,
        "sensitive_tool": sensitive_tool,
    }
