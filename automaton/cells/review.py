"""
Review Cell — coordinates the multi-LLM review pipeline.

Triggers GPT-5.4, Gemini, and Grok reviews in parallel.
Aggregates results and posts a verdict.

States: idle -> reviewing -> aggregating -> idle
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from automaton.framework.cell import Cell
from automaton.framework.state import CellState, Transition

logger = logging.getLogger(__name__)

# Models used in the review pipeline
REVIEW_MODELS = ["gpt-5.4", "gemini-2.5-pro", "grok-3"]


class ReviewCell(Cell):
    CELL_ID = "review"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.REVIEWING, "submission received"),
        Transition(CellState.REVIEWING, CellState.AGGREGATING, "all reviews in"),
        Transition(CellState.AGGREGATING, CellState.IDLE, "verdict published"),
        # recovery
        Transition(CellState.REVIEWING, CellState.IDLE, "review cancelled"),
        Transition(CellState.AGGREGATING, CellState.IDLE, "aggregation cancelled"),
        Transition(CellState.ERROR, CellState.IDLE, "error recovery"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._pending_submissions: list[dict[str, Any]] = []
        self._current_reviews: dict[str, dict[str, Any]] = {}
        self._verdicts: list[dict[str, Any]] = []

    @property
    def verdicts(self) -> list[dict[str, Any]]:
        return list(self._verdicts)

    def submit_for_review(self, submission: dict[str, Any]) -> None:
        """Queue a PR / code submission for multi-LLM review."""
        self._pending_submissions.append(submission)

    # -- tick logic -----------------------------------------------------------

    async def _process(self) -> None:
        if self.state == CellState.IDLE:
            await self._check_submissions()
        elif self.state == CellState.REVIEWING:
            await self._run_reviews()
        elif self.state == CellState.AGGREGATING:
            await self._aggregate()

    async def _check_submissions(self) -> None:
        if self._pending_submissions:
            await self.transition_to(CellState.REVIEWING)

    async def _run_reviews(self) -> None:
        """
        Fan out review requests to all configured LLM models in parallel.

        In production each coroutine calls the respective model API.
        Here we simulate with a lightweight stub.
        """
        submission = self._pending_submissions.pop(0)

        async def _review_with(model: str) -> dict[str, Any]:
            # simulate latency
            await asyncio.sleep(0)
            return {
                "model": model,
                "approved": True,
                "comments": [f"Reviewed by {model}: looks good."],
                "score": 0.9,
            }

        results = await asyncio.gather(*[_review_with(m) for m in REVIEW_MODELS])
        self._current_reviews = {r["model"]: r for r in results}
        self.publish("submission", submission)
        await self.transition_to(CellState.AGGREGATING)

    async def _aggregate(self) -> None:
        """Combine individual model reviews into a single verdict."""
        reviews = self._current_reviews
        approval_count = sum(1 for r in reviews.values() if r.get("approved"))
        total = len(reviews)

        verdict: dict[str, Any] = {
            "approved": approval_count > total / 2,  # majority vote
            "approval_count": approval_count,
            "total_reviews": total,
            "reviews": reviews,
            "summary": (
                "Approved by majority"
                if approval_count > total / 2
                else "Rejected by majority"
            ),
        }
        self._verdicts.append(verdict)
        self.publish("verdict", verdict)
        self._current_reviews = {}
        logger.info("[review] verdict: %s (%d/%d)", verdict["summary"], approval_count, total)
        await self.transition_to(CellState.IDLE)
