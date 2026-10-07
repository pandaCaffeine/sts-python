from typing import Generator
from contextlib import contextmanager
from threading import Lock


class _CountedLock:
    """A lock with a waiter counter.

    Not thread-safe: the counter must only be mutated while holding
    ``LockManager._meta_lock``.
    """

    def __init__(self):
        self.lock = Lock()
        self._counter: int = 0

    def inc(self) -> None:
        self._counter += 1

    def dec(self) -> int:
        self._counter -= 1
        return self._counter


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
        self._locks: dict[str, _CountedLock] = {}
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
                file_lock = _CountedLock()
                self._locks[key] = file_lock
            file_lock.inc()

        try:
            with file_lock.lock:
                yield
        finally:
            with self._meta_lock:
                remaining = file_lock.dec()
                if remaining <= 0:
                    self._locks.pop(key, None)
