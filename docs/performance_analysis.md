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
| Durasi test | 2 menit |
| Jumlah user virtual | 25 |
| Spawn rate | 5 user/detik |
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

| Mode | Users | Spawn Rate | Durasi | Total RPS | Avg Latency | P95 Latency | Max Latency | Error Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 nodes normal | 25 | 5 user/detik | 2 menit | 5.97 req/s | 3654.43 ms | 20000 ms | 27705.93 ms | 26.20% |
| 3 nodes + node failure | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum diuji |

Error rate dihitung dari total `Failure Count / Request Count * 100%`, yaitu `60 / 229 * 100% = 26.20%`.

## Hasil Per Endpoint

| Endpoint | Request Count | Failure Count | RPS | Avg Latency | P95 Latency | Max Latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `POST /queue/orders/publish` | 50 | 0 | 1.30 req/s | 5216.05 ms | 20000 ms | 21312.58 ms |
| `POST /queue/orders/consume` | 45 | 0 | 1.17 req/s | 1230.20 ms | 1600 ms | 1783.51 ms |
| `POST /queue/ack/{message_id}` | 44 | 0 | 1.15 req/s | 1086.00 ms | 1700 ms | 1666.77 ms |
| `POST /cache/product-1` | 16 | 0 | 0.42 req/s | 14800.36 ms | 28000 ms | 27705.93 ms |
| `GET /cache/product-1` | 14 | 0 | 0.36 req/s | 1243.66 ms | 1500 ms | 1493.06 ms |
| `POST /locks/acquire` | 31 | 31 | 0.81 req/s | 5986.66 ms | 21000 ms | 21313.40 ms |
| `POST /locks/release` | 29 | 29 | 0.76 req/s | 1141.96 ms | 1500 ms | 1664.60 ms |

## Metrics Internal Sistem

Endpoint `/metrics` digunakan untuk melihat counter internal tiap node. Pada laporan ini, ringkasan berikut diisi dari hasil Locust CSV sehingga menunjukkan jumlah request yang dikirim selama benchmark. Untuk nilai internal seperti `cache_hit_total`, `cache_miss_total`, `queue_inflight`, dan `cache_entries`, data paling akurat tetap diambil langsung dari endpoint `/metrics` setelah benchmark selesai.

| Komponen | Metric / Endpoint | Nilai dari Locust | Failure | Keterangan |
| --- | --- | ---: | ---: | --- |
| Lock | `POST /locks/acquire` | 31 request | 31 | Semua acquire lock menghasilkan HTTP 409 Conflict |
| Lock | `POST /locks/release` | 29 request | 29 | Semua release lock menghasilkan HTTP 409 Conflict |
| Queue | `POST /queue/orders/publish` | 50 request | 0 | Publish message berhasil tanpa failure |
| Queue | `POST /queue/orders/consume` | 45 request | 0 | Consume message berhasil tanpa failure |
| Queue | `POST /queue/ack/{message_id}` | 44 request | 0 | Ack message berhasil tanpa failure |
| Cache | `POST /cache/product-1` | 16 request | 0 | Operasi write cache berhasil tanpa failure |
| Cache | `GET /cache/product-1` | 14 request | 0 | Operasi read cache berhasil tanpa failure |
| Total | Aggregated | 229 request | 60 | Error rate keseluruhan 26.20% |

Berdasarkan Locust, jumlah request per komponen adalah 139 request queue, 30 request cache, dan 60 request lock. Semua failure berasal dari lock, sedangkan queue dan cache memiliki failure count 0 pada skenario ini.

## Analisis Hasil

Berdasarkan hasil benchmark, sistem menangani total 229 request dengan throughput rata-rata 5.97 request per detik pada konfigurasi 25 virtual user dan spawn rate 5 user per detik. Average latency keseluruhan berada pada 3654.43 ms, sedangkan p95 latency berada pada 20000 ms. Nilai p95 yang jauh lebih tinggi dari median menunjukkan bahwa sebagian request mengalami tail latency tinggi, terutama pada operasi yang membutuhkan komunikasi antar-node atau operasi yang menunggu respons lebih lama.

Dari total 229 request, terdapat 169 request berhasil dan 60 request gagal. Dengan demikian, success rate pengujian adalah 73.80%, sedangkan error rate adalah 26.20%. Seluruh request yang gagal berasal dari endpoint lock, yaitu 31 failure pada `POST /locks/acquire` dan 29 failure pada `POST /locks/release`. Endpoint queue dan cache tidak menghasilkan failure pada pengujian ini.

Distribusi request pada pengujian terdiri dari 139 request queue, 30 request cache, dan 60 request lock. Queue menjadi komponen dengan request terbanyak karena skenario Locust memberi bobot lebih besar pada publish/consume. Cache memiliki jumlah request lebih sedikit, tetapi operasi write cache menunjukkan latency tertinggi dengan p95 28000 ms dan max latency 27705.93 ms. Lock memiliki failure tertinggi karena seluruh request acquire/release menghasilkan HTTP 409 Conflict.

Endpoint queue memiliki karakteristik performa yang dipengaruhi oleh consistent hashing. Pada topic `orders`, request diarahkan ke node owner tertentu. Hasil pengujian menunjukkan `POST /queue/orders/publish` memproses 50 request tanpa failure dengan rata-rata latency 5216.05 ms dan p95 20000 ms. Sementara itu, `POST /queue/orders/consume` memproses 45 request tanpa failure dengan rata-rata latency 1230.20 ms dan p95 1600 ms. Perbedaan ini menunjukkan bahwa operasi publish lebih berat dibanding consume pada pengujian ini, karena publish melibatkan pemilihan owner, forwarding bila diperlukan, dan persistence message ke storage lokal.

Operasi queue acknowledgement (`POST /queue/ack/{message_id}`) juga stabil dengan 44 request, 0 failure, rata-rata latency 1086.00 ms, dan p95 1700 ms. Hal ini menunjukkan bahwa mekanisme ack berjalan baik pada pesan yang berhasil dikonsumsi. Karena skenario hanya memakai satu topic yaitu `orders`, distribusi beban belum sepenuhnya merata ke semua node. Jika jumlah topic diperbanyak, beban queue dapat tersebar lebih baik karena consistent hashing dapat memetakan topic berbeda ke node owner berbeda.

Operasi cache read memiliki latency lebih rendah dibanding cache write. `GET /cache/product-1` memproses 14 request tanpa failure dengan rata-rata latency 1243.66 ms dan p95 1500 ms. Sebaliknya, `POST /cache/product-1` memproses 16 request tanpa failure dengan rata-rata latency 14800.36 ms dan p95 28000 ms. Perbedaan ini terjadi karena write cache tidak hanya mengubah data lokal, tetapi juga melakukan propagasi invalidation dan update ke peer agar coherence antar-node tetap terjaga. Dengan demikian, cache read relatif ringan, sedangkan cache write memiliki overhead komunikasi yang lebih besar.

Operasi lock menunjukkan failure paling tinggi. `POST /locks/acquire` memiliki 31 request dan seluruhnya gagal, sedangkan `POST /locks/release` memiliki 29 request dan seluruhnya gagal. File `locust_result_failures.csv` menunjukkan error berupa HTTP 409 Conflict pada kedua endpoint tersebut. Hal ini menandakan bahwa skenario Locust untuk lock belum ideal untuk mengukur performa lock normal, karena request lock membutuhkan kondisi leader Raft yang tepat dan state lock yang sesuai. Pada implementasi ini, operasi lock write harus dikirim ke leader. Jika request diarahkan ke node non-leader atau lock tidak berada pada state yang dapat dilepas, sistem mengembalikan konflik dan Locust menghitungnya sebagai failure.

Error rate keseluruhan sebesar 26.20% berasal dari 60 failure pada 229 request. Namun, failure tersebut terkonsentrasi pada endpoint lock. Endpoint queue dan cache pada pengujian ini tidak menghasilkan failure. Oleh karena itu, hasil benchmark menunjukkan bahwa queue dan cache stabil pada skenario yang diuji, sedangkan skenario lock perlu diuji ulang dengan mengarahkan request ke leader Raft dan mengatur owner/resource agar acquire dan release berjalan secara valid.

## Analisis Saat Node Failure

Pada pengujian Locust ini, skenario node failure belum dijalankan sebagai benchmark terpisah. Karena itu, tabel hasil node failure masih belum diisi. Untuk melengkapi analisis failure, pengujian berikutnya dapat dilakukan dengan menjalankan Locust, menghentikan salah satu container node di tengah pengujian, lalu membandingkan RPS, p95 latency, dan error rate sebelum dan sesudah node dihentikan.

Penurunan throughput atau kenaikan latency pada skenario ini wajar terjadi karena sebagian request perlu melakukan retry, forwarding, atau menunggu deteksi failure. Pada komponen lock, Raft membutuhkan mayoritas node agar command tetap dapat diproses. Dengan tiga node, sistem masih dapat berjalan selama dua node masih aktif. Pada komponen queue, topic yang owner-nya berada pada node yang gagal dapat mengalami gangguan sampai node kembali tersedia atau mekanisme recovery dijalankan.

## Kesimpulan

Dari hasil pengujian, sistem menunjukkan bahwa setiap komponen memiliki tradeoff performa yang berbeda. Queue dapat menjalankan publish, consume, dan ack tanpa failure pada skenario yang diuji, tetapi latency publish lebih tinggi karena melibatkan owner routing dan persistence. Cache read memiliki latency lebih rendah, sedangkan cache write memiliki latency tinggi karena membutuhkan propagation ke node lain agar coherence tetap terjaga. Lock manager belum berhasil diuji sebagai successful request pada skenario Locust ini karena seluruh request lock menghasilkan HTTP 409 Conflict.

Secara umum, queue dan cache dapat dikatakan stabil pada pengujian ini karena tidak menghasilkan failure. Namun, error rate keseluruhan masih tinggi karena endpoint lock gagal seluruhnya. Untuk mendapatkan hasil performance analysis yang lebih representatif, skenario Locust bagian lock perlu diperbaiki agar request dikirim ke leader Raft dan release hanya dilakukan setelah acquire berhasil.

## Visualisasi yang Disarankan

Gunakan CSV Locust untuk membuat grafik berikut:

- Grafik total RPS terhadap waktu.
- Grafik average dan p95 latency per endpoint.
- Grafik perbandingan latency queue, cache, dan lock.
- Grafik error rate pada kondisi normal dan node failure.
