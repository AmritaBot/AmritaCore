import asyncio


class ContextThreadsafe:
    """Add a optional async-context lock for thread-safe."""

    _lock = asyncio.Lock()

    async def __aenter__(self):
        await self._lock.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()
