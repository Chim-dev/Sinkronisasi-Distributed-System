from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


@dataclass(frozen=True)
class NodeConfig:
    node_id: str
    host: str
    port: int
    peers: Dict[str, str]
    redis_url: str
    data_dir: Path
    region: str
    replication_factor: int
    log_level: str

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def parse_cluster_nodes(value: str) -> Dict[str, str]:
    peers: Dict[str, str] = {}
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        node_id, url = item.split(":", 1)
        peers[node_id] = url
    return peers


def load_config() -> NodeConfig:
    load_dotenv()
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return NodeConfig(
        node_id=os.getenv("NODE_ID", "node1"),
        host=os.getenv("NODE_HOST", "0.0.0.0"),
        port=int(os.getenv("NODE_PORT", "8001")),
        peers=parse_cluster_nodes(os.getenv("CLUSTER_NODES", "node1:http://localhost:8001,node2:http://localhost:8002,node3:http://localhost:8003")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        data_dir=data_dir,
        region=os.getenv("REGION", "local"),
        replication_factor=int(os.getenv("REPLICATION_FACTOR", "2")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
