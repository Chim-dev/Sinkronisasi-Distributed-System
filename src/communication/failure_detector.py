from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Set

from src.communication.message_passing import MessageBus


@dataclass
class FailureDetector:
    node_id: str
    bus: MessageBus
    heartbeat_interval: float = 2.0
    failure_timeout: float = 6.0
    last_seen: Dict[str, float] = field(default_factory=dict)
    failed: Set[str] = field(default_factory=set)
    _running: bool = False

    async def start(self) -> None:
        self._running = True
        while self._running:
            await self.probe_once()
            await asyncio.sleep(self.heartbeat_interval)

    def stop(self) -> None:
        self._running = False

    async def probe_once(self) -> None:
        now = time.time()
        for peer_id in self.bus.peers:
            if peer_id == self.node_id:
                continue
            try:
                await self.bus.get(peer_id, "/health")
                self.last_seen[peer_id] = now
                self.failed.discard(peer_id)
            except Exception:
                if now - self.last_seen.get(peer_id, 0) > self.failure_timeout:
                    self.failed.add(peer_id)

    def alive_nodes(self) -> Set[str]:
        return set(self.bus.peers) - self.failed
