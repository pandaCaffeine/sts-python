from typing import Generator
from contextlib import contextmanager
from threading import Lock


class LockManager:
    """
    Manages thread-safe locks with automatic cleanup.

    Provides a context-manager based API for acquiring per-key locks.
    Locks are reference-counted: a lock object stays the same for all
    waiters of a key and is removed from memory only after the last
    holder/waiter leaves, which both prevents memory leaks and keeps
    mutual exclusion intact under concurrency.
    """

    def __init__(self):
        self._locks: dict[str, Lock] = {}
        self._ref_counts: dict[str, int] = {}
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
            file_lock = self._locks.get(key)
            if file_lock is None:
                file_lock = Lock()
                self._locks[key] = file_lock
            self._ref_counts[key] = self._ref_counts.get(key, 0) + 1

        try:
            with file_lock:
                yield
        finally:
            with self._meta_lock:
                remaining = self._ref_counts.get(key, 0) - 1
                if remaining <= 0:
                    self._ref_counts.pop(key, None)
                    self._locks.pop(key, None)
                else:
                    self._ref_counts[key] = remaining
