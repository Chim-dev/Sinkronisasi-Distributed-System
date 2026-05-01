from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from src.communication.message_passing import MessageBus


class Role(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    term: int
    command: dict

    def to_dict(self) -> dict:
        return {"term": self.term, "command": self.command}

    @classmethod
    def from_dict(cls, value: dict) -> "LogEntry":
        return cls(term=value["term"], command=value["command"])


@dataclass
class RaftNode:
    node_id: str
    peers: Dict[str, str]
    bus: MessageBus
    apply_command: Callable[[dict], None]
    role: Role = Role.FOLLOWER
    current_term: int = 0
    voted_for: Optional[str] = None
    leader_id: Optional[str] = None
    log: List[LogEntry] = field(default_factory=list)
    commit_index: int = -1
    last_applied: int = -1
    last_heartbeat: float = field(default_factory=time.time)
    _running: bool = False

    @property
    def cluster_size(self) -> int:
        return len(self.peers)

    @property
    def majority(self) -> int:
        return self.cluster_size // 2 + 1

    async def start(self) -> None:
        self._running = True
        while self._running:
            if self.role == Role.LEADER:
                await self.send_heartbeats()
                await asyncio.sleep(0.5)
            elif time.time() - self.last_heartbeat > random.uniform(1.5, 3.0):
                await self.start_election()
            else:
                await asyncio.sleep(0.2)

    def stop(self) -> None:
        self._running = False

    async def start_election(self) -> None:
        self.role = Role.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.last_heartbeat = time.time()
        votes = 1
        payload = {
            "term": self.current_term,
            "candidate_id": self.node_id,
            "last_log_index": len(self.log) - 1,
            "last_log_term": self.log[-1].term if self.log else 0,
        }
        results = await self.bus.broadcast("/raft/request_vote", payload)
        for response in results.values():
            if isinstance(response, dict) and response.get("vote_granted"):
                votes += 1
            if isinstance(response, dict) and response.get("term", 0) > self.current_term:
                self.become_follower(response["term"])
                return
        if votes >= self.majority:
            self.role = Role.LEADER
            self.leader_id = self.node_id
            await self.send_heartbeats()

    def become_follower(self, term: int, leader_id: Optional[str] = None) -> None:
        self.role = Role.FOLLOWER
        self.current_term = term
        self.voted_for = None
        self.leader_id = leader_id
        self.last_heartbeat = time.time()

    def on_request_vote(self, payload: dict) -> dict:
        term = payload["term"]
        if term < self.current_term:
            return {"term": self.current_term, "vote_granted": False}
        if term > self.current_term:
            self.become_follower(term)
        candidate_log_ok = self._candidate_log_is_fresh(payload["last_log_index"], payload["last_log_term"])
        grant = (self.voted_for in (None, payload["candidate_id"])) and candidate_log_ok
        if grant:
            self.voted_for = payload["candidate_id"]
            self.last_heartbeat = time.time()
        return {"term": self.current_term, "vote_granted": grant}

    def on_append_entries(self, payload: dict) -> dict:
        term = payload["term"]
        if term < self.current_term:
            return {"term": self.current_term, "success": False, "match_index": len(self.log) - 1}
        self.become_follower(term, payload.get("leader_id"))
        entries = [LogEntry.from_dict(entry) for entry in payload.get("entries", [])]
        prev_index = payload.get("prev_log_index", -1)
        prev_term = payload.get("prev_log_term", 0)
        if prev_index >= 0 and (prev_index >= len(self.log) or self.log[prev_index].term != prev_term):
            return {"term": self.current_term, "success": False, "match_index": len(self.log) - 1}
        insert_at = prev_index + 1
        if entries:
            self.log = self.log[:insert_at] + entries
        leader_commit = payload.get("leader_commit", -1)
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log) - 1)
            self.apply_committed()
        return {"term": self.current_term, "success": True, "match_index": len(self.log) - 1}

    async def send_heartbeats(self) -> None:
        await self._replicate([])

    async def propose(self, command: dict) -> dict:
        if self.role != Role.LEADER:
            return {"ok": False, "leader_id": self.leader_id, "error": "not_leader"}
        entry = LogEntry(self.current_term, command)
        self.log.append(entry)
        acks = await self._replicate([entry])
        if acks >= self.majority:
            self.commit_index = len(self.log) - 1
            self.apply_committed()
            await self.send_heartbeats()
            return {"ok": True, "index": self.commit_index}
        return {"ok": False, "error": "no_majority"}

    async def _replicate(self, entries: List[LogEntry]) -> int:
        prev_index = len(self.log) - len(entries) - 1 if entries else len(self.log) - 1
        prev_term = self.log[prev_index].term if prev_index >= 0 and prev_index < len(self.log) else 0
        payload = {
            "term": self.current_term,
            "leader_id": self.node_id,
            "prev_log_index": prev_index,
            "prev_log_term": prev_term,
            "entries": [entry.to_dict() for entry in entries],
            "leader_commit": self.commit_index,
        }
        results = await self.bus.broadcast("/raft/append_entries", payload)
        acks = 1
        for response in results.values():
            if isinstance(response, dict) and response.get("success"):
                acks += 1
            if isinstance(response, dict) and response.get("term", 0) > self.current_term:
                self.become_follower(response["term"])
        return acks

    def apply_committed(self) -> None:
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            self.apply_command(self.log[self.last_applied].command)

    def _candidate_log_is_fresh(self, last_index: int, last_term: int) -> bool:
        own_term = self.log[-1].term if self.log else 0
        if last_term != own_term:
            return last_term > own_term
        return last_index >= len(self.log) - 1
