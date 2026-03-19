"""
PM Cell — Project Manager that decomposes Director proposals into bounty specs.

Takes Director proposals and decomposes into bounty specs.
Generates acceptance criteria, estimates complexity.
Posts as GitHub Issues with proper templates.

States: idle -> decomposing -> posting -> idle
"""

from __future__ import annotations

import logging
from typing import Any

from automaton.framework.cell import Cell
from automaton.framework.state import CellState, Transition

logger = logging.getLogger(__name__)


# Complexity tiers used for estimation
COMPLEXITY_TIERS = {
    "trivial": {"points": 1, "hours_estimate": "1-2h"},
    "small": {"points": 2, "hours_estimate": "2-4h"},
    "medium": {"points": 5, "hours_estimate": "4-8h"},
    "large": {"points": 8, "hours_estimate": "1-2d"},
    "epic": {"points": 13, "hours_estimate": "3-5d"},
}


class PMCell(Cell):
    CELL_ID = "pm"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.DECOMPOSING, "director published proposal"),
        Transition(CellState.DECOMPOSING, CellState.POSTING, "spec ready"),
        Transition(CellState.POSTING, CellState.IDLE, "issue posted"),
        # recovery
        Transition(CellState.DECOMPOSING, CellState.IDLE, "decompose cancelled"),
        Transition(CellState.POSTING, CellState.IDLE, "post cancelled"),
        Transition(CellState.ERROR, CellState.IDLE, "error recovery"),
    ]

    def __init__(self, repo: str = "solfoundry/solfoundry") -> None:
        super().__init__()
        self.repo = repo
        self._current_spec: dict[str, Any] | None = None
        self._posted_issues: list[dict[str, Any]] = []

    @property
    def posted_issues(self) -> list[dict[str, Any]]:
        return list(self._posted_issues)

    # -- tick logic -----------------------------------------------------------

    async def _process(self) -> None:
        if self.state == CellState.IDLE:
            await self._watch_director()
        elif self.state == CellState.DECOMPOSING:
            await self._decompose()
        elif self.state == CellState.POSTING:
            await self._post_issue()

    async def _watch_director(self) -> None:
        """Check if the Director has published a new proposal."""
        director = self.neighbor("director")
        if director and director.payload.get("proposal"):
            self._current_spec = director.payload["proposal"]
            await self.transition_to(CellState.DECOMPOSING)

    async def _decompose(self) -> None:
        """Break the proposal into a bounty spec with acceptance criteria."""
        if self._current_spec is None:
            await self.transition_to(CellState.IDLE)
            return

        proposal = self._current_spec
        priority = proposal.get("priority", "medium")
        complexity = self._estimate_complexity(priority)

        spec: dict[str, Any] = {
            "title": f"[Bounty] {proposal.get('title', 'Untitled')}",
            "description": proposal.get("description", ""),
            "priority": priority,
            "complexity": complexity,
            "acceptance_criteria": self._generate_acceptance_criteria(proposal),
            "labels": ["bounty", f"priority:{priority}", f"complexity:{complexity}"],
            "repo": self.repo,
        }
        self._current_spec = spec
        await self.transition_to(CellState.POSTING)

    async def _post_issue(self) -> None:
        """
        Post the bounty spec as a GitHub Issue.

        In production this uses the GitHub API / `gh` CLI.
        Here we simulate and publish for downstream cells.
        """
        if self._current_spec is None:
            await self.transition_to(CellState.IDLE)
            return

        issue_record = {
            **self._current_spec,
            "issue_number": len(self._posted_issues) + 1,
            "status": "open",
        }
        self._posted_issues.append(issue_record)
        self.publish("bounty_spec", issue_record)
        logger.info("[pm] posted bounty issue: %s", issue_record["title"])
        self._current_spec = None
        await self.transition_to(CellState.IDLE)

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _estimate_complexity(priority: str) -> str:
        mapping = {"critical": "large", "high": "medium", "medium": "small", "low": "trivial"}
        return mapping.get(priority, "medium")

    @staticmethod
    def _generate_acceptance_criteria(proposal: dict[str, Any]) -> list[str]:
        criteria = [
            "Implementation matches the spec description.",
            "All existing tests pass.",
            "New tests cover the added functionality.",
            "Code passes lint/format checks.",
        ]
        if proposal.get("priority") in ("critical", "high"):
            criteria.append("Performance benchmarks do not regress.")
        return criteria
