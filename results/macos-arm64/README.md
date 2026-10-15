# Recorded verified IPC round trips

Pipe receive API: `into` (into: recv_bytes_into; bytes: recv_bytes plus target copy).

Actual spawn-process observations. All prespecified pairs are retained. Medians of per-trial throughput/latency/baseline; maximum paired sampled RSS/gap. No universal speedup or unique-physical-memory claim.

| Payload bytes | Mode | Messages/trial | Payload MiB/s | RTT p50 ms | RTT p95 ms | Warm baseline RSS MiB | Peak paired RSS MiB | Max RSS gap ms |
|---|---|---|---|---|---|---|---|---|
| 64 | pipe | 8192 | 1.92 | 0.0247 | 0.0514 | 77.41 | 84.22 | 11.869 |
| 64 | shared | 8192 | 2.25 | 0.0204 | 0.0439 | 77.52 | 84.67 | 6.446 |
| 1024 | pipe | 8192 | 32.52 | 0.0251 | 0.0488 | 77.37 | 84.42 | 6.629 |
| 1024 | shared | 8192 | 34.83 | 0.0228 | 0.0463 | 77.72 | 84.95 | 6.954 |
| 16384 | pipe | 8192 | 339.37 | 0.0401 | 0.0723 | 77.60 | 84.53 | 6.943 |
| 16384 | shared | 8192 | 453.67 | 0.0220 | 0.0451 | 77.65 | 84.62 | 6.454 |
| 262144 | pipe | 1024 | 800.08 | 0.2751 | 0.4360 | 78.84 | 80.28 | 6.486 |
| 262144 | shared | 1024 | 2310.67 | 0.0990 | 0.1655 | 78.73 | 80.16 | 18.978 |
| 1048576 | pipe | 256 | 869.48 | 1.0842 | 1.5280 | 84.64 | 85.84 | 6.361 |
| 1048576 | shared | 256 | 3848.68 | 0.2384 | 0.3672 | 83.61 | 83.97 | 6.455 |
| 4194304 | pipe | 64 | 845.37 | 4.1364 | 6.1741 | 133.53 | 358.52 | 6.406 |
| 4194304 | shared | 64 | 3673.33 | 1.0975 | 1.2968 | 103.11 | 104.06 | 6.448 |

Paired shared/Pipe throughput ratios: median [min, max] over every prespecified pair, not a ratio of table medians or a confidence interval.

| Payload bytes | Paired descriptive ratio |
|---:|---:|
| 64 | 1.394 [0.857, 1.799] |
| 1024 | 1.046 [0.888, 1.267] |
| 16384 | 1.330 [1.234, 1.932] |
| 262144 | 2.924 [1.841, 3.518] |
| 1048576 | 4.411 [3.833, 4.551] |
| 4194304 | 4.337 [3.114, 5.193] |

RTT includes generation, CRC, transport/copy, complete receiver validation and ACK. One payload in flight in both modes. RSS includes warm arrays and measurement buffers and can double-count shared pages. Sampling can miss spikes. These finite traces do not establish maximum sustainable capacity.

- [JSON index](report.json)
- [Offline HTML](report.html)
