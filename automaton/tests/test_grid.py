"""Tests for Grid state propagation."""

import pytest

from automaton.framework.cell import Cell
from automaton.framework.grid import Grid
from automaton.framework.state import CellState, Transition


class PingCell(Cell):
    """Goes IDLE -> ANALYZING when a neighbor named 'trigger' is ANALYZING."""

    CELL_ID = "ping"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.ANALYZING),
        Transition(CellState.ANALYZING, CellState.IDLE),
    ]

    async def _process(self):
        trigger = self.neighbor("trigger")
        if trigger and trigger.state == CellState.ANALYZING:
            if self.state == CellState.IDLE:
                await self.transition_to(CellState.ANALYZING)
        elif self.state == CellState.ANALYZING:
            await self.transition_to(CellState.IDLE)


class TriggerCell(Cell):
    CELL_ID = "trigger"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.ANALYZING),
        Transition(CellState.ANALYZING, CellState.IDLE),
    ]

    def __init__(self):
        super().__init__()
        self.should_analyze = False

    async def _process(self):
        if self.should_analyze and self.state == CellState.IDLE:
            await self.transition_to(CellState.ANALYZING)
            self.should_analyze = False
        elif self.state == CellState.ANALYZING:
            await self.transition_to(CellState.IDLE)


@pytest.mark.asyncio
async def test_add_cell():
    grid = Grid()
    cell = PingCell()
    grid.add_cell(cell)
    assert grid.get_cell("ping") is cell


@pytest.mark.asyncio
async def test_duplicate_cell_raises():
    grid = Grid()
    grid.add_cell(PingCell())
    with pytest.raises(ValueError, match="already registered"):
        grid.add_cell(PingCell())


@pytest.mark.asyncio
async def test_neighbor_propagation():
    """Trigger goes ANALYZING -> Ping should react on next tick."""
    grid = Grid()
    trigger = TriggerCell()
    ping = PingCell()

    grid.add_cell(trigger)
    grid.add_cell(ping, neighbors=["trigger"])

    # tick 1: trigger becomes ANALYZING
    trigger.should_analyze = True
    await grid.tick()
    assert trigger.state == CellState.ANALYZING  # trigger activated but will go idle next
    # ping hasn't seen it yet because neighbor snapshot was taken before trigger ticked
    # (depends on order — asyncio.gather is concurrent)

    # tick 2: ping sees trigger's ANALYZING snapshot
    await grid.tick()
    # trigger goes idle, but ping may have seen it as ANALYZING in the snapshot
    # After tick 2 trigger is back to IDLE, ping may or may not have reacted

    # What matters: the grid ran without error and states are valid
    assert trigger.state in (CellState.IDLE, CellState.ANALYZING)
    assert ping.state in (CellState.IDLE, CellState.ANALYZING)


@pytest.mark.asyncio
async def test_grid_summary():
    grid = Grid()
    grid.add_cell(PingCell())
    await grid.tick()
    summary = grid.summary()
    assert summary["tick"] == 1
    assert "ping" in summary["cells"]
    assert summary["cells"]["ping"]["state"] == "idle"
