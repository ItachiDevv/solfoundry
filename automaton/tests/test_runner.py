"""Tests for the Runner."""

import pytest

from automaton.framework.grid import Grid
from automaton.framework.runner import Runner
from automaton.framework.cell import Cell
from automaton.framework.state import CellState, Transition


class CounterCell(Cell):
    CELL_ID = "counter"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = []

    async def _process(self):
        pass  # just counts ticks via base class


@pytest.mark.asyncio
async def test_run_ticks():
    grid = Grid()
    cell = CounterCell()
    grid.add_cell(cell)

    runner = Runner(grid, tick_interval=0.01)
    await runner.run_ticks(5)

    assert cell.tick_count == 5
    assert grid.tick_count == 5


@pytest.mark.asyncio
async def test_runner_stop():
    grid = Grid()
    grid.add_cell(CounterCell())
    runner = Runner(grid, tick_interval=0.01)
    assert not runner.running
    runner.stop()  # should be safe even when not running
