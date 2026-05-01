from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class LockMode(str, Enum):
    SHARED = "shared"
    EXCLUSIVE = "exclusive"


@dataclass
class LockRequest:
    resource: str
    owner: str
    mode: LockMode
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResourceLock:
    shared_owners: Set[str] = field(default_factory=set)
    exclusive_owner: Optional[str] = None
    wait_queue: List[LockRequest] = field(default_factory=list)


class DistributedLockManager:
    def __init__(self) -> None:
        self.resources: Dict[str, ResourceLock] = defaultdict(ResourceLock)

    def apply(self, command: dict) -> None:
        action = command.get("action")
        if action == "acquire":
            self._apply_acquire(command["resource"], command["owner"], LockMode(command["mode"]))
        elif action == "release":
            self._apply_release(command["resource"], command["owner"])

    def preview_acquire(self, resource: str, owner: str, mode: LockMode) -> dict:
        lock = self.resources[resource]
        can_grant = self._can_grant(lock, owner, mode)
        return {"granted": can_grant, "resource": resource, "owner": owner, "mode": mode.value}

    def _apply_acquire(self, resource: str, owner: str, mode: LockMode) -> None:
        lock = self.resources[resource]
        if self._can_grant(lock, owner, mode):
            if mode == LockMode.SHARED:
                lock.shared_owners.add(owner)
            else:
                lock.exclusive_owner = owner
            lock.wait_queue = [req for req in lock.wait_queue if req.owner != owner]
            return
        if not any(req.owner == owner for req in lock.wait_queue):
            lock.wait_queue.append(LockRequest(resource, owner, mode))

    def _apply_release(self, resource: str, owner: str) -> None:
        lock = self.resources[resource]
        lock.shared_owners.discard(owner)
        if lock.exclusive_owner == owner:
            lock.exclusive_owner = None
        self._promote_waiters(lock)

    def _promote_waiters(self, lock: ResourceLock) -> None:
        changed = True
        while changed:
            changed = False
            for request in list(lock.wait_queue):
                if self._can_grant(lock, request.owner, request.mode):
                    if request.mode == LockMode.SHARED:
                        lock.shared_owners.add(request.owner)
                    else:
                        lock.exclusive_owner = request.owner
                    lock.wait_queue.remove(request)
                    changed = True
                    if request.mode == LockMode.EXCLUSIVE:
                        return

    def _can_grant(self, lock: ResourceLock, owner: str, mode: LockMode) -> bool:
        if mode == LockMode.SHARED:
            return lock.exclusive_owner in (None, owner)
        return (lock.exclusive_owner in (None, owner)) and (not lock.shared_owners or lock.shared_owners == {owner})

    def release_all(self, owner: str) -> None:
        for resource in list(self.resources):
            self._apply_release(resource, owner)

    def detect_deadlocks(self) -> dict:
        waits_for: Dict[str, Set[str]] = defaultdict(set)
        for lock in self.resources.values():
            holders = set(lock.shared_owners)
            if lock.exclusive_owner:
                holders.add(lock.exclusive_owner)
            for request in lock.wait_queue:
                waits_for[request.owner].update(holder for holder in holders if holder != request.owner)
        cycles = _find_cycles(waits_for)
        return {"deadlocked": bool(cycles), "cycles": cycles, "waits_for": {k: sorted(v) for k, v in waits_for.items()}}

    def snapshot(self) -> dict:
        return {
            resource: {
                "shared_owners": sorted(lock.shared_owners),
                "exclusive_owner": lock.exclusive_owner,
                "wait_queue": [_request_to_dict(request) for request in lock.wait_queue],
            }
            for resource, lock in self.resources.items()
        }


def _find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    cycles: List[List[str]] = []
    visited: Set[str] = set()

    def dfs(node: str, path: List[str]) -> None:
        if node in path:
            cycles.append(path[path.index(node):] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        for neighbor in graph.get(node, set()):
            dfs(neighbor, path + [node])

    for node in graph:
        dfs(node, [])
    return cycles


def _request_to_dict(request: LockRequest) -> dict:
    data = dict(request.__dict__)
    data["mode"] = request.mode.value
    return data
