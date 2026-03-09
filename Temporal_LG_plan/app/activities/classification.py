"""
Intent Classification Activity.

Classifies user messages into KB, ACTION, or DELEGATE intents.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from temporalio import activity

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ClassificationResult:
    """Result of intent classification."""

    intent: str  # "kb", "action", or "delegate"
    confidence: float
    reasoning: str
    delegate_agent_url: str | None = None


@activity.defn(name="classify_intent")
async def classify_intent(message: str) -> dict:
    """
    Temporal Activity — classifies user message intent.

    Returns:
        Dict with keys: intent, confidence, reasoning, delegate_agent_url
    """
    settings = get_settings()

    llm = ChatOpenAI(
        model=settings.llm.model,
        temperature=0.0,
        api_key=settings.llm.api_key,
    )

    classification_prompt = """You are an intent classifier for an enterprise agent system.

Classify the user's message into exactly one of these categories:

1. **kb** — The user is asking a question, seeking information, or wants to know something.
   Examples: "How do I reset my password?", "What is the leave policy?", "Tell me about..."

2. **action** — The user wants to perform an action, execute a task, create/submit/update something.
   Examples: "Submit a leave request", "Create a ticket", "Look up employee John"

3. **delegate** — The user's request is about a domain that requires an external specialist agent
   (travel, finance, external systems not covered by KB or Action).
   Examples: "Check my flight status", "What's the stock price of GOOG?"

Respond with ONLY a JSON object (no markdown):
{"intent": "kb|action|delegate", "confidence": 0.0-1.0, "reasoning": "brief explanation"}
"""

    response = await llm.ainvoke(
        [
            HumanMessage(content=classification_prompt),
            HumanMessage(content=f"User message: {message}"),
        ]
    )

    # Parse LLM response
    import json

    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        logger.warning(
            "Failed to parse classification, defaulting to kb",
            raw_response=response.content,
        )
        result = {
            "intent": "kb",
            "confidence": 0.5,
            "reasoning": "Failed to parse — defaulting to KB",
        }

    intent = result.get("intent", "kb").lower()
    if intent not in ("kb", "action", "delegate"):
        intent = "kb"

    logger.info(
        "Intent classified",
        intent=intent,
        confidence=result.get("confidence"),
        reasoning=result.get("reasoning"),
        message_preview=message[:80],
    )

    return {
        "intent": intent,
        "confidence": result.get("confidence", 0.0),
        "reasoning": result.get("reasoning", ""),
        "delegate_agent_url": None,
    }
