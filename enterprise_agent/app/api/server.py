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
    access_token: Optional[str] = None # For JWT
    user_id: Optional[str] = None # Fallback or debug

# ... (ApproveRequest remains same) ...

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Generate thread_id if not provided
    thread_id = request.thread_id or str(uuid.uuid4())
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # 1. Validate Access Token
    user_info = {"id": "anonymous", "role": "guest"}
    token = request.access_token
    
    if token:
        decoded_user = validate_token(token)
        if not decoded_user:
            raise HTTPException(status_code=401, detail="Invalid or expired access token")
        user_info = decoded_user
    
    # Initialize Input State
    initial_inputs = {
        "messages": [HumanMessage(content=request.message)],
        "user_info": user_info,
        "access_token": token, # Store raw token for downstream tools
        "dialog_context": {},
        "middleware_results": {},
        "next_step": None,
        "action_queue": [], # Initialize queue
        "current_action": None
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
