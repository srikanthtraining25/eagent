"""
FastAPI server — unified gateway for user chat, HITL approval, and A2A inbound.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.a2a.registry import AgentRegistry
from app.a2a.worker import TemporalA2AWorker
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.temporal import get_temporal_client

logger = get_logger(__name__)

# Module-level singletons
_registry: AgentRegistry | None = None
_a2a_worker: TemporalA2AWorker | None = None


# ---- Lifespan ----


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown."""
    global _registry, _a2a_worker

    setup_logging()
    settings = get_settings()
    logger.info(
        "Starting Enterprise Agent",
        name=settings.app.name,
        version=settings.app.version,
        port=settings.app.port,
    )

    # Initialize Temporal client
    await get_temporal_client()
    logger.info("Temporal client ready")

    # Initialize Agent Registry (discover external agents)
    _registry = AgentRegistry()
    await _registry.discover_all()
    logger.info(
        "Agent registry ready",
        external_agents=_registry.agent_count,
    )

    # Initialize A2A Worker
    _a2a_worker = TemporalA2AWorker()
    logger.info("A2A worker ready")

    yield

    logger.info("Shutting down Enterprise Agent")


# ---- App ----


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description=settings.a2a.agent_description,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(router)

    return app


# ---- Request/Response Models ----


class ChatRequest(BaseModel):
    """Chat request from user."""

    message: str = Field(..., description="User's message")
    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Session ID for multi-turn conversations",
    )


class ChatResponse(BaseModel):
    """Chat response to user."""

    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID")
    workflow_id: str = Field(..., description="Temporal workflow ID")


class ApprovalRequest(BaseModel):
    """Approval request for HITL."""

    approved: bool = Field(default=True, description="Whether the action is approved")


class ApprovalResponse(BaseModel):
    """Approval response."""

    status: str = Field(..., description="Status of the approval")
    workflow_id: str = Field(..., description="Workflow that was approved")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    name: str = ""
    version: str = ""


class AgentCardResponse(BaseModel):
    """Agent Card for A2A discovery."""

    name: str
    description: str
    version: str
    url: str
    capabilities: dict
    skills: list[dict]


# ---- Routes ----

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        name=settings.app.name,
        version=settings.app.version,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.

    Starts a Temporal OrchestrationWorkflow for the user's message.
    """
    settings = get_settings()
    client = await get_temporal_client()

    workflow_id = f"chat-{request.session_id}-{uuid4().hex[:8]}"

    logger.info(
        "Chat request received",
        session_id=request.session_id,
        workflow_id=workflow_id,
        message_preview=request.message[:80],
    )

    try:
        result = await client.execute_workflow(
            "OrchestrationWorkflow",
            args=[request.message, request.session_id],
            id=workflow_id,
            task_queue=settings.temporal.task_queue,
        )
    except Exception as e:
        logger.error("Workflow execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")

    logger.info(
        "Chat response generated",
        workflow_id=workflow_id,
        response_length=len(str(result)),
    )

    return ChatResponse(
        response=str(result),
        session_id=request.session_id,
        workflow_id=workflow_id,
    )


@router.post("/approve/{workflow_id}", response_model=ApprovalResponse)
async def approve_action(
    workflow_id: str, request: ApprovalRequest
) -> ApprovalResponse:
    """
    Approve or reject a pending action.

    Sends a signal to the ActionSubWorkflow waiting for approval.
    """
    client = await get_temporal_client()

    logger.info(
        "Approval request",
        workflow_id=workflow_id,
        approved=request.approved,
    )

    try:
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("approve", request.approved)
    except Exception as e:
        logger.error("Approval signal failed", error=str(e))
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found or signal failed: {str(e)}",
        )

    return ApprovalResponse(
        status="approved" if request.approved else "rejected",
        workflow_id=workflow_id,
    )


@router.get("/.well-known/agent.json")
async def agent_card() -> dict:
    """
    Serve the A2A Agent Card for external agent discovery.
    """
    settings = get_settings()

    return {
        "name": settings.a2a.agent_name,
        "description": settings.a2a.agent_description,
        "version": settings.a2a.agent_version,
        "url": f"{settings.a2a.base_url}/a2a",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "skills": [
            {
                "id": "knowledge",
                "name": "Knowledge Retrieval",
                "description": "RAG-based Q&A from enterprise knowledge base",
                "examples": [
                    "How do I reset my password?",
                    "What is the leave policy?",
                ],
            },
            {
                "id": "actions",
                "name": "Action Execution",
                "description": "Execute enterprise actions with optional approval",
                "examples": [
                    "Submit a leave request",
                    "Create a support ticket",
                ],
            },
            {
                "id": "delegation",
                "name": "Task Delegation",
                "description": "Delegate to specialized external agents",
                "examples": [
                    "Check my flight status",
                    "Look up stock price",
                ],
            },
        ],
        "authentication": {
            "schemes": ["bearer"],
        },
    }


@router.post("/a2a")
async def a2a_endpoint(request: dict) -> dict:
    """
    A2A JSON-RPC 2.0 endpoint for inbound agent-to-agent communication.

    Handles tasks/send, tasks/get, and tasks/cancel methods.
    """
    global _a2a_worker

    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id")

    logger.info("A2A request received", method=method, request_id=request_id)

    try:
        if method == "tasks/send":
            # Extract message from parts
            message_data = params.get("message", {})
            parts = message_data.get("parts", [])
            text = ""
            for part in parts:
                if part.get("kind") == "text":
                    text = part.get("text", "")
                    break

            context_id = params.get("contextId", str(uuid4()))
            task_id = str(uuid4())

            # Run via Temporal
            result = await _a2a_worker.run_task(
                message=text,
                context_id=context_id,
                task_id=task_id,
            )

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "id": task_id,
                    "contextId": context_id,
                    "status": "completed",
                    "artifacts": [
                        {
                            "parts": [{"kind": "text", "text": result}],
                        }
                    ],
                },
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    except Exception as e:
        logger.error("A2A request failed", method=method, error=str(e))
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": str(e),
            },
        }


# Create the app instance
app = create_app()
