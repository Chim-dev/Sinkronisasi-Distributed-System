from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, Optional

import aiohttp


class MessageBus:
    def __init__(self, node_id: str, peers: Dict[str, str], timeout: float = 1.5):
        self.node_id = node_id
        self.peers = peers
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def post(self, node_id: str, path: str, payload: dict) -> dict:
        url = self.peers[node_id].rstrip("/") + path
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                return await response.json()

    async def get(self, node_id: str, path: str) -> dict:
        url = self.peers[node_id].rstrip("/") + path
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()

    async def broadcast(self, path: str, payload: dict, targets: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        target_ids = [node_id for node_id in (targets or self.peers.keys()) if node_id != self.node_id]
        results = await asyncio.gather(
            *(self.post(node_id, path, payload) for node_id in target_ids),
            return_exceptions=True,
        )
        return {
            node_id: result if not isinstance(result, Exception) else {"error": str(result)}
            for node_id, result in zip(target_ids, results)
        }
