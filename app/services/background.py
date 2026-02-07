from __future__ import annotations

import asyncio
import contextlib
import logging

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Base class for services that run a periodic background loop."""

    def __init__(self, *, interval: float, name: str) -> None:
        self._interval = interval
        self._name = name
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        await self._on_start()
        self._task = asyncio.create_task(self._loop(), name=self._name)
        logger.info("%s started (every %ds)", self._name, self._interval)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
            logger.info("%s stopped", self._name)

    async def _on_start(self) -> None:
        pass

    async def _tick(self) -> None:
        raise NotImplementedError

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                await self._tick()
            except Exception:
                logger.exception("%s tick failed — will retry", self._name)
