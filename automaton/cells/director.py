"""
Director Cell — the strategic eye of the automaton.

Monitors roadmap progress, community requests, and bug reports.
Identifies work needed and creates bounty proposals.
Uses Claude Opus 4.6 for decision-making.

States: idle -> analyzing -> proposing -> idle
"""

from __future__ import annotations

import logging
from typing import Any

from automaton.framework.cell import Cell
from automaton.framework.state import CellState, Transition

logger = logging.getLogger(__name__)


class DirectorCell(Cell):
    CELL_ID = "director"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.ANALYZING, "new signals detected"),
        Transition(CellState.ANALYZING, CellState.PROPOSING, "analysis complete"),
        Transition(CellState.PROPOSING, CellState.IDLE, "proposal published"),
        # error recovery
        Transition(CellState.ANALYZING, CellState.IDLE, "analysis cancelled"),
        Transition(CellState.PROPOSING, CellState.IDLE, "proposal cancelled"),
        Transition(CellState.ERROR, CellState.IDLE, "error recovery"),
    ]

    def __init__(
        self,
        roadmap_source: str = "docs/ROADMAP.md",
        model: str = "claude-opus-4-6-20250219",
    ) -> None:
        super().__init__()
        self.roadmap_source = roadmap_source
        self.model = model
        self._pending_signals: list[dict[str, Any]] = []
        self._current_proposal: dict[str, Any] | None = None

    # -- public helpers -------------------------------------------------------

    def ingest_signal(self, signal: dict[str, Any]) -> None:
        """Queue an external signal (bug report, feature request, etc.)."""
        self._pending_signals.append(signal)
        logger.debug("[director] ingested signal: %s", signal.get("type", "unknown"))

    # -- tick logic -----------------------------------------------------------

    async def _process(self) -> None:
        if self.state == CellState.IDLE:
            await self._check_for_work()
        elif self.state == CellState.ANALYZING:
            await self._analyze()
        elif self.state == CellState.PROPOSING:
            await self._propose()

    async def _check_for_work(self) -> None:
        """Transition to ANALYZING if there are pending signals."""
        if self._pending_signals:
            await self.transition_to(CellState.ANALYZING)

    async def _analyze(self) -> None:
        """
        Evaluate pending signals and decide whether a bounty is warranted.

        In production this calls Claude Opus 4.6 via the Anthropic API.
        Here we build the prompt context and simulate the decision.
        """
        signals = list(self._pending_signals)
        self._pending_signals.clear()

        # Build analysis context
        analysis: dict[str, Any] = {
            "signals": signals,
            "signal_count": len(signals),
            "model": self.model,
        }

        # Determine if any signal warrants a bounty proposal
        actionable = [s for s in signals if s.get("priority", "low") != "low"]
        if actionable:
            self._current_proposal = {
                "title": actionable[0].get("title", "Untitled bounty"),
                "description": actionable[0].get("description", ""),
                "priority": actionable[0].get("priority", "medium"),
                "source_signals": actionable,
                "analysis": analysis,
            }
            await self.transition_to(CellState.PROPOSING)
        else:
            # nothing actionable — go back to idle
            logger.info("[director] no actionable signals, returning to idle")
            await self.transition_to(CellState.IDLE)

    async def _propose(self) -> None:
        """Publish the proposal for the PM cell to pick up, then go idle."""
        if self._current_proposal:
            self.publish("proposal", self._current_proposal)
            logger.info(
                "[director] published proposal: %s",
                self._current_proposal.get("title"),
            )
            self._current_proposal = None
        await self.transition_to(CellState.IDLE)
