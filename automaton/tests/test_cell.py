"""Tests for the base Cell class."""

import pytest
import asyncio

from automaton.framework.cell import Cell
from automaton.framework.state import CellState, Transition, NeighborSnapshot


class DummyCell(Cell):
    """Minimal cell for testing the base class."""

    CELL_ID = "dummy"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = [
        Transition(CellState.IDLE, CellState.ANALYZING),
        Transition(CellState.ANALYZING, CellState.IDLE),
    ]

    def __init__(self):
        super().__init__()
        self.process_count = 0

    async def _process(self):
        self.process_count += 1


class ErrorCell(Cell):
    """Cell that always raises in _process."""

    CELL_ID = "error_cell"
    INITIAL_STATE = CellState.IDLE
    ALLOWED_TRANSITIONS = []

    async def _process(self):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_initial_state():
    cell = DummyCell()
    assert cell.state == CellState.IDLE
    assert cell.tick_count == 0


@pytest.mark.asyncio
async def test_transition():
    cell = DummyCell()
    await cell.transition_to(CellState.ANALYZING)
    assert cell.state == CellState.ANALYZING


@pytest.mark.asyncio
async def test_invalid_transition():
    cell = DummyCell()
    with pytest.raises(ValueError, match="invalid transition"):
        await cell.transition_to(CellState.POSTING)


@pytest.mark.asyncio
async def test_tick_increments():
    cell = DummyCell()
    await cell.tick()
    assert cell.tick_count == 1
    assert cell.process_count == 1
    await cell.tick()
    assert cell.tick_count == 2


@pytest.mark.asyncio
async def test_error_in_process():
    cell = ErrorCell()
    await cell.tick()
    assert cell.state == CellState.ERROR


@pytest.mark.asyncio
async def test_snapshot():
    cell = DummyCell()
    cell.publish("foo", "bar")
    snap = cell.snapshot()
    assert snap.cell_id == "dummy"
    assert snap.state == CellState.IDLE
    assert snap.payload == {"foo": "bar"}


@pytest.mark.asyncio
async def test_neighbor_awareness():
    cell = DummyCell()
    snap = NeighborSnapshot(cell_id="other", state=CellState.ANALYZING, tick=1)
    cell.receive_neighbor_states({"other": snap})
    assert cell.neighbor("other") is not None
    assert cell.neighbor("other").state == CellState.ANALYZING
    assert cell.neighbor("missing") is None


@pytest.mark.asyncio
async def test_same_state_transition_noop():
    cell = DummyCell()
    await cell.transition_to(CellState.IDLE)  # should not raise
    assert cell.state == CellState.IDLE
