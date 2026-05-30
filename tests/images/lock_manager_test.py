
import threading
import time

from sts.images.lock_manager import LockManager


def test_basic_acquire_and_cleanup():
    """Verify basic lock creation and removal after context exit."""
    manager = LockManager()

    with manager.acquire("test_key"):
        assert "test_key" in manager._locks

    # Lock should be removed immediately after exiting the context
    assert "test_key" not in manager._locks


def test_exception_cleanup():
    """Verify that the lock is removed even when an exception is raised."""
    manager = LockManager()

    try:
        with manager.acquire("error_key"):
            assert "error_key" in manager._locks
            raise ValueError("Unexpected error")
    except ValueError:
        pass

    # finally block guarantees removal
    assert "error_key" not in manager._locks


def test_sequential_execution_same_key():
    """Verify that two threads with the SAME key block each other."""
    manager = LockManager()
    execution_times = []

    def worker(duration):
        with manager.acquire("shared_key"):
            start = time.time()
            time.sleep(duration)
            execution_times.append(time.time() - start)

    t1 = threading.Thread(target=worker, args=(0.2,))
    t2 = threading.Thread(target=worker, args=(0.2,))

    start = time.time()
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    total_time = time.time() - start

    # If they ran in parallel, it would take ~0.2 sec.
    # Since they block each other, it takes ~0.4 sec
    assert total_time >= 0.35
    # Total execution time inside should match
    assert sum(execution_times) >= 0.35


def test_parallel_execution_different_keys():
    """Verify that two threads with DIFFERENT keys run in parallel."""
    manager = LockManager()

    def worker(key_id, duration):
        with manager.acquire(f"unique_key_{key_id}"):
            time.sleep(duration)

    t1 = threading.Thread(target=worker, args=(1, 0.2))
    t2 = threading.Thread(target=worker, args=(2, 0.2))

    start = time.time()
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    total_time = time.time() - start

    # Should complete in ~0.2 sec, not 0.4
    assert total_time < 0.25


def test_lock_memory_cleanup_under_load():
    """Verify that no memory is leaked after a large number of requests."""
    manager = LockManager()

    def worker(unique_id):
        key = f"heavy_load_{unique_id}"
        with manager.acquire(key):
            # Simulate work
            pass

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The internal dictionary should be fully cleared
    assert len(manager._locks) == 0