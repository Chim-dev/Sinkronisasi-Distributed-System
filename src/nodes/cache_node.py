from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class MESIState(str, Enum):
    MODIFIED = "M"
    EXCLUSIVE = "E"
    SHARED = "S"
    INVALID = "I"


@dataclass
class CacheEntry:
    key: str
    value: dict
    state: MESIState
    version: int = 1
    updated_at: float = field(default_factory=time.time)
    hits: int = 0


class MESICache:
    def __init__(self, capacity: int = 128, policy: str = "LRU"):
        self.capacity = capacity
        self.policy = policy.upper()
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> dict:
        entry = self.entries.get(key)
        if not entry or entry.state == MESIState.INVALID:
            return {"hit": False, "value": None}
        entry.hits += 1
        if self.policy == "LRU":
            self.entries.move_to_end(key)
        return {"hit": True, "value": entry.value, "state": entry.state.value, "version": entry.version}

    def put_local(self, key: str, value: dict) -> CacheEntry:
        old = self.entries.get(key)
        entry = CacheEntry(key=key, value=value, state=MESIState.MODIFIED, version=(old.version + 1 if old else 1))
        self.entries[key] = entry
        self.entries.move_to_end(key)
        self.evict_if_needed()
        return entry

    def receive_update(self, key: str, value: dict, version: int) -> None:
        current = self.entries.get(key)
        if current and current.version > version:
            return
        self.entries[key] = CacheEntry(key=key, value=value, state=MESIState.SHARED, version=version)
        self.entries.move_to_end(key)
        self.evict_if_needed()

    def invalidate(self, key: str, version: int = 0) -> None:
        entry = self.entries.get(key)
        if entry and entry.version <= version:
            entry.state = MESIState.INVALID

    def evict_if_needed(self) -> None:
        while len(self.entries) > self.capacity:
            if self.policy == "LFU":
                victim = min(self.entries.values(), key=lambda entry: (entry.hits, entry.updated_at)).key
                self.entries.pop(victim, None)
            else:
                self.entries.popitem(last=False)

    def snapshot(self) -> dict:
        return {
            key: {
                "state": entry.state.value,
                "version": entry.version,
                "hits": entry.hits,
                "updated_at": entry.updated_at,
            }
            for key, entry in self.entries.items()
        }
