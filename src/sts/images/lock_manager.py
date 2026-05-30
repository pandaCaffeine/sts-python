from typing import Generator
from contextlib import contextmanager
from threading import Lock


class LockManager:
    """
    Manages thread-safe locks with automatic cleanup.

    Provides a context-manager based API for acquiring per-key locks.
    Locks are automatically removed from memory after the protected
    block is exited, preventing memory leaks under high concurrency.
    """

    def __init__(self):
        self._locks: dict[str, Lock] = {}
        self._meta_lock = Lock()

    @contextmanager
    def acquire(self, key: str) -> Generator[None, None, None]:
        """
        Acquire a lock identified by the given key.

        Uses a context manager to ensure the lock is released and cleaned up
        automatically, even if an exception occurs within the protected block.

        Args:
            key: Unique identifier for the lock. Threads calling acquire with
                 the same key will block each other; different keys allow
                 parallel execution.
        """
        with self._meta_lock:
            file_lock = self._locks.setdefault(key, Lock())

        try:
            with file_lock:
                yield
        finally:
            with self._meta_lock:
                self._locks.pop(key, None)
