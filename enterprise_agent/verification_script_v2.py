import sys
import os
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

# Add PARENT directory of 'enterprise_agent' to sys.path
# Script is in: .../enterprise_agent/verification_script_v2.py
# We need to add: .../
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Update settings to avoid API errors
os.environ["OPENAI_API_KEY"] = "mock_key"

# Imports from new locations
from enterprise_agent.app.core.state import AgentState
from enterprise_agent.app.agent.graph import create_agent_graph
from enterprise_agent.app.core.config import settings

# Mock LLM and Graph for testing without API Key
from unittest.mock import MagicMock, patch

def mock_router_node(state: AgentState):
    """
    Mock router returns 'planner' for actions, 'kb' for questions.
    """
    messages = state["messages"]
    last_msg = messages[-1].content.lower()
    
    if "action" in last_msg or "multiple" in last_msg:
         return {"next_step": "planner"}
    else:
         return {"next_step": "kb"}

def mock_planner_node(state: AgentState):
    """
    Mock planner returns action_queue.
    """
    messages = state["messages"]
    last_msg = messages[-1].content.lower()
    
    actions = []
    if "multiple" in last_msg:
        actions = [
            {"tool_name": "perform_action", "parameters": {"id": "1", "data": "task1"}},
            {"tool_name": "perform_action", "parameters": {"id": "2", "data": "task2"}}
        ]
    elif "action" in last_msg:
        actions = [
             {"tool_name": "perform_action", "parameters": {"id": "single", "data": "task"}}
        ]
        
    return {
        "next_step": "dispatcher",
        "action_queue": actions
    }

def run_verification():
    print("--- Starting Verification V2 (New Structure) ---")
    
    checkpointer = MemorySaver()
    
    # Patch BOTH Router and Planner
    with patch("enterprise_agent.app.agent.graph.router_node", side_effect=mock_router_node), \
         patch("enterprise_agent.app.agent.graph.action_planner_node", side_effect=mock_planner_node):
        
        # 2. Initialize Graph
        graph = create_agent_graph(checkpointer=checkpointer)
        thread_id = "test_struct_1"
        config = {"configurable": {"thread_id": thread_id}}
        
        # 3. Test Multi-Action Flow + Token Injection
        print("\n--- Test: Multi-Action + Token Injection ---")
        item1 = "Execute multiple actions"
        inputs = {
            "messages": [HumanMessage(content=item1)],
            "user_info": {"id": "tester", "role": "admin"},
            "access_token": "valid_mock_token"
        }
        
        # Step 1: Start -> Router -> Planner -> Dispatcher -> Action1 -> Review
        print("[Step 1] Initial Invoke...")
        result = graph.invoke(inputs, config=config)
        
        snapshot = graph.get_state(config)
        if snapshot.next:
            print(f"[Pass] Graph interrupted at: {snapshot.next}")
        else:
            print(f"[Fail] Graph did not interrupt. Result: {result}")
            return

        # Step 2: Approve Action 1
        print("\n[Step 2] Approving Action 1...")
        result = graph.invoke(None, config=config)
        
        snapshot = graph.get_state(config)
        if snapshot.next:
             print(f"[Pass] Graph interrupted again at: {snapshot.next}")
        else:
             print(f"[Fail] Graph did not interrupt for second action.")
             return

        # Step 3: Approve Action 2
        print("\n[Step 3] Approving Action 2...")
        result = graph.invoke(None, config=config)
        
        if not snapshot.next:
            print("[Pass] Graph completed successfully.")
            last_msg = result["messages"][-1].content
            print(f"[Result] Last Message: {last_msg}")
            if "Token Present" in last_msg:
                 print("[Pass] Tool received token.")
            else:
                 print("[Fail] Tool did NOT receive token!")

if __name__ == "__main__":
    run_verification()
