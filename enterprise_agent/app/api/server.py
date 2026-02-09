# ... imports ...
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from typing import Optional
import uuid

from enterprise_agent.app.agent.graph import create_agent_graph
from enterprise_agent.app.core.config import settings
from enterprise_agent.app.services.checkpointer import get_checkpointer
from enterprise_agent.app.services.middleware import validate_token

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    user_id: str = "user123"

# ... (ApproveRequest remains same) ...

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Generate thread_id if not provided
    thread_id = request.thread_id or str(uuid.uuid4())
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # ... (rest of the function uses local variable `thread_id` instead of `request.thread_id`) ...
    
    # Initialize state with user info if new
    # For simplicity, we just pass the message. The state schema handles default.
    # In a real app, we might check if state exists and inject user_info if not.
    
    initial_inputs = {
        "messages": [HumanMessage(content=request.message)],
        "user_info": {"id": request.user_id, "role": "admin"}, # Mock user info
        "dialog_context": {},
        "middleware_results": {},
        "next_step": None
    }
    
    try:
        # If thread exists, this appends. If new, it starts.
        result = graph.invoke(initial_inputs, config=config)
        
        # Check if we stopped for interrupt
        snapshot = graph.get_state(config) 
        if snapshot.next:
             return {
                 "response": "Action pending approval. Please approve to proceed.",
                 "status": "interrupted",
                 "thread_id": thread_id
             }
             
        return {
            "response": result["messages"][-1].content,
            "status": "completed",
            "thread_id": thread_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approve")
async def approve_endpoint(request: ApproveRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    
    if not request.approved:
        # If rejected, we should probably update state or route to a "Rejected" node.
        # For now, let's just return a message saying cancelled.
        # Or we could invoke with a "Rejected" message?
        return {"response": "Action cancelled.", "status": "cancelled"}
    
    try:
        # Resume the graph
        # Passing None as input to resume from interruption
        result = graph.invoke(None, config=config)
        
        return {
            "response": result["messages"][-1].content,
            "status": "completed",
            "thread_id": request.thread_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
