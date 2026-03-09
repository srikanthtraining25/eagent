"""
LangGraph KB (Knowledge Base) Graph — RAG-based Q&A agent.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _create_llm() -> ChatOpenAI:
    """Create LLM instance from settings."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.llm.model,
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
        api_key=settings.llm.api_key,
    )


async def retrieve_context(state: AgentState) -> AgentState:
    """
    RAG retrieval node — fetches relevant documents.

    TODO: Integrate with actual vector store (e.g., ChromaDB, Pinecone).
    Currently returns a placeholder context.
    """
    settings = get_settings()
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    logger.info(
        "Retrieving context",
        query=last_message[:100],
        collection=settings.kb.collection_name,
        top_k=settings.kb.top_k,
    )

    # Placeholder — replace with actual vector store retrieval
    retrieved_docs = [
        f"[Retrieved context for: '{last_message[:50]}...'] "
        "This is a placeholder. Integrate your vector store here."
    ]

    context = state.get("context", {})
    context["retrieved_docs"] = retrieved_docs

    return {**state, "context": context}


async def generate_response(state: AgentState) -> AgentState:
    """
    Generation node — produces answer using retrieved context + LLM.
    """
    llm = _create_llm()
    messages = state["messages"]
    context = state.get("context", {})
    retrieved_docs = context.get("retrieved_docs", [])

    # Build system prompt with context
    context_text = "\n".join(retrieved_docs) if retrieved_docs else "No context available."

    system_prompt = (
        "You are a helpful Enterprise Knowledge Base assistant. "
        "Answer the user's question based on the following context:\n\n"
        f"Context:\n{context_text}\n\n"
        "If the context doesn't contain the answer, say so honestly."
    )

    # Invoke LLM
    response = await llm.ainvoke(
        [HumanMessage(content=system_prompt)] + messages
    )

    logger.info("KB response generated", response_length=len(response.content))

    return {"messages": [response]}


def build_kb_graph() -> StateGraph:
    """
    Build the KB agent LangGraph graph.

    Flow: retrieve_context → generate_response → END
    """
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_context)
    graph.add_node("generate", generate_response)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph
