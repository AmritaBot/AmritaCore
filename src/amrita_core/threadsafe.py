import asyncio
import sys
import threading
from contextlib import nullcontext

from typing_extensions import Self

NO_GIL = sys.version_info >= (3, 13)


class NoneLock(nullcontext):
    """
    A lock-like object that does nothing.
    """

    def acquire(self):
        pass

    def release(self):
        pass

    def locked(self):
        return False


class AsyncLockThreadsafe:
    """
    A lock that provides mutual exclusion across both asyncio coroutines
    and multiple threads without blocking the event loop.

    This lock combines an asyncio.Lock for coroutine synchronization within
    the same thread and a threading.Lock for cross-thread synchronization.
    It automatically detects the execution context and uses the appropriate
    locking mechanism.

    Attributes:
        _async_lock: Protects coroutines within the same event loop thread.
        _thread_lock: Protects access across different threads.
        _meta_lock: Protects metadata attributes (_owner_thread_id and _is_thread_locked).
        _owner_thread_id: ID of the thread that currently owns the lock.
        _is_thread_locked: Flag indicating if the lock is held via threading.Lock.
    """

    def __init__(self) -> None:
        self._async_lock = asyncio.Lock()
        self._thread_lock = threading.Lock() if NO_GIL else NoneLock()
        self._meta_lock = threading.Lock()

        self._owner_thread_id: int | None = None
        self._is_thread_locked: bool = False

    async def acquire(self) -> None:
        """
        Acquire the lock from within a coroutine.

        If called from the same thread that previously acquired the lock,
        uses asyncio.Lock. If called from a different thread, delegates to
        threading.Lock via asyncio.to_thread to avoid blocking the event loop.

        The lock is bound to the event loop from which it is first acquired
        asynchronously.
        """
        current_tid = threading.get_ident()

        try:
            self._meta_lock.acquire()
            if self._owner_thread_id is None or self._owner_thread_id == current_tid:
                self._owner_thread_id = current_tid
                self._meta_lock.release()
                await self._async_lock.acquire()
            else:
                self._meta_lock.release()
                await asyncio.to_thread(self._thread_lock.acquire)
                self._meta_lock.acquire()
                self._owner_thread_id = current_tid
                self._is_thread_locked = True
                self._meta_lock.release()
        finally:
            if self._meta_lock.locked():
                self._meta_lock.release()

    def release(self) -> None:
        """
        Release the lock previously acquired by a coroutine.

        Releases either the asyncio.Lock or threading.Lock depending on how
        the lock was acquired.

        Raises:
            RuntimeError: If called from a thread that does not own the lock.
        """
        current_tid = threading.get_ident()
        if self._owner_thread_id != current_tid:
            raise RuntimeError("Lock released by non-owner thread")
        with self._meta_lock:
            if self._is_thread_locked:
                self._is_thread_locked = False
                self._thread_lock.release()
            else:
                self._async_lock.release()
            self._owner_thread_id = None

    async def __aenter__(self) -> Self:
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


class ContextThreadsafe:
    """
    Provides an optional async context manager for thread-safe operations.

    This class wraps AsyncLockThreadsafe to provide a convenient context manager
    interface for ensuring thread safety in async code.
    """

    _ctx_lock: AsyncLockThreadsafe

    def __init__(self):
        self._ctx_lock = AsyncLockThreadsafe()

    async def __aenter__(self):
        await self._ctx_lock.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._ctx_lock.release()
