# Deployment Guide

## Prasyarat

- Python 3.8+; direkomendasikan Python 3.11.
- Docker dan Docker Compose.
- Port `8001`, `8002`, `8003`, dan `6379` tersedia.

## Local Development

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Jalankan satu node manual:

```bash
$env:NODE_ID="node1"
$env:NODE_PORT="8001"
$env:CLUSTER_NODES="node1:http://localhost:8001,node2:http://localhost:8002,node3:http://localhost:8003"
python -m src.main
```

Untuk cluster lokal tanpa Docker, buka tiga terminal dan ubah `NODE_ID` serta `NODE_PORT`.

## Docker Compose

```bash
docker compose -f docker/docker-compose.yml up --build
```

Cek status:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## Troubleshooting

- `not_leader`: cek `/health`, cari `leader_id`, lalu kirim ulang request lock ke leader.
- Queue tidak muncul di node yang sama: topic dimiliki oleh hasil consistent hashing, cek field `owner` pada response.
- Message terkirim ulang: ini normal untuk at-least-once delivery saat ack belum diterima.
- Leader belum muncul: tunggu 3-5 detik setelah cluster start agar election selesai.
- Port conflict: ubah mapping port di `docker/docker-compose.yml`.

## Dynamic Scaling

Desain queue memakai hash ring sehingga node baru dapat ditambahkan ke `CLUSTER_NODES`. Untuk demo tugas, compose menyediakan 3 node fixed agar identity dan port jelas. Jika ingin scaling, tambahkan service baru dengan `NODE_ID` unik dan update `CLUSTER_NODES` di semua node.
