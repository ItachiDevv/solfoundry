"""Tests for state management (state.py)."""

import pytest

from automaton.framework.state import (
    CellState,
    NeighborSnapshot,
    Transition,
    validate_transition,
)


def test_cell_state_values():
    assert CellState.IDLE.value == "idle"
    assert CellState.ERROR.value == "error"


def test_transition_equality():
    t = Transition(CellState.IDLE, CellState.ANALYZING, "test")
    assert t.from_state == CellState.IDLE
    assert t.to_state == CellState.ANALYZING


def test_validate_transition_allowed():
    allowed = [
        Transition(CellState.IDLE, CellState.ANALYZING),
        Transition(CellState.ANALYZING, CellState.IDLE),
    ]
    assert validate_transition(allowed, CellState.IDLE, CellState.ANALYZING)
    assert validate_transition(allowed, CellState.ANALYZING, CellState.IDLE)


def test_validate_transition_blocked():
    allowed = [Transition(CellState.IDLE, CellState.ANALYZING)]
    assert not validate_transition(allowed, CellState.ANALYZING, CellState.IDLE)
    assert not validate_transition(allowed, CellState.IDLE, CellState.POSTING)


def test_neighbor_snapshot():
    snap = NeighborSnapshot(
        cell_id="test",
        state=CellState.IDLE,
        tick=5,
        payload={"key": "val"},
    )
    assert snap.cell_id == "test"
    assert snap.state == CellState.IDLE
    assert snap.tick == 5
    assert snap.payload == {"key": "val"}
