import time

from src.nodes.queue_node import ConsistentHashRing, DistributedQueue


def test_consistent_hash_owner_is_stable():
    ring = ConsistentHashRing(["node1", "node2", "node3"])
    assert ring.owner("orders") == ring.owner("orders")


def test_queue_persistence_and_recovery(tmp_path):
    queue = DistributedQueue("node1", ["node1"], tmp_path, visibility_timeout=0.01)
    message = queue.publish_local("orders", {"id": 1})
    consumed = queue.consume_local("orders")
    assert consumed["message"]["id"] == message.id

    time.sleep(0.02)
    recovered = DistributedQueue("node1", ["node1"], tmp_path, visibility_timeout=0.01)
    consumed_again = recovered.consume_local("orders")
    assert consumed_again["message"]["id"] == message.id
    assert consumed_again["message"]["attempts"] == 2


def test_ack_removes_inflight_message(tmp_path):
    queue = DistributedQueue("node1", ["node1"], tmp_path)
    message = queue.publish_local("jobs", {"task": "x"})
    queue.consume_local("jobs")
    assert queue.ack_local(message.id)["acked"] is True
    assert queue.snapshot()["inflight"] == 0
