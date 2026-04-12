import aiologic


class ContextThreadsafe:
    """
    Provides an optional async context manager for thread-safe operations.

    This class wraps aiologic.Lock to provide a convenient context manager
    interface for ensuring thread safety in async code.
    """

    _ctx_lock: aiologic.Lock

    def __init__(self):
        self._ctx_lock = aiologic.Lock()

    async def __aenter__(self):
        await self._ctx_lock.async_acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self._ctx_lock.async_release()
