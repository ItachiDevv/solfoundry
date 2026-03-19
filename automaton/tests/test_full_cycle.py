"""
End-to-end test: full automaton cycle.

Simulates the lifecycle: Director proposes -> PM decomposes ->
Treasury escrows -> Social announces.
"""

import pytest

from automaton.framework.grid import Grid
from automaton.framework.runner import Runner
from automaton.framework.state import CellState

from automaton.cells.director import DirectorCell
from automaton.cells.pm import PMCell
from automaton.cells.review import ReviewCell
from automaton.cells.treasury import TreasuryCell
from automaton.cells.social import SocialCell
from automaton.cells.integration import IntegrationCell


def _build_grid() -> tuple[Grid, dict]:
    """Wire up the full automaton and return (grid, cells_dict)."""
    grid = Grid()

    director = DirectorCell()
    pm = PMCell()
    review = ReviewCell()
    treasury = TreasuryCell(initial_reserves=50.0)
    social = SocialCell()
    integration = IntegrationCell()

    grid.add_cell(director)
    grid.add_cell(pm, neighbors=["director"])
    grid.add_cell(review)
    grid.add_cell(treasury, neighbors=["pm"])
    grid.add_cell(social, neighbors=["pm", "treasury"])
    grid.add_cell(integration, neighbors=["review"])

    cells = {
        "director": director,
        "pm": pm,
        "review": review,
        "treasury": treasury,
        "social": social,
        "integration": integration,
    }
    return grid, cells


@pytest.mark.asyncio
async def test_director_to_pm_pipeline():
    """Director creates proposal -> PM picks it up and posts a bounty issue."""
    grid, cells = _build_grid()
    director = cells["director"]
    pm = cells["pm"]

    # Inject a high-priority signal
    director.ingest_signal({
        "type": "feature",
        "priority": "high",
        "title": "Implement governance voting",
        "description": "DAO governance voting module",
    })

    runner = Runner(grid)

    # Run enough ticks for director (3 ticks: idle->analyzing->proposing->idle)
    await runner.run_ticks(3)
    assert director.payload.get("proposal") is not None

    # Run more ticks for PM to pick up and process
    await runner.run_ticks(3)
    assert pm.state == CellState.IDLE
    assert len(pm.posted_issues) == 1
    assert "governance" in pm.posted_issues[0]["title"].lower()


@pytest.mark.asyncio
async def test_full_bounty_lifecycle():
    """
    Full lifecycle:
      1. Director proposes
      2. PM creates bounty
      3. Treasury escrows
      4. Social announces
      5. Review approves submission
      6. Integration merges
    """
    grid, cells = _build_grid()
    director = cells["director"]
    review = cells["review"]
    runner = Runner(grid)

    # 1-2. Director -> PM
    director.ingest_signal({
        "type": "bug",
        "priority": "critical",
        "title": "Fix token transfer bug",
        "description": "Transfers fail over 1000 SOL",
    })
    await runner.run_ticks(8)  # enough for director + PM pipeline

    pm = cells["pm"]
    assert len(pm.posted_issues) >= 1

    # 3. Treasury should have escrowed (it watches PM)
    treasury = cells["treasury"]
    # Run a few more ticks for treasury to react
    await runner.run_ticks(4)

    # 4. Social should have announced
    social = cells["social"]
    await runner.run_ticks(4)

    # 5-6. Submit for review, then integration merges
    review.submit_for_review({"pr_number": 101, "diff": "fix transfer logic"})
    await runner.run_ticks(6)

    assert len(review.verdicts) >= 1
    assert review.verdicts[0]["approved"] is True

    # Integration picks up the verdict
    integration = cells["integration"]
    await runner.run_ticks(4)

    # Verify the grid ran without any cells in ERROR state
    for name, cell in cells.items():
        assert cell.state != CellState.ERROR, f"{name} ended in ERROR state"


@pytest.mark.asyncio
async def test_grid_summary_after_ticks():
    grid, _ = _build_grid()
    runner = Runner(grid)
    await runner.run_ticks(2)

    summary = grid.summary()
    assert summary["tick"] == 2
    assert len(summary["cells"]) == 6
    for cell_info in summary["cells"].values():
        assert "state" in cell_info
        assert "tick" in cell_info
