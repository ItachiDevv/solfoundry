"""
State management for the cellular automaton.

Defines the CellState enum, transition rules, and neighbor-state protocol
used by every cell in the grid.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class CellState(str, enum.Enum):
    """Universal states shared by all cell types."""

    IDLE = "idle"
    ANALYZING = "analyzing"
    PROPOSING = "proposing"
    DECOMPOSING = "decomposing"
    POSTING = "posting"
    REVIEWING = "reviewing"
    AGGREGATING = "aggregating"
    CALCULATING = "calculating"
    PAYING = "paying"
    ANNOUNCING = "announcing"
    MONITORING = "monitoring"
    CHECKING = "checking"
    MERGING = "merging"
    ERROR = "error"


@dataclass(frozen=True)
class Transition:
    """Represents a valid state transition for a cell."""

    from_state: CellState
    to_state: CellState
    condition: str = ""  # human-readable description of when this fires


@dataclass
class NeighborSnapshot:
    """Immutable snapshot of a neighbor cell's public state at a given tick."""

    cell_id: str
    state: CellState
    tick: int
    payload: dict[str, Any] = field(default_factory=dict)


def validate_transition(
    allowed: list[Transition],
    current: CellState,
    target: CellState,
) -> bool:
    """Return True if *current -> target* is in the allowed transition list."""
    return any(
        t.from_state == current and t.to_state == target for t in allowed
    )
