from __future__ import annotations

import statistics
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterator


@dataclass
class MetricsRegistry:
    counters: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    gauges: Dict[str, float] = field(default_factory=dict)
    latencies: Dict[str, Deque[float]] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=1000)))

    def inc(self, name: str, value: int = 1) -> None:
        self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        self.latencies[name].append(value)

    @contextmanager
    def timer(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.observe(name, time.perf_counter() - start)

    def snapshot(self) -> dict:
        latency_snapshot = {}
        for key, values in self.latencies.items():
            data = list(values)
            if not data:
                continue
            latency_snapshot[key] = {
                "count": len(data),
                "avg_ms": round(statistics.mean(data) * 1000, 3),
                "p95_ms": round(_percentile(data, 0.95) * 1000, 3),
                "max_ms": round(max(data) * 1000, 3),
            }
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "latencies": latency_snapshot,
        }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * percentile))
    return ordered[index]
