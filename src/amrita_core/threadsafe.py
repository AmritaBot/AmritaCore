import threading
from abc import ABC


class ContextThreadsafe(ABC):
    _ctx_lock: threading.Lock  # Thread-safe for python 3.14+ (No GIL versions)

    def __init_subclass__(cls) -> None:
        cls._ctx_lock = threading.Lock()

    async def __aenter__(self):
        self._ctx_lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._ctx_lock.release()

    def __enter__(self):
        self._ctx_lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ctx_lock.release()
