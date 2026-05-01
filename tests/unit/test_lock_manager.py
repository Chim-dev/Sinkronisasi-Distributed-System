from src.nodes.lock_manager import DistributedLockManager, LockMode


def test_shared_and_exclusive_lock_semantics():
    manager = DistributedLockManager()
    manager.apply({"action": "acquire", "resource": "file", "owner": "alice", "mode": "shared"})
    manager.apply({"action": "acquire", "resource": "file", "owner": "bob", "mode": "shared"})
    manager.apply({"action": "acquire", "resource": "file", "owner": "carol", "mode": "exclusive"})

    state = manager.snapshot()["file"]
    assert state["shared_owners"] == ["alice", "bob"]
    assert state["exclusive_owner"] is None
    assert state["wait_queue"][0]["owner"] == "carol"

    manager.apply({"action": "release", "resource": "file", "owner": "alice"})
    manager.apply({"action": "release", "resource": "file", "owner": "bob"})

    state = manager.snapshot()["file"]
    assert state["exclusive_owner"] == "carol"


def test_deadlock_detection_finds_wait_for_cycle():
    manager = DistributedLockManager()
    manager.apply({"action": "acquire", "resource": "a", "owner": "n1", "mode": "exclusive"})
    manager.apply({"action": "acquire", "resource": "b", "owner": "n2", "mode": "exclusive"})
    manager.apply({"action": "acquire", "resource": "b", "owner": "n1", "mode": "exclusive"})
    manager.apply({"action": "acquire", "resource": "a", "owner": "n2", "mode": "exclusive"})

    result = manager.detect_deadlocks()
    assert result["deadlocked"] is True
    assert any(cycle[0] == cycle[-1] for cycle in result["cycles"])


def test_preview_does_not_mutate_state():
    manager = DistributedLockManager()
    preview = manager.preview_acquire("x", "owner", LockMode.EXCLUSIVE)
    assert preview["granted"] is True
    assert manager.snapshot()["x"]["exclusive_owner"] is None
