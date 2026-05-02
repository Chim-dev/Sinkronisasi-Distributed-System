# Distributed Sync System

Sistem simulasi sinkronisasi terdistribusi untuk tugas distributed systems. Proyek ini berisi tiga komponen utama:

- Distributed Lock Manager dengan Raft consensus sederhana, shared/exclusive locks, dan deadlock detection.
- Distributed Queue dengan consistent hashing, persistence lokal, recovery, dan at-least-once delivery.
- Distributed Cache Coherence dengan protokol MESI, invalidation/update propagation, LRU/LFU replacement, dan metrics.

## Quick Start

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Jalankan 3 node dengan Docker:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Endpoint node tersedia di:

- `http://localhost:8001`
- `http://localhost:8002`
- `http://localhost:8003`

## Demo API

```bash
curl http://localhost:8001/health
curl -X POST http://localhost:8001/locks/acquire -H "Content-Type: application/json" -d "{\"resource\":\"inventory\",\"owner\":\"client-a\",\"mode\":\"exclusive\"}"
curl -X POST http://localhost:8001/locks/release -H "Content-Type: application/json" -d "{\"resource\":\"inventory\",\"owner\":\"client-a\"}"

curl -X POST http://localhost:8001/queue/orders/publish -H "Content-Type: application/json" -d "{\"order_id\":1}"
curl -X POST http://localhost:8002/queue/orders/consume -H "Content-Type: application/json" -d "{}"

curl -X POST http://localhost:8001/cache/product-1 -H "Content-Type: application/json" -d "{\"stock\":25}"
curl http://localhost:8002/cache/product-1
curl http://localhost:8001/metrics
```

Lock write harus dikirim ke leader Raft. Jika node bukan leader, respons akan berisi `leader_id`; ulangi request ke node leader.

## Performance Test

```bash
locust -f benchmarks/load_test_scenarios.py --host http://localhost:8001
```

Buka `http://localhost:8089`, lalu jalankan skenario queue, cache, dan lock.

## Dokumentasi

- [Architecture](docs/architecture.md)
- [OpenAPI Spec](docs/api_spec.yaml)
- [Deployment Guide](docs/deployment_guide.md)
- [Performance Analysis](docs/performance_analysis.md)

## Video

Link YouTube publik: `https://youtu.be/PyzNjkaRVaA`

Disclaimer: Video presentasi menggunakan avatar hanya sebagai media bantu visual agar penyampaian materi lebih dinamis dan mudah diikuti. Penggunaan avatar tidak dimaksudkan untuk mengurangi rasa hormat, keseriusan, atau tanggung jawab akademik dalam presentasi ini. Seluruh isi teknis, demo sistem, penjelasan arsitektur, dan hasil analisis tetap disusun berdasarkan implementasi proyek ini.
