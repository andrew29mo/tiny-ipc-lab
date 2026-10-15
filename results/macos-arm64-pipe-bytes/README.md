# Recorded verified IPC round trips

Pipe receive API: `bytes` (into: recv_bytes_into; bytes: recv_bytes plus target copy).

Actual spawn-process observations. All prespecified pairs are retained. Medians of per-trial throughput/latency/baseline; maximum paired sampled RSS/gap. No universal speedup or unique-physical-memory claim.

| Payload bytes | Mode | Messages/trial | Payload MiB/s | RTT p50 ms | RTT p95 ms | Warm baseline RSS MiB | Peak paired RSS MiB | Max RSS gap ms |
|---|---|---|---|---|---|---|---|---|
| 64 | pipe | 8192 | 2.11 | 0.0217 | 0.0459 | 77.44 | 84.09 | 6.826 |
| 64 | shared | 8192 | 2.47 | 0.0188 | 0.0388 | 77.46 | 84.36 | 7.244 |
| 1024 | pipe | 8192 | 36.00 | 0.0219 | 0.0400 | 77.57 | 84.33 | 6.422 |
| 1024 | shared | 8192 | 34.08 | 0.0191 | 0.0408 | 77.58 | 84.55 | 6.807 |
| 16384 | pipe | 8192 | 343.08 | 0.0389 | 0.0584 | 77.54 | 84.55 | 6.603 |
| 16384 | shared | 8192 | 509.46 | 0.0206 | 0.0371 | 77.61 | 85.05 | 6.875 |
| 262144 | pipe | 1024 | 594.74 | 0.3288 | 0.7442 | 78.86 | 80.03 | 7.437 |
| 262144 | shared | 1024 | 1916.06 | 0.1046 | 0.2022 | 78.95 | 80.06 | 6.577 |
| 1048576 | pipe | 256 | 898.19 | 1.0108 | 1.5141 | 84.77 | 85.78 | 6.936 |
| 1048576 | shared | 256 | 3582.36 | 0.2547 | 0.3964 | 83.57 | 83.97 | 6.397 |
| 4194304 | pipe | 64 | 894.81 | 3.8930 | 5.9857 | 106.19 | 107.28 | 6.372 |
| 4194304 | shared | 64 | 3627.00 | 1.0820 | 1.2655 | 102.59 | 104.02 | 6.371 |

Paired shared/Pipe throughput ratios: median [min, max] over every prespecified pair, not a ratio of table medians or a confidence interval.

| Payload bytes | Paired descriptive ratio |
|---:|---:|
| 64 | 1.144 [0.873, 1.681] |
| 1024 | 0.977 [0.785, 1.342] |
| 16384 | 1.551 [1.324, 1.879] |
| 262144 | 3.324 [2.647, 4.277] |
| 1048576 | 4.186 [2.361, 4.307] |
| 4194304 | 4.040 [2.198, 4.607] |

RTT includes generation, CRC, transport/copy, complete receiver validation and ACK. One payload in flight in both modes. RSS includes warm arrays and measurement buffers and can double-count shared pages. Sampling can miss spikes. These finite traces do not establish maximum sustainable capacity.

- [JSON index](report.json)
- [Offline HTML](report.html)
