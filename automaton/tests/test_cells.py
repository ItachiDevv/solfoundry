"""Tests for each cell's state transitions and core logic."""

import pytest

from automaton.framework.state import CellState, NeighborSnapshot
from automaton.cells.director import DirectorCell
from automaton.cells.pm import PMCell
from automaton.cells.review import ReviewCell
from automaton.cells.treasury import TreasuryCell
from automaton.cells.social import SocialCell
from automaton.cells.integration import IntegrationCell


# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------

class TestDirectorCell:
    @pytest.mark.asyncio
    async def test_idle_without_signals(self):
        cell = DirectorCell()
        await cell.tick()
        assert cell.state == CellState.IDLE

    @pytest.mark.asyncio
    async def test_low_priority_signal_returns_idle(self):
        cell = DirectorCell()
        cell.ingest_signal({"type": "bug", "priority": "low", "title": "minor"})
        # tick 1: idle -> analyzing
        await cell.tick()
        assert cell.state == CellState.ANALYZING
        # tick 2: analyzing -> idle (low priority, no proposal)
        await cell.tick()
        assert cell.state == CellState.IDLE
        assert cell.payload.get("proposal") is None

    @pytest.mark.asyncio
    async def test_high_priority_creates_proposal(self):
        cell = DirectorCell()
        cell.ingest_signal({
            "type": "feature",
            "priority": "high",
            "title": "Add staking",
            "description": "Implement staking module",
        })
        # tick 1: idle -> analyzing
        await cell.tick()
        assert cell.state == CellState.ANALYZING
        # tick 2: analyzing -> proposing
        await cell.tick()
        assert cell.state == CellState.PROPOSING
        # tick 3: proposing -> idle (publishes)
        await cell.tick()
        assert cell.state == CellState.IDLE
        assert cell.payload.get("proposal") is not None
        assert cell.payload["proposal"]["title"] == "Add staking"


# ---------------------------------------------------------------------------
# PM
# ---------------------------------------------------------------------------

class TestPMCell:
    @pytest.mark.asyncio
    async def test_idle_without_director(self):
        cell = PMCell()
        await cell.tick()
        assert cell.state == CellState.IDLE

    @pytest.mark.asyncio
    async def test_decomposes_director_proposal(self):
        cell = PMCell()
        # Inject director neighbor with a proposal
        director_snap = NeighborSnapshot(
            cell_id="director",
            state=CellState.IDLE,
            tick=3,
            payload={"proposal": {
                "title": "Add staking",
                "description": "Implement staking",
                "priority": "high",
            }},
        )
        cell.receive_neighbor_states({"director": director_snap})

        # tick 1: idle -> decomposing
        await cell.tick()
        assert cell.state == CellState.DECOMPOSING

        # tick 2: decomposing -> posting
        await cell.tick()
        assert cell.state == CellState.POSTING

        # tick 3: posting -> idle
        await cell.tick()
        assert cell.state == CellState.IDLE
        assert len(cell.posted_issues) == 1
        issue = cell.posted_issues[0]
        assert issue["title"] == "[Bounty] Add staking"
        assert "acceptance_criteria" in issue


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

class TestReviewCell:
    @pytest.mark.asyncio
    async def test_idle_without_submissions(self):
        cell = ReviewCell()
        await cell.tick()
        assert cell.state == CellState.IDLE

    @pytest.mark.asyncio
    async def test_full_review_cycle(self):
        cell = ReviewCell()
        cell.submit_for_review({"pr_number": 42, "diff": "..."})

        # tick 1: idle -> reviewing
        await cell.tick()
        assert cell.state == CellState.REVIEWING

        # tick 2: reviewing -> aggregating
        await cell.tick()
        assert cell.state == CellState.AGGREGATING

        # tick 3: aggregating -> idle
        await cell.tick()
        assert cell.state == CellState.IDLE
        assert len(cell.verdicts) == 1
        assert cell.verdicts[0]["approved"] is True
        assert cell.verdicts[0]["total_reviews"] == 3


# ---------------------------------------------------------------------------
# Treasury
# ---------------------------------------------------------------------------

class TestTreasuryCell:
    @pytest.mark.asyncio
    async def test_idle_without_bounty(self):
        cell = TreasuryCell()
        await cell.tick()
        assert cell.state == CellState.IDLE

    @pytest.mark.asyncio
    async def test_escrow_on_bounty_spec(self):
        cell = TreasuryCell(initial_reserves=100.0)
        pm_snap = NeighborSnapshot(
            cell_id="pm",
            state=CellState.IDLE,
            tick=1,
            payload={"bounty_spec": {
                "issue_number": 1,
                "complexity": "medium",
                "priority": "high",
            }},
        )
        cell.receive_neighbor_states({"pm": pm_snap})

        # tick 1: idle -> calculating
        await cell.tick()
        assert cell.state == CellState.CALCULATING

        # tick 2: calculating -> paying (escrow)
        await cell.tick()
        assert cell.state == CellState.PAYING
        assert 1 in cell.escrow

        # tick 3: paying -> idle
        await cell.tick()
        assert cell.state == CellState.IDLE
        assert cell.reserves < 100.0

    @pytest.mark.asyncio
    async def test_payout(self):
        cell = TreasuryCell(initial_reserves=100.0)
        # Manually escrow funds
        cell._reserves -= 5.0
        cell._escrow[1] = 5.0

        cell.request_payout(1, "contributor123")

        # tick 1: idle -> calculating (payout request)
        await cell.tick()
        assert cell.state == CellState.CALCULATING

        # tick 2: calculating -> paying
        await cell.tick()
        assert cell.state == CellState.PAYING

        # tick 3: paying -> idle
        await cell.tick()
        assert cell.state == CellState.IDLE
        assert len(cell.payouts) == 1
        assert cell.payouts[0]["amount"] == 5.0
        assert cell.payouts[0]["recipient"] == "contributor123"


# ---------------------------------------------------------------------------
# Social
# ---------------------------------------------------------------------------

class TestSocialCell:
    @pytest.mark.asyncio
    async def test_idle_without_events(self):
        cell = SocialCell()
        await cell.tick()
        assert cell.state == CellState.IDLE

    @pytest.mark.asyncio
    async def test_announce_new_bounty(self):
        cell = SocialCell()
        pm_snap = NeighborSnapshot(
            cell_id="pm",
            state=CellState.IDLE,
            tick=1,
            payload={"bounty_spec": {
                "title": "[Bounty] Add staking",
                "complexity": "medium",
                "labels": ["bounty"],
            }},
        )
        cell.receive_neighbor_states({"pm": pm_snap})

        # tick 1: idle -> announcing
        await cell.tick()
        assert cell.state == CellState.ANNOUNCING

        # tick 2: announcing -> monitoring
        await cell.tick()
        assert cell.state == CellState.MONITORING

        # tick 3: monitoring -> idle
        await cell.tick()
        assert cell.state == CellState.IDLE
        assert len(cell.announcements) == 1
        assert "SolFoundry" in cell.announcements[0]["tweet"]


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestIntegrationCell:
    @pytest.mark.asyncio
    async def test_idle_without_prs(self):
        cell = IntegrationCell()
        await cell.tick()
        assert cell.state == CellState.IDLE

    @pytest.mark.asyncio
    async def test_full_merge_cycle(self):
        cell = IntegrationCell()
        cell.submit_pr({"pr_number": 99})

        # tick 1: idle -> checking
        await cell.tick()
        assert cell.state == CellState.CHECKING

        # tick 2: checking -> merging
        await cell.tick()
        assert cell.state == CellState.MERGING

        # tick 3: merging -> idle
        await cell.tick()
        assert cell.state == CellState.IDLE
        assert len(cell.merge_log) == 1
        assert cell.merge_log[0]["pr_number"] == 99
        assert cell.merge_log[0]["merged"] is True

    @pytest.mark.asyncio
    async def test_reacts_to_review_verdict(self):
        cell = IntegrationCell()
        review_snap = NeighborSnapshot(
            cell_id="review",
            state=CellState.IDLE,
            tick=1,
            payload={
                "verdict": {"approved": True},
                "submission": {"pr_number": 55},
            },
        )
        cell.receive_neighbor_states({"review": review_snap})

        # tick 1: idle -> checking
        await cell.tick()
        assert cell.state == CellState.CHECKING
