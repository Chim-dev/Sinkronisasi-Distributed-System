from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class QueueMessage:
    id: str
    topic: str
    payload: dict
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    visible_at: float = field(default_factory=time.time)


class ConsistentHashRing:
    def __init__(self, nodes: List[str], replicas: int = 80):
        self.nodes = sorted(nodes)
        self.replicas = replicas
        self.ring: List[tuple[int, str]] = []
        for node in self.nodes:
            for replica in range(replicas):
                self.ring.append((self._hash(f"{node}:{replica}"), node))
        self.ring.sort()

    def owner(self, key: str) -> str:
        if not self.ring:
            raise RuntimeError("hash ring has no nodes")
        value = self._hash(key)
        for point, node in self.ring:
            if value <= point:
                return node
        return self.ring[0][1]

    @staticmethod
    def _hash(value: str) -> int:
        return int(hashlib.sha256(value.encode()).hexdigest(), 16)


class DistributedQueue:
    def __init__(self, node_id: str, all_nodes: List[str], data_dir: Path, visibility_timeout: float = 10.0):
        self.node_id = node_id
        self.ring = ConsistentHashRing(all_nodes)
        self.visibility_timeout = visibility_timeout
        self.path = data_dir / f"queue_{node_id}.json"
        self.queues: Dict[str, List[QueueMessage]] = defaultdict(list)
        self.inflight: Dict[str, QueueMessage] = {}
        self.load()

    def owns(self, topic: str) -> bool:
        return self.ring.owner(topic) == self.node_id

    def publish_local(self, topic: str, payload: dict) -> QueueMessage:
        message = QueueMessage(id=str(uuid.uuid4()), topic=topic, payload=payload)
        self.queues[topic].append(message)
        self.persist()
        return message

    def consume_local(self, topic: str) -> dict:
        self.recover_expired()
        now = time.time()
        for message in list(self.queues[topic]):
            if message.visible_at <= now:
                self.queues[topic].remove(message)
                message.attempts += 1
                message.visible_at = now + self.visibility_timeout
                self.inflight[message.id] = message
                self.persist()
                return {"message": message.__dict__}
        return {"message": None}

    def ack_local(self, message_id: str) -> dict:
        removed = self.inflight.pop(message_id, None)
        self.persist()
        return {"acked": removed is not None}

    def recover_expired(self) -> None:
        now = time.time()
        for message_id, message in list(self.inflight.items()):
            if message.visible_at <= now:
                self.inflight.pop(message_id)
                self.queues[message.topic].append(message)
        self.persist()

    def persist(self) -> None:
        data = {
            "queues": {topic: [message.__dict__ for message in messages] for topic, messages in self.queues.items()},
            "inflight": {mid: message.__dict__ for mid, message in self.inflight.items()},
        }
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.queues = defaultdict(list, {
            topic: [QueueMessage(**message) for message in messages]
            for topic, messages in data.get("queues", {}).items()
        })
        self.inflight = {
            mid: QueueMessage(**message)
            for mid, message in data.get("inflight", {}).items()
        }
        self.recover_expired()

    def snapshot(self) -> dict:
        return {
            "owned_topics": list(self.queues),
            "depth": {topic: len(messages) for topic, messages in self.queues.items()},
            "inflight": len(self.inflight),
        }
