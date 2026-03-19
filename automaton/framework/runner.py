"""
Runner — main loop driving the automaton with a configurable tick interval.

Usage:
    runner = Runner(grid, tick_interval=5.0)
    await runner.start()   # runs until cancelled
    runner.stop()
"""

from __future__ import annotations

import asyncio
import logging

from .grid import Grid

logger = logging.getLogger(__name__)


class Runner:
    """Drives the Grid tick loop at a fixed interval."""

    def __init__(self, grid: Grid, tick_interval: float = 10.0) -> None:
        self.grid = grid
        self.tick_interval = tick_interval
        self._running = False
        self._task: asyncio.Task[None] | None = None

    # -- control --------------------------------------------------------------

    async def start(self) -> None:
        """Start the tick loop.  Blocks until `stop()` is called."""
        self._running = True
        logger.info(
            "Runner starting (interval=%.1fs, cells=%d)",
            self.tick_interval,
            len(self.grid.cells),
        )
        try:
            while self._running:
                await self.grid.tick()
                await asyncio.sleep(self.tick_interval)
        except asyncio.CancelledError:
            logger.info("Runner cancelled")
        finally:
            self._running = False
            logger.info("Runner stopped")

    def stop(self) -> None:
        """Signal the runner to stop after the current tick completes."""
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    # -- convenience ----------------------------------------------------------

    def launch(self) -> asyncio.Task[None]:
        """Schedule `start()` as a background task on the current event loop."""
        self._task = asyncio.create_task(self.start())
        return self._task

    async def run_ticks(self, n: int) -> None:
        """Run exactly *n* ticks (useful for testing / scripted runs)."""
        for _ in range(n):
            await self.grid.tick()
