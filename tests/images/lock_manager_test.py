
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


def test_mutual_exclusion_when_waiter_still_queued():
    """Regression: a lock must not be replaced while a waiter is queued on it.

    The old implementation popped the key from the dict as soon as the
    holder exited, so a newcomer could create a fresh lock object and enter
    the critical section while a queued waiter was still blocked on the old
    lock object.
    """
    manager = LockManager()
    first_entered = threading.Event()
    first_can_exit = threading.Event()
    occupancy = []
    overlaps = []

    def worker(number):
        with manager.acquire("race_key"):
            occupancy.append(number)
            if len(occupancy) > 1:
                overlaps.append(number)
            if number == 1:
                first_entered.set()
                first_can_exit.wait(timeout=2)
            time.sleep(0.05)
            occupancy.pop()

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))
    t1.start()
    assert first_entered.wait(timeout=2)
    t2.start()
    time.sleep(0.1)  # give t2 time to register on the same lock and block
    first_can_exit.set()
    t1.join(timeout=2)

    # t3 arrives after the holder left but while t2 is still inside
    t3 = threading.Thread(target=worker, args=(3,))
    t3.start()
    t2.join(timeout=2)
    t3.join(timeout=2)

    assert not overlaps
    assert "race_key" not in manager._locks


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