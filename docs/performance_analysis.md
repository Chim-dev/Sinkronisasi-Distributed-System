# Performance Analysis

Bagian ini menjelaskan hasil pengujian performa sistem Distributed Sync System. Pengujian dilakukan menggunakan Locust untuk mengukur throughput, latency, dan error rate pada tiga fitur utama: distributed lock, distributed queue, dan cache coherence. Data numerik pada bagian ini diisi berdasarkan hasil benchmark yang dijalankan pada mesin penguji.

## Tujuan Pengujian

Tujuan performance test adalah mengetahui kemampuan sistem dalam menangani beban request secara bersamaan dan melihat karakteristik performa dari masing-masing komponen. Pengujian juga digunakan untuk membandingkan perilaku sistem ketika berjalan pada kondisi normal dan ketika salah satu node mengalami gangguan.

Metrik utama yang diamati adalah:

- Throughput, yaitu jumlah request yang dapat diproses per detik.
- Average latency, yaitu rata-rata waktu respons request.
- P95 latency, yaitu batas waktu respons untuk 95% request.
- Maximum latency, yaitu waktu respons tertinggi selama pengujian.
- Error rate, yaitu persentase request yang gagal.
- Internal metrics, yaitu counter dan gauge dari endpoint `/metrics`.

## Lingkungan Pengujian

Pengujian dijalankan dengan konfigurasi berikut:

| Item | Nilai |
| --- | --- |
| Jumlah node | 3 node (`node1`, `node2`, `node3`) |
| Endpoint utama | `http://localhost:8001` |
| Tool benchmark | Locust |
| Durasi test | `[isi durasi, contoh: 2 menit]` |
| Jumlah user virtual | `[isi jumlah user, contoh: 25]` |
| Spawn rate | `[isi spawn rate, contoh: 5 user/detik]` |
| Mesin pengujian | `[isi spesifikasi singkat laptop/PC]` |

Command benchmark:

```bash
locust -f benchmarks/load_test_scenarios.py --host http://localhost:8001 --headless -u [jumlah_user] -r [spawn_rate] -t [durasi] --csv docs/locust_result
```

Contoh:

```bash
locust -f benchmarks/load_test_scenarios.py --host http://localhost:8001 --headless -u 25 -r 5 -t 2m --csv docs/locust_result
```

Selain Locust, data internal sistem dapat diambil melalui:

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/metrics" | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://localhost:8002/metrics" | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://localhost:8003/metrics" | ConvertTo-Json -Depth 10
```

## Skenario Pengujian

| Skenario | Deskripsi | Endpoint |
| --- | --- | --- |
| Queue publish/consume | Client mengirim message ke topic `orders`, lalu message dikonsumsi dan di-ack | `/queue/orders/publish`, `/queue/orders/consume`, `/queue/ack/{id}` |
| Cache put/get | Client menulis data produk, lalu membaca data dari cache | `/cache/product-1` |
| Lock acquire/release | Client meminta exclusive lock pada resource `inventory`, lalu melepas lock | `/locks/acquire`, `/locks/release` |

## Hasil Pengujian Keseluruhan

Isi tabel berikut dari file `docs/locust_result_stats.csv` atau dashboard Locust.

| Mode | Users | Spawn Rate | Durasi | Total RPS | Avg Latency | P95 Latency | Max Latency | Error Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 nodes normal | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| 3 nodes + node failure | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |

## Hasil Per Endpoint

Isi tabel berikut dari baris endpoint pada hasil Locust.

| Endpoint | Request Count | Failure Count | RPS | Avg Latency | P95 Latency | Max Latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `POST /queue/orders/publish` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| `POST /queue/orders/consume` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| `POST /queue/ack/{message_id}` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| `POST /cache/product-1` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| `GET /cache/product-1` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| `POST /locks/acquire` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |
| `POST /locks/release` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` | `[isi]` |

## Metrics Internal Sistem

Endpoint `/metrics` digunakan untuk melihat counter internal tiap node. Nilai ini membantu menjelaskan apakah request benar-benar masuk ke komponen lock, queue, dan cache.

| Node | Metric | Nilai | Keterangan |
| --- | --- | ---: | --- |
| node1 | `lock_acquire_total` | `[isi]` | Jumlah request acquire lock |
| node1 | `lock_release_total` | `[isi]` | Jumlah request release lock |
| node1 | `queue_publish_total` | `[isi]` | Jumlah publish message yang diproses node |
| node1 | `queue_consume_total` | `[isi]` | Jumlah consume message yang diproses node |
| node1 | `queue_ack_total` | `[isi]` | Jumlah ack message |
| node1 | `cache_put_total` | `[isi]` | Jumlah operasi write cache |
| node1 | `cache_hit_total` | `[isi]` | Jumlah cache hit |
| node1 | `cache_miss_total` | `[isi]` | Jumlah cache miss |
| node1 | `queue_inflight` | `[isi]` | Message yang sedang dikonsumsi tetapi belum ack |
| node1 | `cache_entries` | `[isi]` | Jumlah entry cache |

Jika diperlukan, tabel yang sama dapat dibuat untuk `node2` dan `node3`.

## Analisis Hasil

Berdasarkan hasil benchmark, sistem mampu menangani beban sebesar `[isi total RPS]` request per detik pada konfigurasi `[isi jumlah user]` virtual user. Average latency berada pada `[isi avg latency]`, sedangkan p95 latency berada pada `[isi p95 latency]`. Nilai p95 lebih penting daripada rata-rata karena menunjukkan pengalaman mayoritas request ketika sistem berada di bawah beban.

Endpoint queue memiliki karakteristik performa yang dipengaruhi oleh consistent hashing. Pada topic `orders`, request akan diarahkan ke node owner tertentu. Karena itu, walaupun sistem memiliki tiga node, topic tunggal tidak selalu membagi beban secara merata ke semua node. Jika jumlah topic diperbanyak, distribusi beban akan lebih tersebar karena setiap topic dapat dipetakan ke node owner yang berbeda.

Operasi cache memiliki latency yang relatif rendah pada operasi read lokal, terutama ketika data sudah tersedia di cache dan menghasilkan cache hit. Namun operasi write cache membutuhkan propagasi invalidation dan update ke node lain. Hal ini dapat menambah latency dibanding read biasa, tetapi diperlukan agar data antar-node tetap konsisten sesuai mekanisme MESI.

Operasi lock cenderung memiliki latency lebih tinggi dibanding queue dan cache karena request acquire dan release lock harus diproses melalui mekanisme Raft. Raft menambah overhead komunikasi karena command perlu disepakati oleh mayoritas node sebelum dianggap committed. Overhead ini merupakan tradeoff untuk mendapatkan konsistensi pada distributed lock.

Error rate sebesar `[isi error rate]` menunjukkan tingkat stabilitas sistem selama pengujian. Jika error rate mendekati 0%, maka sistem dapat dikatakan stabil pada beban tersebut. Jika terdapat error, penyebab yang perlu dianalisis adalah kemungkinan request lock dikirim ke non-leader, timeout antar-node, queue kosong saat consume, atau node tidak tersedia saat skenario failure dijalankan.

## Analisis Saat Node Failure

Pada skenario node failure, salah satu node dihentikan selama benchmark berjalan. Hasil pengujian menunjukkan perubahan throughput dari `[isi RPS normal]` menjadi `[isi RPS failure]`, dan p95 latency berubah dari `[isi p95 normal]` menjadi `[isi p95 failure]`.

Penurunan throughput atau kenaikan latency pada skenario ini wajar terjadi karena sebagian request perlu melakukan retry, forwarding, atau menunggu deteksi failure. Pada komponen lock, Raft membutuhkan mayoritas node agar command tetap dapat diproses. Dengan tiga node, sistem masih dapat berjalan selama dua node masih aktif. Pada komponen queue, topic yang owner-nya berada pada node yang gagal dapat mengalami gangguan sampai node kembali tersedia atau mekanisme recovery dijalankan.

## Kesimpulan

Dari hasil pengujian, sistem menunjukkan bahwa setiap komponen memiliki tradeoff performa yang berbeda. Queue cocok untuk workload asynchronous dan throughput-nya dipengaruhi oleh distribusi topic. Cache memberikan read latency yang rendah, tetapi write membutuhkan propagation agar coherence tetap terjaga. Lock manager memiliki overhead paling besar karena menggunakan Raft untuk menjaga konsistensi, tetapi overhead tersebut diperlukan agar keputusan lock tidak berbeda antar-node.

Secara umum, sistem dapat dikatakan berjalan baik apabila error rate rendah, throughput stabil selama durasi pengujian, dan p95 latency masih berada dalam batas yang dapat diterima untuk simulasi distributed system.

## Visualisasi yang Disarankan

Gunakan CSV Locust untuk membuat grafik berikut:

- Grafik total RPS terhadap waktu.
- Grafik average dan p95 latency per endpoint.
- Grafik perbandingan latency queue, cache, dan lock.
- Grafik error rate pada kondisi normal dan node failure.
