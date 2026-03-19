"""
Base Cell class — the building block of the management automaton.

Every cell owns:
  * a finite state machine (allowed transitions)
  * a neighbor list (other cell IDs it can observe)
  * a tick() coroutine invoked each automaton cycle
  * a payload dict for publishing data to neighbors
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from .state import CellState, NeighborSnapshot, Transition, validate_transition

logger = logging.getLogger(__name__)


class Cell(ABC):
    """Abstract base for every automaton cell."""

    # Subclasses MUST override -----------------------------------------------
    CELL_ID: str = ""
    ALLOWED_TRANSITIONS: list[Transition] = []
    INITIAL_STATE: CellState = CellState.IDLE

    def __init__(self) -> None:
        self._state: CellState = self.INITIAL_STATE
        self._tick_count: int = 0
        self._payload: dict[str, Any] = {}
        self._neighbors: dict[str, NeighborSnapshot] = {}
        self._lock = asyncio.Lock()

    # -- public API -----------------------------------------------------------

    @property
    def state(self) -> CellState:
        return self._state

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def payload(self) -> dict[str, Any]:
        """Read-only copy of the cell's published data."""
        return dict(self._payload)

    def snapshot(self) -> NeighborSnapshot:
        """Create a snapshot of this cell for neighbor consumption."""
        return NeighborSnapshot(
            cell_id=self.CELL_ID,
            state=self._state,
            tick=self._tick_count,
            payload=dict(self._payload),
        )

    # -- state machine --------------------------------------------------------

    async def transition_to(self, target: CellState) -> None:
        """
        Attempt to move to *target* state.

        Raises ValueError if the transition is not allowed.
        """
        async with self._lock:
            if target == self._state:
                return
            if not validate_transition(self.ALLOWED_TRANSITIONS, self._state, target):
                raise ValueError(
                    f"[{self.CELL_ID}] invalid transition: "
                    f"{self._state.value} -> {target.value}"
                )
            old = self._state
            self._state = target
            logger.info(
                "[%s] %s -> %s (tick %d)",
                self.CELL_ID,
                old.value,
                target.value,
                self._tick_count,
            )

    # -- neighbor awareness ---------------------------------------------------

    def receive_neighbor_states(
        self, snapshots: dict[str, NeighborSnapshot]
    ) -> None:
        """Called by the Grid before each tick to inject neighbor state."""
        self._neighbors = dict(snapshots)

    def neighbor(self, cell_id: str) -> NeighborSnapshot | None:
        return self._neighbors.get(cell_id)

    # -- tick loop ------------------------------------------------------------

    async def tick(self) -> None:
        """
        One automaton cycle.  The Grid calls this once per tick.

        Delegates to the subclass `_process` method, catches errors, and
        transitions to ERROR if anything goes wrong.
        """
        self._tick_count += 1
        try:
            await self._process()
        except Exception:
            logger.exception("[%s] error during tick %d", self.CELL_ID, self._tick_count)
            # force into error state (always allowed)
            self._state = CellState.ERROR

    @abstractmethod
    async def _process(self) -> None:
        """Subclass-specific logic executed every tick."""

    # -- payload helpers ------------------------------------------------------

    def publish(self, key: str, value: Any) -> None:
        """Set a key in the cell's public payload."""
        self._payload[key] = value

    def clear_payload(self) -> None:
        self._payload.clear()
