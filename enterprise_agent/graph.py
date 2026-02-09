from typing import Annotated, Literal, List, Optional
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from .state import AgentState
from .middleware import rai_check, pii_filter, check_permission, post_process_response
from .tools import search_kb, perform_action
from .checkpointer import get_checkpointer
from .config import settings

# --- Pydantic Models for Router ---

class RouteDecision(BaseModel):
    destination: Literal["kb", "action"] = Field(description="The intent of the user. 'kb' for information, 'action' for doing something.")

class ActionPlan(BaseModel):
    actions: List[dict] = Field(description="List of tool calls to execute.")

# --- Nodes ---

def router_node(state: AgentState):
    """
    Classifies intent: KB or Action.
    """
    messages = state["messages"]
    
    # Fast/Simple classification
    llm = ChatOpenAI(
        model=settings.ACTION_LLM_MODEL, 
        base_url=settings.ACTION_LLM_BASE_URL,
        api_key=settings.ACTION_LLM_API_KEY,
        temperature=0
    )
    structured_llm = llm.with_structured_output(RouteDecision)
    
    system_prompt = "Classify the user's intent. Route to 'kb' for questions/info. Route to 'action' if the user wants to perform a task or update something."
    
    response = structured_llm.invoke([SystemMessage(content=system_prompt)] + messages)
    
    if response.destination == "action":
        return {"next_step": "planner"}
    else:
        return {"next_step": "kb"}

def action_planner_node(state: AgentState):
    """
    Identifies specific tools to run using the Action LLM and Tool Bindings.
    """
    messages = state["messages"]
    
    # Initialize LLM with Tools
    llm = ChatOpenAI(
        model=settings.ACTION_LLM_MODEL, 
        base_url=settings.ACTION_LLM_BASE_URL,
        api_key=settings.ACTION_LLM_API_KEY,
        temperature=0
    )
    
    # Bind tools so LLM knows what's available
    tools = [perform_action, search_kb] # Give it all tools, or just action tools
    llm_with_tools = llm.bind_tools(tools)
    
    system_prompt = """You are an action planner. 
    Analyze the user's request and generate a list of tool calls to execute. 
    You can call multiple tools if needed.
    """
    
    response = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + messages)
    
    queue = []
    if response.tool_calls:
        for tc in response.tool_calls:
            queue.append({
                "tool_name": tc["name"],
                "parameters": tc["args"]
            })
    
    return {
        "next_step": "dispatcher",
        "action_queue": queue
    }

def kb_node(state: AgentState):
    """
    Queries the Knowledge Base using the KB LLM.
    """
    query = state["messages"][-1].content
    
    # Initialize KB Model
    llm = ChatOpenAI(
        model=settings.KB_LLM_MODEL,
        base_url=settings.KB_LLM_BASE_URL,
        api_key=settings.KB_LLM_API_KEY,
        temperature=0
    )
    
    # Simple RAG Simulation: 
    # 1. Retrieve context (mock)
    context = search_kb(query)
    
    # 2. Generate Answer using LLM
    system_prompt = f"You are a helpful assistant. Answer the user query based ONLY on the following context:\n\n{context}"
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=query)]
    
    response = llm.invoke(messages)
    
    return {"messages": [response]}

def action_dispatcher_node(state: AgentState):
    """
    Manages the action queue.
    """
    queue = state.get("action_queue", [])
    
    if not queue:
        return {"next_step": "done", "current_action": None}
    
    # Pop next action
    next_action = queue[0]
    remaining_queue = queue[1:]
    
    return {
        "current_action": next_action,
        "action_queue": remaining_queue,
        "next_step": "process_action"
    }

def action_input_node(state: AgentState):
    """
    Prepares for action, runs checks on the CURRENT action.
    """
    action = state.get("current_action")
    if not action:
        return {"next_step": "error"} # Should not happen

    # Extract data for checks
    # Assuming 'data' param exists or we construct it.
    params = action.get("parameters", {})
    data_content = str(params) # Simplification for checks
    
    # Middleware: RAI Check
    rai_result = rai_check(data_content)
    if not rai_result["safe"]:
         return {
            "messages": [AIMessage(content=f"Skipped action due to RAI: {rai_result['reason']}")],
            "next_step": "skip"
        }
    
    # Middleware: PII Filter
    # We might sanitize params here.
    
    # Middleware: Permission Check
    user_info = state.get("user_info", {})
    if not check_permission(user_info, "sensitive_action"):
         return {
            "messages": [AIMessage(content="Permission Denied for this action.")],
             "next_step": "skip"
        }

    # Prepare Context for Human Review
    # We update dialog_context to show what's waiting
    return {
        "dialog_context": {"action_type": action.get("tool_name"), "data": params},
        "messages": [AIMessage(content=f"Action '{action.get('tool_name')}' pending approval.")],
        "next_step": "review"
    }

def human_review_node(state: AgentState):
    pass

def execute_action_node(state: AgentState):
    """
    Executes the CURRENT action.
    """
    action = state.get("current_action")
    params = action.get("parameters", {})
    
    # Execute
    if action.get("tool_name") == "perform_action":
        result = perform_action.invoke(params)
    else:
        result = f"Unknown tool: {action.get('tool_name')}"
        
    return {"messages": [AIMessage(content=result)]}

def post_process_node(state: AgentState):
    """
    Final cleanup.
    """
    # Logic remains similar, mostly for context updates.
    return {"dialog_context": {}} # Clear context? Or keep history?

# --- Edges ---

def route_decision(state: AgentState) -> Literal["action_planner_node", "kb_node"]:
    if state["next_step"] == "planner":
        return "action_planner_node"
    return "kb_node"

def dispatch_decision(state: AgentState) -> Literal["action_input_node", "post_process_node"]:
    if state["next_step"] == "process_action":
        return "action_input_node"
    return "post_process_node"

def action_review_decision(state: AgentState) -> Literal["human_review_node", "action_dispatcher_node"]:
    # If skipped/blocked, go back to dispatcher for next action
    if state.get("next_step") == "skip":
        return "action_dispatcher_node"
    return "human_review_node"

# --- Graph ---

def create_agent_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    
    graph.add_node("router_node", router_node)
    graph.add_node("action_planner_node", action_planner_node)
    graph.add_node("kb_node", kb_node)
    graph.add_node("action_dispatcher_node", action_dispatcher_node)
    graph.add_node("action_input_node", action_input_node)
    graph.add_node("human_review_node", human_review_node)
    graph.add_node("execute_action_node", execute_action_node)
    graph.add_node("post_process_node", post_process_node)
    
    graph.add_edge(START, "router_node")
    
    graph.add_conditional_edges("router_node", route_decision)
    graph.add_edge("action_planner_node", "action_dispatcher_node")
    
    graph.add_conditional_edges("action_dispatcher_node", dispatch_decision)
    graph.add_conditional_edges("action_input_node", action_review_decision)
    
    graph.add_edge("human_review_node", "execute_action_node")
    graph.add_edge("execute_action_node", "action_dispatcher_node") # Loop back!
    
    graph.add_edge("kb_node", "post_process_node")
    graph.add_edge("post_process_node", END)
    
    if checkpointer is None:
        checkpointer = get_checkpointer()
    
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action_node"]
    )
