"""
Treasury Cell — manages reward calculation, escrow funding, and payouts.

Calculates reward based on complexity, urgency, and token reserves.
Manages escrow funding for new bounties.
Processes payouts on bounty completion.

States: idle -> calculating -> paying -> idle
"""

from __future__ import annotations

import logging
from typing import Any

from automaton.framework.cell import Cell
from automaton.framework.state import CellState, Transition

logger = logging.getLogger(__name__)

# Base reward rates per complexity tier (in SOL)
REWARD_TABLE: dict[str, float] = {
    "trivial": 0.5,
    "small": 1.0,
    "medium": 2.5,
    "large": 5.0,
    "epic": 10.0,
}

URGENCY_MULTIPLIER: dict[str, float] = {
    "critical": 2.0,
    "high": 1.5,
    "medium": 1.0,
    "low": 0.75,
}


class TreasuryCell(Cell):
    CELL_ID = "treasury"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.CALCULATING, "bounty spec received"),
        Transition(CellState.CALCULATING, CellState.PAYING, "reward calculated"),
        Transition(CellState.CALCULATING, CellState.IDLE, "insufficient reserves"),
        Transition(CellState.PAYING, CellState.IDLE, "payout complete"),
        # recovery
        Transition(CellState.PAYING, CellState.IDLE, "payout cancelled"),
        Transition(CellState.ERROR, CellState.IDLE, "error recovery"),
    ]

    def __init__(self, initial_reserves: float = 100.0) -> None:
        super().__init__()
        self._reserves: float = initial_reserves
        self._escrow: dict[int, float] = {}  # issue_number -> escrowed amount
        self._payouts: list[dict[str, Any]] = []
        self._pending_bounty: dict[str, Any] | None = None
        self._pending_payout_request: dict[str, Any] | None = None

    @property
    def reserves(self) -> float:
        return self._reserves

    @property
    def escrow(self) -> dict[int, float]:
        return dict(self._escrow)

    @property
    def payouts(self) -> list[dict[str, Any]]:
        return list(self._payouts)

    def request_payout(self, issue_number: int, recipient: str) -> None:
        """Queue a payout request for a completed bounty."""
        self._pending_payout_request = {
            "issue_number": issue_number,
            "recipient": recipient,
        }

    # -- tick logic -----------------------------------------------------------

    async def _process(self) -> None:
        if self.state == CellState.IDLE:
            await self._watch_for_work()
        elif self.state == CellState.CALCULATING:
            await self._calculate_and_escrow()
        elif self.state == CellState.PAYING:
            await self._process_payout()

    async def _watch_for_work(self) -> None:
        """React to PM posting a bounty spec or a payout request."""
        pm = self.neighbor("pm")
        if pm and pm.payload.get("bounty_spec"):
            spec = pm.payload["bounty_spec"]
            if spec.get("issue_number") not in self._escrow:
                self._pending_bounty = spec
                await self.transition_to(CellState.CALCULATING)
                return

        if self._pending_payout_request:
            await self.transition_to(CellState.CALCULATING)

    async def _calculate_and_escrow(self) -> None:
        """Calculate reward and move funds into escrow (or process payout)."""
        if self._pending_payout_request:
            # transition to paying
            await self.transition_to(CellState.PAYING)
            return

        if self._pending_bounty is None:
            await self.transition_to(CellState.IDLE)
            return

        spec = self._pending_bounty
        complexity = spec.get("complexity", "medium")
        priority = spec.get("priority", "medium")

        base = REWARD_TABLE.get(complexity, 2.5)
        multiplier = URGENCY_MULTIPLIER.get(priority, 1.0)
        reward = round(base * multiplier, 4)

        if reward > self._reserves:
            logger.warning(
                "[treasury] insufficient reserves (%.4f needed, %.4f available)",
                reward,
                self._reserves,
            )
            self._pending_bounty = None
            await self.transition_to(CellState.IDLE)
            return

        issue_num = spec["issue_number"]
        self._reserves -= reward
        self._escrow[issue_num] = reward
        self.publish("escrow", {"issue_number": issue_num, "amount": reward})
        logger.info("[treasury] escrowed %.4f SOL for issue #%d", reward, issue_num)
        self._pending_bounty = None
        await self.transition_to(CellState.PAYING)

    async def _process_payout(self) -> None:
        """Release escrowed funds to the bounty completer."""
        if self._pending_payout_request:
            req = self._pending_payout_request
            issue_num = req["issue_number"]
            amount = self._escrow.pop(issue_num, 0.0)
            if amount > 0:
                payout = {
                    "issue_number": issue_num,
                    "recipient": req["recipient"],
                    "amount": amount,
                }
                self._payouts.append(payout)
                self.publish("payout", payout)
                logger.info(
                    "[treasury] paid %.4f SOL to %s for issue #%d",
                    amount,
                    req["recipient"],
                    issue_num,
                )
            self._pending_payout_request = None

        await self.transition_to(CellState.IDLE)
