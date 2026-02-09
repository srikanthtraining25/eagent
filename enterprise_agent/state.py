from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Full chat history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User details (ID, role, permissions)
    user_info: Dict[str, Any]
    
    # Current flow context (e.g., specific form data being filled)
    dialog_context: Dict[str, Any]
    
    # Results from RAI, PII, and Permission checks for the current turn
    middleware_results: Dict[str, Any]
    
    # Next intended action (controlled by Router)
    next_step: Optional[str]

    # Queue of actions to execute (for multi-action support)
    action_queue: List[Dict[str, Any]]
    
    # Currently processing action
    current_action: Optional[Dict[str, Any]]
