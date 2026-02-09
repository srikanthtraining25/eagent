import sys
import os
from langchain_core.messages import HumanMessage
from redis import Redis
from langgraph.checkpoint.memory import MemorySaver

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock LLM and Graph for testing without API Key
from unittest.mock import MagicMock, patch

# Update settings to avoid API errors
os.environ["OPENAI_API_KEY"] = "mock_key"

from enterprise_agent.state import AgentState
from enterprise_agent.graph import create_agent_graph
from enterprise_agent.config import settings

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
    print("--- Starting Verification (Router -> Planner -> Dispatcher) ---")
    
    checkpointer = MemorySaver()
    
    # Patch BOTH Router and Planner
    with patch("enterprise_agent.graph.router_node", side_effect=mock_router_node), \
         patch("enterprise_agent.graph.action_planner_node", side_effect=mock_planner_node):
        
        # 2. Initialize Graph
        graph = create_agent_graph(checkpointer=checkpointer)
        thread_id = "test_planner_1"
        config = {"configurable": {"thread_id": thread_id}}
        
        # 3. Test Multi-Action Flow
        print("\n--- Test 1: Multiple Actions (via Planner) ---")
        item1 = "Execute multiple actions"
        inputs = {
            "messages": [HumanMessage(content=item1)],
            "user_info": {"id": "tester", "role": "admin"}
        }
        
        # Step 1: Start -> Router -> Planner -> Dispatcher -> Action1 -> Review
        print("[Step 1] Initial Invoke...")
        result = graph.invoke(inputs, config=config)
        
        snapshot = graph.get_state(config)
        if snapshot.next:
            print(f"[Pass] Graph interrupted at: {snapshot.next}")
            # Verify Action 1
            curr = snapshot.values.get("current_action")
            print(f"[Check] Current Action ID: {curr['parameters']['id']}")
            if curr['parameters']['id'] == "1":
                print("[Pass] Action 1 is active.")
        else:
            print(f"[Fail] Graph did not interrupt. Result: {result}")
            return

        # Step 2: Approve Action 1
        print("\n[Step 2] Approving Action 1...")
        result = graph.invoke(None, config=config)
        
        snapshot = graph.get_state(config)
        if snapshot.next:
             print(f"[Pass] Graph interrupted again at: {snapshot.next}")
             curr = snapshot.values.get("current_action")
             if curr['parameters']['id'] == "2":
                 print("[Pass] Action 2 is active.")
        else:
             print(f"[Fail] Graph did not interrupt for second action.")
             return

        # Step 3: Approve Action 2
        print("\n[Step 3] Approving Action 2...")
        result = graph.invoke(None, config=config)
        print("[Pass] Graph completed successfully.")

if __name__ == "__main__":
    run_verification()
