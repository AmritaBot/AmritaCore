import asyncio


class ContextThreadsafe:
    """Add a optional async-context lock for thread-safe in python 3.14+ (No GIL versions)"""

    _ctx_lock: asyncio.Lock

    def __init_subclass__(cls) -> None:
        cls._ctx_lock = asyncio.Lock()

    async def __aenter__(self):
        await self._ctx_lock.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._ctx_lock.release()
