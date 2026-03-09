"""
Shared agent state definitions for LangGraph graphs.
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    Shared state for all LangGraph agents.

    Attributes:
        messages: Conversation message history (auto-appended via add_messages reducer).
        session_id: Unique session identifier for multi-turn persistence.
        context: Additional context (user info, retrieved docs, etc.).
        intent: Classified intent (kb, action, delegate).
    """

    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    context: dict[str, Any]
    intent: str
