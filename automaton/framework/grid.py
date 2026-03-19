"""
Grid — manages all cells, propagates neighbor state, and drives ticks.

The grid is the "world" in which cells live.  Each tick it:
  1. Broadcasts neighbor snapshots to every cell.
  2. Calls `cell.tick()` on every cell (concurrently).
  3. Collects new snapshots for the next round.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .cell import Cell
from .state import NeighborSnapshot

logger = logging.getLogger(__name__)


class Grid:
    """Manages the lifecycle and communication of automaton cells."""

    def __init__(self) -> None:
        self._cells: dict[str, Cell] = {}
        self._adjacency: dict[str, list[str]] = {}  # cell_id -> [neighbor_ids]
        self._tick_count: int = 0

    # -- registration ---------------------------------------------------------

    def add_cell(self, cell: Cell, neighbors: list[str] | None = None) -> None:
        """Register a cell and its neighbor list."""
        if cell.CELL_ID in self._cells:
            raise ValueError(f"Cell '{cell.CELL_ID}' already registered")
        self._cells[cell.CELL_ID] = cell
        self._adjacency[cell.CELL_ID] = neighbors or []
        logger.info("Grid: registered cell '%s'", cell.CELL_ID)

    def get_cell(self, cell_id: str) -> Cell | None:
        return self._cells.get(cell_id)

    @property
    def cells(self) -> dict[str, Cell]:
        return dict(self._cells)

    @property
    def tick_count(self) -> int:
        return self._tick_count

    # -- neighbor state propagation -------------------------------------------

    def _build_neighbor_map(self, cell_id: str) -> dict[str, NeighborSnapshot]:
        """Collect snapshots from a cell's declared neighbors."""
        result: dict[str, NeighborSnapshot] = {}
        for nid in self._adjacency.get(cell_id, []):
            neighbor = self._cells.get(nid)
            if neighbor is not None:
                result[nid] = neighbor.snapshot()
        return result

    # -- tick -----------------------------------------------------------------

    async def tick(self) -> None:
        """
        Run one global tick:
          1. Push neighbor snapshots.
          2. Run all cells concurrently.
        """
        self._tick_count += 1
        logger.debug("Grid tick %d — propagating state", self._tick_count)

        # 1. propagate
        for cid, cell in self._cells.items():
            cell.receive_neighbor_states(self._build_neighbor_map(cid))

        # 2. tick all cells concurrently
        await asyncio.gather(*(cell.tick() for cell in self._cells.values()))

        logger.debug("Grid tick %d complete", self._tick_count)

    # -- introspection --------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a JSON-serialisable summary of the grid."""
        return {
            "tick": self._tick_count,
            "cells": {
                cid: {
                    "state": cell.state.value,
                    "tick": cell.tick_count,
                    "payload": cell.payload,
                }
                for cid, cell in self._cells.items()
            },
        }
