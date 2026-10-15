# Recorded verified IPC round trips

Actual spawn-process observations. All prespecified pairs are retained. Medians of per-trial throughput/latency/baseline; maximum paired sampled RSS/gap. No universal speedup or unique-physical-memory claim.

| Payload bytes | Mode | Messages/trial | Payload MiB/s | RTT p50 ms | RTT p95 ms | Warm baseline RSS MiB | Peak paired RSS MiB | Max RSS gap ms |
|---|---|---|---|---|---|---|---|---|
| 64 | pipe | 8192 | 2.28 | 0.0214 | 0.0493 | 77.56 | 84.20 | 8.665 |
| 64 | shared | 8192 | 2.35 | 0.0185 | 0.0443 | 77.57 | 84.45 | 9.440 |
| 1024 | pipe | 8192 | 32.49 | 0.0245 | 0.0546 | 77.60 | 84.28 | 8.728 |
| 1024 | shared | 8192 | 38.51 | 0.0202 | 0.0476 | 77.70 | 84.61 | 9.014 |
| 16384 | pipe | 8192 | 308.56 | 0.0412 | 0.0796 | 77.80 | 84.78 | 8.753 |
| 16384 | shared | 8192 | 557.22 | 0.0224 | 0.0528 | 77.62 | 84.72 | 8.609 |
| 262144 | pipe | 1024 | 747.63 | 0.2851 | 0.5518 | 79.12 | 80.39 | 6.928 |
| 262144 | shared | 1024 | 2400.83 | 0.1019 | 0.1529 | 78.90 | 79.80 | 7.028 |
| 1048576 | pipe | 256 | 852.78 | 1.0492 | 1.5710 | 84.31 | 85.91 | 6.699 |
| 1048576 | shared | 256 | 3198.52 | 0.2882 | 0.3941 | 83.68 | 84.09 | 6.570 |
| 4194304 | pipe | 64 | 823.65 | 4.4610 | 6.3400 | 134.67 | 358.30 | 9.573 |
| 4194304 | shared | 64 | 3744.14 | 1.0020 | 1.1924 | 103.29 | 104.44 | 6.491 |

RTT includes generation, CRC, transport/copy, complete receiver validation and ACK. One payload in flight in both modes. RSS includes warm arrays and measurement buffers and can double-count shared pages. Sampling can miss spikes. These finite traces do not establish maximum sustainable capacity.

- [JSON index](report.json)
- [Offline HTML](report.html)
