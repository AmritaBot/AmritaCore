import asyncio
import sys
import threading

from typing_extensions import Self

NO_GIL = sys.version_info >= (3, 13)


class AsyncLockThreadsafe:
    """
    A lock that provides mutual exclusion across both asyncio coroutines
    and multiple threads.

    In Python 3.13+ free-threaded builds, it combines asyncio.Lock and
    threading.Lock with lightweight meta-data protection. In older GIL-enabled
    versions, it acts as a plain asyncio.Lock wrapper.
    """

    # In NO_GIL mode, these attributes are bound in __init__.
    _thread_lock: threading.Lock
    _meta_lock: threading.Lock
    _owner_thread_id: int | None
    _is_thread_locked: bool

    def __init__(self) -> None:
        self._async_lock = asyncio.Lock()
        if NO_GIL:
            self._thread_lock = threading.Lock()
            self._meta_lock = threading.Lock()
            self._owner_thread_id = None
            self._is_thread_locked = False

    async def acquire(self) -> None:
        """Acquire the lock from within a coroutine."""
        if not NO_GIL:
            await self._async_lock.acquire()
            return

        current_tid = threading.get_ident()
        with self._meta_lock:
            if self._owner_thread_id is None or self._owner_thread_id == current_tid:
                self._owner_thread_id = current_tid
                take_async = True
            else:
                take_async = False

        if take_async:
            await self._async_lock.acquire()
        else:
            await asyncio.to_thread(self._thread_lock.acquire)
            with self._meta_lock:
                self._owner_thread_id = current_tid
                self._is_thread_locked = True

    def release(self) -> None:
        """Release the lock."""
        if not NO_GIL:
            self._async_lock.release()
            return

        current_tid = threading.get_ident()
        with self._meta_lock:
            if self._owner_thread_id != current_tid:
                raise RuntimeError("Lock released by non-owner thread")
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
