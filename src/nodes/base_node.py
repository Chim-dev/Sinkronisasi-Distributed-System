from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import web

from src.communication.failure_detector import FailureDetector
from src.communication.message_passing import MessageBus
from src.consensus.raft import RaftNode
from src.nodes.cache_node import MESICache
from src.nodes.lock_manager import DistributedLockManager, LockMode
from src.nodes.queue_node import DistributedQueue
from src.utils.config import NodeConfig
from src.utils.metrics import MetricsRegistry


class DistributedSyncNode:
    def __init__(self, config: NodeConfig):
        self.config = config
        self.logger = logging.getLogger(config.node_id)
        self.metrics = MetricsRegistry()
        self.bus = MessageBus(config.node_id, config.peers)
        self.failure_detector = FailureDetector(config.node_id, self.bus)
        self.lock_manager = DistributedLockManager()
        self.queue = DistributedQueue(config.node_id, list(config.peers), config.data_dir, visibility_timeout=10)
        self.cache = MESICache(capacity=128, policy="LRU")
        self.raft = RaftNode(config.node_id, config.peers, self.bus, self.lock_manager.apply)
        self.app = web.Application()
        self._tasks: list[asyncio.Task[Any]] = []
        self._routes()

    def _routes(self) -> None:
        self.app.router.add_get("/health", self.health)
        self.app.router.add_get("/metrics", self.get_metrics)
        self.app.router.add_get("/state", self.get_state)
        self.app.router.add_post("/raft/request_vote", self.raft_request_vote)
        self.app.router.add_post("/raft/append_entries", self.raft_append_entries)
        self.app.router.add_post("/locks/acquire", self.acquire_lock)
        self.app.router.add_post("/locks/release", self.release_lock)
        self.app.router.add_get("/locks", self.list_locks)
        self.app.router.add_get("/locks/deadlocks", self.detect_deadlocks)
        self.app.router.add_post("/queue/{topic}/publish", self.publish)
        self.app.router.add_post("/queue/{topic}/consume", self.consume)
        self.app.router.add_post("/queue/ack/{message_id}", self.ack)
        self.app.router.add_get("/queue", self.queue_state)
        self.app.router.add_post("/cache/{key}", self.cache_put)
        self.app.router.add_get("/cache/{key}", self.cache_get)
        self.app.router.add_post("/cache/internal/update", self.cache_internal_update)
        self.app.router.add_post("/cache/internal/invalidate", self.cache_internal_invalidate)
        self.app.on_startup.append(self.on_startup)
        self.app.on_cleanup.append(self.on_cleanup)

    async def on_startup(self, _: web.Application) -> None:
        self._tasks.append(asyncio.create_task(self.raft.start()))
        self._tasks.append(asyncio.create_task(self.failure_detector.start()))

    async def on_cleanup(self, _: web.Application) -> None:
        self.raft.stop()
        self.failure_detector.stop()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def health(self, _: web.Request) -> web.Response:
        return web.json_response({"ok": True, "node_id": self.config.node_id, "role": self.raft.role.value, "leader_id": self.raft.leader_id})

    async def get_metrics(self, _: web.Request) -> web.Response:
        self.metrics.set_gauge("queue_inflight", len(self.queue.inflight))
        self.metrics.set_gauge("cache_entries", len(self.cache.entries))
        return web.json_response(self.metrics.snapshot())

    async def get_state(self, _: web.Request) -> web.Response:
        return web.json_response({
            "node_id": self.config.node_id,
            "raft": {
                "role": self.raft.role.value,
                "term": self.raft.current_term,
                "leader_id": self.raft.leader_id,
                "commit_index": self.raft.commit_index,
                "log_size": len(self.raft.log),
            },
            "failed_nodes": sorted(self.failure_detector.failed),
            "locks": self.lock_manager.snapshot(),
            "queue": self.queue.snapshot(),
            "cache": self.cache.snapshot(),
        })

    async def raft_request_vote(self, request: web.Request) -> web.Response:
        return web.json_response(self.raft.on_request_vote(await request.json()))

    async def raft_append_entries(self, request: web.Request) -> web.Response:
        return web.json_response(self.raft.on_append_entries(await request.json()))

    async def acquire_lock(self, request: web.Request) -> web.Response:
        payload = await request.json()
        resource = payload["resource"]
        owner = payload["owner"]
        mode = LockMode(payload.get("mode", "exclusive"))
        preview = self.lock_manager.preview_acquire(resource, owner, mode)
        result = await self.raft.propose({"action": "acquire", "resource": resource, "owner": owner, "mode": mode.value})
        self.metrics.inc("lock_acquire_total")
        response = dict(preview)
        response.update(result)
        return web.json_response(response, status=200 if result.get("ok") else 409)

    async def release_lock(self, request: web.Request) -> web.Response:
        payload = await request.json()
        result = await self.raft.propose({"action": "release", "resource": payload["resource"], "owner": payload["owner"]})
        self.metrics.inc("lock_release_total")
        return web.json_response(result, status=200 if result.get("ok") else 409)

    async def list_locks(self, _: web.Request) -> web.Response:
        return web.json_response(self.lock_manager.snapshot())

    async def detect_deadlocks(self, _: web.Request) -> web.Response:
        return web.json_response(self.lock_manager.detect_deadlocks())

    async def publish(self, request: web.Request) -> web.Response:
        topic = request.match_info["topic"]
        payload = await request.json()
        owner = self.queue.ring.owner(topic)
        if owner != self.config.node_id:
            return web.json_response(await self.bus.post(owner, f"/queue/{topic}/publish", payload))
        message = self.queue.publish_local(topic, payload)
        self.metrics.inc("queue_publish_total")
        return web.json_response({"published": True, "owner": owner, "message": message.__dict__})

    async def consume(self, request: web.Request) -> web.Response:
        topic = request.match_info["topic"]
        owner = self.queue.ring.owner(topic)
        if owner != self.config.node_id:
            return web.json_response(await self.bus.post(owner, f"/queue/{topic}/consume", {}))
        self.metrics.inc("queue_consume_total")
        response = self.queue.consume_local(topic)
        response["owner"] = owner
        return web.json_response(response)

    async def ack(self, request: web.Request) -> web.Response:
        message_id = request.match_info["message_id"]
        result = self.queue.ack_local(message_id)
        if not result["acked"]:
            for node_id in self.config.peers:
                if node_id == self.config.node_id:
                    continue
                try:
                    remote = await self.bus.post(node_id, f"/queue/ack/{message_id}", {})
                    if remote.get("acked"):
                        result = dict(remote)
                        result["owner"] = node_id
                        break
                except Exception:
                    continue
        self.metrics.inc("queue_ack_total")
        return web.json_response(result)

    async def queue_state(self, _: web.Request) -> web.Response:
        return web.json_response(self.queue.snapshot())

    async def cache_put(self, request: web.Request) -> web.Response:
        key = request.match_info["key"]
        payload = await request.json()
        entry = self.cache.put_local(key, payload)
        await self.bus.broadcast("/cache/internal/invalidate", {"key": key, "version": entry.version})
        await self.bus.broadcast("/cache/internal/update", {"key": key, "value": payload, "version": entry.version})
        self.metrics.inc("cache_put_total")
        return web.json_response({"ok": True, "key": key, "state": entry.state.value, "version": entry.version})

    async def cache_get(self, request: web.Request) -> web.Response:
        result = self.cache.get(request.match_info["key"])
        self.metrics.inc("cache_hit_total" if result["hit"] else "cache_miss_total")
        return web.json_response(result)

    async def cache_internal_update(self, request: web.Request) -> web.Response:
        payload = await request.json()
        self.cache.receive_update(payload["key"], payload["value"], payload["version"])
        return web.json_response({"ok": True})

    async def cache_internal_invalidate(self, request: web.Request) -> web.Response:
        payload = await request.json()
        self.cache.invalidate(payload["key"], payload.get("version", 0))
        return web.json_response({"ok": True})


def create_app(config: NodeConfig) -> web.Application:
    return DistributedSyncNode(config).app
