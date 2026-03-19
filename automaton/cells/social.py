"""
Social Cell — public-facing announcements and community monitoring.

Announces new bounties on X/Twitter.
Posts completion updates.
Monitors community sentiment.

States: idle -> announcing -> monitoring -> idle
"""

from __future__ import annotations

import logging
from typing import Any

from automaton.framework.cell import Cell
from automaton.framework.state import CellState, Transition

logger = logging.getLogger(__name__)


class SocialCell(Cell):
    CELL_ID = "social"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.ANNOUNCING, "new bounty to announce"),
        Transition(CellState.ANNOUNCING, CellState.MONITORING, "announcement posted"),
        Transition(CellState.MONITORING, CellState.IDLE, "monitoring cycle complete"),
        Transition(CellState.IDLE, CellState.MONITORING, "scheduled monitoring"),
        # recovery
        Transition(CellState.ANNOUNCING, CellState.IDLE, "announce cancelled"),
        Transition(CellState.MONITORING, CellState.IDLE, "monitoring cancelled"),
        Transition(CellState.ERROR, CellState.IDLE, "error recovery"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._announcements: list[dict[str, Any]] = []
        self._sentiment_log: list[dict[str, Any]] = []
        self._pending_announcement: dict[str, Any] | None = None

    @property
    def announcements(self) -> list[dict[str, Any]]:
        return list(self._announcements)

    @property
    def sentiment_log(self) -> list[dict[str, Any]]:
        return list(self._sentiment_log)

    # -- tick logic -----------------------------------------------------------

    async def _process(self) -> None:
        if self.state == CellState.IDLE:
            await self._check_for_announcements()
        elif self.state == CellState.ANNOUNCING:
            await self._announce()
        elif self.state == CellState.MONITORING:
            await self._monitor()

    async def _check_for_announcements(self) -> None:
        """Watch PM and Treasury for events worth announcing."""
        pm = self.neighbor("pm")
        treasury = self.neighbor("treasury")

        # New bounty posted by PM
        if pm and pm.payload.get("bounty_spec"):
            spec = pm.payload["bounty_spec"]
            self._pending_announcement = {
                "type": "new_bounty",
                "title": spec.get("title", "New Bounty"),
                "complexity": spec.get("complexity", "unknown"),
                "labels": spec.get("labels", []),
            }
            await self.transition_to(CellState.ANNOUNCING)
            return

        # Payout completed by Treasury
        if treasury and treasury.payload.get("payout"):
            payout = treasury.payload["payout"]
            self._pending_announcement = {
                "type": "payout",
                "issue_number": payout.get("issue_number"),
                "amount": payout.get("amount"),
                "recipient": payout.get("recipient"),
            }
            await self.transition_to(CellState.ANNOUNCING)
            return

    async def _announce(self) -> None:
        """
        Post the announcement to social channels.

        In production this calls the X/Twitter API.
        Here we simulate and log.
        """
        if self._pending_announcement is None:
            await self.transition_to(CellState.MONITORING)
            return

        ann = self._pending_announcement
        tweet = self._compose_tweet(ann)
        record = {**ann, "tweet": tweet, "posted": True}
        self._announcements.append(record)
        self.publish("last_announcement", record)
        logger.info("[social] announced: %s", tweet[:80])
        self._pending_announcement = None
        await self.transition_to(CellState.MONITORING)

    async def _monitor(self) -> None:
        """
        Check community sentiment.

        In production this scrapes mentions / replies.
        Here we produce a stub sentiment score.
        """
        sentiment: dict[str, Any] = {
            "tick": self.tick_count,
            "score": 0.75,  # placeholder positive sentiment
            "mentions": 0,
        }
        self._sentiment_log.append(sentiment)
        self.publish("sentiment", sentiment)
        await self.transition_to(CellState.IDLE)

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _compose_tweet(ann: dict[str, Any]) -> str:
        if ann["type"] == "new_bounty":
            return (
                f"New SolFoundry bounty: {ann['title']} "
                f"(complexity: {ann['complexity']}). "
                "Contribute and earn! #SolFoundry #Solana"
            )
        if ann["type"] == "payout":
            return (
                f"Bounty #{ann['issue_number']} completed! "
                f"{ann['amount']} SOL paid to {ann['recipient']}. "
                "Great work! #SolFoundry #Solana"
            )
        return "SolFoundry update! #SolFoundry #Solana"
