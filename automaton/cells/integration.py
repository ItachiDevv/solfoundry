"""
Integration Cell — CI/CD pipeline coordinator.

Runs CI/CD checks on submissions.
Validates PR meets acceptance criteria.
Triggers merge on approval.

States: idle -> checking -> merging -> idle
"""

from __future__ import annotations

import logging
from typing import Any

from automaton.framework.cell import Cell
from automaton.framework.state import CellState, Transition

logger = logging.getLogger(__name__)


class IntegrationCell(Cell):
    CELL_ID = "integration"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.CHECKING, "submission to check"),
        Transition(CellState.CHECKING, CellState.MERGING, "all checks passed"),
        Transition(CellState.CHECKING, CellState.IDLE, "checks failed"),
        Transition(CellState.MERGING, CellState.IDLE, "merge complete"),
        # recovery
        Transition(CellState.MERGING, CellState.IDLE, "merge cancelled"),
        Transition(CellState.ERROR, CellState.IDLE, "error recovery"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._pending_prs: list[dict[str, Any]] = []
        self._check_results: list[dict[str, Any]] = []
        self._merge_log: list[dict[str, Any]] = []
        self._current_pr: dict[str, Any] | None = None

    @property
    def merge_log(self) -> list[dict[str, Any]]:
        return list(self._merge_log)

    def submit_pr(self, pr: dict[str, Any]) -> None:
        """Queue a pull request for CI/CD checking."""
        self._pending_prs.append(pr)

    # -- tick logic -----------------------------------------------------------

    async def _process(self) -> None:
        if self.state == CellState.IDLE:
            await self._check_queue()
        elif self.state == CellState.CHECKING:
            await self._run_checks()
        elif self.state == CellState.MERGING:
            await self._merge()

    async def _check_queue(self) -> None:
        """Watch for new PRs or review verdicts."""
        review = self.neighbor("review")
        if review and review.payload.get("verdict"):
            verdict = review.payload["verdict"]
            if verdict.get("approved"):
                submission = review.payload.get("submission", {})
                self._current_pr = {
                    "pr_number": submission.get("pr_number", 0),
                    "verdict": verdict,
                    "submission": submission,
                }
                await self.transition_to(CellState.CHECKING)
                return

        if self._pending_prs:
            self._current_pr = self._pending_prs.pop(0)
            await self.transition_to(CellState.CHECKING)

    async def _run_checks(self) -> None:
        """
        Run CI/CD checks against the PR.

        In production this triggers GitHub Actions and polls for results.
        Here we simulate passing checks.
        """
        if self._current_pr is None:
            await self.transition_to(CellState.IDLE)
            return

        checks = {
            "lint": True,
            "test": True,
            "build": True,
            "security_scan": True,
        }
        all_passed = all(checks.values())

        result = {
            "pr_number": self._current_pr.get("pr_number", 0),
            "checks": checks,
            "all_passed": all_passed,
        }
        self._check_results.append(result)
        self.publish("check_result", result)

        if all_passed:
            logger.info("[integration] all checks passed for PR #%d", result["pr_number"])
            await self.transition_to(CellState.MERGING)
        else:
            logger.warning("[integration] checks failed for PR #%d", result["pr_number"])
            self._current_pr = None
            await self.transition_to(CellState.IDLE)

    async def _merge(self) -> None:
        """
        Merge the PR.

        In production this calls the GitHub API to merge.
        Here we simulate and log.
        """
        if self._current_pr is None:
            await self.transition_to(CellState.IDLE)
            return

        merge_record = {
            "pr_number": self._current_pr.get("pr_number", 0),
            "merged": True,
            "method": "squash",
        }
        self._merge_log.append(merge_record)
        self.publish("merge", merge_record)
        logger.info("[integration] merged PR #%d", merge_record["pr_number"])
        self._current_pr = None
        await self.transition_to(CellState.IDLE)
