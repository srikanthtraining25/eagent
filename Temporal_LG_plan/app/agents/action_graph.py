"""
LangGraph Action Graph — ReAct tool-calling agent.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---- Example Tools (replace with real enterprise tools) ----


@tool
def submit_leave_request(
    employee_id: str, start_date: str, end_date: str, reason: str
) -> str:
    """Submit a leave request for an employee."""
    logger.info(
        "Submitting leave request",
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
    )
    # Placeholder — integrate with HR system
    return f"Leave request submitted for {employee_id} from {start_date} to {end_date}."


@tool
def lookup_employee(employee_id: str) -> str:
    """Look up employee details by ID."""
    logger.info("Looking up employee", employee_id=employee_id)
    # Placeholder
    return f"Employee {employee_id}: John Doe, Engineering, Senior Engineer."


@tool
def create_ticket(title: str, description: str, priority: str = "medium") -> str:
    """Create a support ticket."""
    logger.info("Creating ticket", title=title, priority=priority)
    # Placeholder
    return f"Ticket created: '{title}' with priority {priority}. ID: TKT-{hash(title) % 10000:04d}"


# Sensitive tools that require human approval
SENSITIVE_TOOLS = {"submit_leave_request"}

# All available tools
ALL_TOOLS = [submit_leave_request, lookup_employee, create_ticket]


def _create_llm() -> ChatOpenAI:
    """Create LLM instance with tools bound."""
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm.model,
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
        api_key=settings.llm.api_key,
    )
    return llm.bind_tools(ALL_TOOLS)


async def plan_action(state: AgentState) -> AgentState:
    """
    Planning node — LLM decides which tool(s) to call.
    """
    llm = _create_llm()
    messages = state["messages"]

    system_prompt = (
        "You are an Enterprise Action Agent. You can execute actions on behalf of users.\n"
        "Available tools: submit_leave_request, lookup_employee, create_ticket.\n"
        "Analyze the user's request and call the appropriate tool.\n"
        "If the action seems sensitive, still proceed with the tool call — "
        "approval will be handled by the system."
    )

    response = await llm.ainvoke(
        [HumanMessage(content=system_prompt)] + messages
    )

    logger.info(
        "Action plan generated",
        has_tool_calls=bool(response.tool_calls),
        num_tool_calls=len(response.tool_calls) if response.tool_calls else 0,
    )

    return {"messages": [response]}


async def execute_tools(state: AgentState) -> AgentState:
    """
    Tool execution node — runs the tool calls from the LLM response.
    """
    messages = state["messages"]
    last_message = messages[-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return state

    tool_map = {t.name: t for t in ALL_TOOLS}
    results = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        logger.info("Executing tool", tool_name=tool_name, args=tool_args)

        if tool_name in tool_map:
            result = await tool_map[tool_name].ainvoke(tool_args)
            from langchain_core.messages import ToolMessage

            results.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )

    return {"messages": results}


async def summarize_result(state: AgentState) -> AgentState:
    """
    Summary node — generates a human-friendly response from tool results.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm.model,
        temperature=settings.llm.temperature,
        api_key=settings.llm.api_key,
    )

    messages = state["messages"]
    response = await llm.ainvoke(
        [
            HumanMessage(
                content="Summarize the results of the actions taken in a clear, "
                "user-friendly way. Be concise."
            )
        ]
        + messages
    )

    return {"messages": [response]}


def _should_execute(state: AgentState) -> str:
    """Router: check if the LLM wants to call tools."""
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute"
    return "end"


def check_approval_needed(state: AgentState) -> dict[str, Any]:
    """
    Check if any tool call requires human approval.

    Returns updated context with needs_approval flag.
    """
    messages = state["messages"]
    context = state.get("context", {})

    for msg in messages:
        if hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                if tc["name"] in SENSITIVE_TOOLS:
                    context["needs_approval"] = True
                    context["sensitive_tool"] = tc["name"]
                    logger.info(
                        "Approval required",
                        tool=tc["name"],
                    )
                    return {**state, "context": context}

    context["needs_approval"] = False
    return {**state, "context": context}


def build_action_graph() -> StateGraph:
    """
    Build the Action agent LangGraph graph.

    Flow: plan_action → (tools?) → execute_tools → summarize → END
    """
    graph = StateGraph(AgentState)

    graph.add_node("plan", plan_action)
    graph.add_node("execute", execute_tools)
    graph.add_node("summarize", summarize_result)

    graph.set_entry_point("plan")
    graph.add_conditional_edges(
        "plan",
        _should_execute,
        {"execute": "execute", "end": END},
    )
    graph.add_edge("execute", "summarize")
    graph.add_edge("summarize", END)

    return graph
