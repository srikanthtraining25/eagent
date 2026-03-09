"""
Agent Registry — discovers and caches external A2A Agent Cards.
"""

from __future__ import annotations

from typing import Any

from app.a2a.client import A2AClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentRegistry:
    """
    Registry of known A2A agents and their capabilities.

    - Discovers agents from configured URLs at startup.
    - Caches Agent Cards in memory.
    - Matches queries to agent skills for delegation.
    """

    def __init__(self, agent_urls: list[str] | None = None):
        settings = get_settings()
        self._agent_urls = agent_urls or settings.a2a.external_agent_urls
        self._cards: dict[str, dict[str, Any]] = {}  # name → Agent Card
        self._client = A2AClient()

    async def discover_all(self) -> None:
        """
        Discover and cache Agent Cards from all configured URLs.

        Call this at application startup.
        """
        for url in self._agent_urls:
            try:
                card = await self._client.discover(url)
                name = card.get("name", url)
                self._cards[name] = card
                logger.info(
                    "Agent registered",
                    name=name,
                    url=card.get("url"),
                    skills=len(card.get("skills", [])),
                )
            except Exception as e:
                logger.warning(
                    "Failed to discover agent",
                    url=url,
                    error=str(e),
                )

    def register(self, card: dict[str, Any]) -> None:
        """Manually register an Agent Card."""
        name = card.get("name", "unknown")
        self._cards[name] = card
        logger.info("Agent manually registered", name=name)

    def get_all_agents(self) -> list[dict[str, Any]]:
        """Get all registered Agent Cards."""
        return list(self._cards.values())

    def get_agent(self, name: str) -> dict[str, Any] | None:
        """Get a specific agent by name."""
        return self._cards.get(name)

    def find_by_skill(self, query: str) -> dict[str, Any] | None:
        """
        Find an agent whose skills match the query.

        Simple keyword matching — can be enhanced with embeddings.

        Args:
            query: The user's query to match against agent skills.

        Returns:
            Matching Agent Card, or None if no match.
        """
        query_lower = query.lower()

        for card in self._cards.values():
            for skill in card.get("skills", []):
                skill_text = (
                    f"{skill.get('name', '')} {skill.get('description', '')}"
                ).lower()

                # Check if any skill keywords match the query
                if any(
                    word in query_lower
                    for word in skill_text.split()
                    if len(word) > 3
                ):
                    logger.info(
                        "Agent matched",
                        agent=card.get("name"),
                        skill=skill.get("name"),
                        query=query[:80],
                    )
                    return card

        return None

    @property
    def agent_count(self) -> int:
        return len(self._cards)
