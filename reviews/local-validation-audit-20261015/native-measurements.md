Native macOS ARM64; dedicated Colima VM stopped during measurement.

# Bounded IPC pool comparison

Five-profile verified exchanges; all blocks retained. ACK-observed latency includes loan waiting and ACK collection; admitted-to-ready and ACK-observation lag are reported separately. RSS is sampled two-worker RSS, not unique physical RAM.

| Case | Profile | Count | MiB/s median | ACK-observed p50 ms | ACK-observed p95 ms | Admitted-to-ready p95 ms | ACK-observation lag p95 ms | Baseline RSS MiB median | Peak RSS MiB max | Slots max | ACK-reclaim events median | Reclaim ms total median | Max RSS gap ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal-64 | pipe | 8192 | 2.15 | 0.0209 | 0.0453 | 0.0296 | 0.0195 | 78.31 | 86.28 | 1 | 0 | 0.000 | 7.112 |
| normal-64 | shared | 8192 | 2.64 | 0.0186 | 0.0400 | 0.0259 | 0.0202 | 78.14 | 86.28 | 1 | 0 | 0.000 | 8.054 |
| normal-64 | pool_1 | 8192 | 2.21 | 0.0406 | 0.0910 | 0.0279 | 0.0205 | 78.16 | 90.59 | 1 | 8191 | 187.639 | 9.791 |
| normal-64 | pool_n | 8192 | 6.43 | 0.0353 | 0.0943 | 0.0465 | 0.0411 | 78.20 | 91.06 | 4 | 8188 | 49.365 | 7.525 |
| normal-64 | window_pipe | 8192 | 5.30 | 0.0402 | 0.1016 | 0.0538 | 0.0494 | 78.42 | 90.73 | 4 | 8188 | 55.734 | 7.895 |
| normal-1024 | pipe | 8192 | 31.68 | 0.0245 | 0.0520 | 0.0295 | 0.0212 | 78.16 | 86.06 | 1 | 0 | 0.000 | 8.862 |
| normal-1024 | shared | 8192 | 37.17 | 0.0206 | 0.0395 | 0.0272 | 0.0207 | 78.33 | 86.25 | 1 | 0 | 0.000 | 6.421 |
| normal-1024 | pool_1 | 8192 | 39.24 | 0.0369 | 0.0717 | 0.0241 | 0.0188 | 78.27 | 91.05 | 1 | 8191 | 166.754 | 7.633 |
| normal-1024 | pool_n | 8192 | 67.68 | 0.0373 | 0.0982 | 0.0460 | 0.0415 | 78.27 | 90.78 | 4 | 8188 | 85.035 | 7.432 |
| normal-1024 | window_pipe | 8192 | 53.61 | 0.0491 | 0.1201 | 0.0549 | 0.0495 | 78.27 | 91.20 | 4 | 8188 | 90.865 | 10.523 |
| normal-16384 | pipe | 8192 | 345.24 | 0.0393 | 0.0567 | 0.0461 | 0.0158 | 78.25 | 86.28 | 1 | 0 | 0.000 | 7.135 |
| normal-16384 | shared | 8192 | 523.26 | 0.0224 | 0.0390 | 0.0253 | 0.0147 | 78.25 | 86.25 | 1 | 0 | 0.000 | 7.914 |
| normal-16384 | pool_1 | 8192 | 528.37 | 0.0425 | 0.0737 | 0.0253 | 0.0170 | 78.25 | 91.08 | 1 | 8191 | 201.364 | 7.670 |
| normal-16384 | pool_n | 8192 | 852.52 | 0.0543 | 0.1034 | 0.0546 | 0.0498 | 78.48 | 91.44 | 4 | 8188 | 101.942 | 7.347 |
| normal-16384 | window_pipe | 8192 | 417.26 | 0.1451 | 0.2269 | 0.0709 | 0.1578 | 78.27 | 90.97 | 4 | 8188 | 51.405 | 7.384 |
| normal-262144 | pipe | 1024 | 708.22 | 0.2796 | 0.4308 | 0.4066 | 0.0239 | 79.30 | 80.67 | 1 | 0 | 0.000 | 6.999 |
| normal-262144 | shared | 1024 | 2453.56 | 0.0921 | 0.1565 | 0.1103 | 0.0285 | 79.12 | 80.48 | 1 | 0 | 0.000 | 8.996 |
| normal-262144 | pool_1 | 1024 | 2543.08 | 0.1511 | 0.2847 | 0.0933 | 0.0245 | 78.95 | 80.62 | 1 | 1023 | 85.396 | 6.346 |
| normal-262144 | pool_n | 1024 | 2887.26 | 0.2867 | 0.4213 | 0.2648 | 0.1421 | 80.52 | 82.16 | 4 | 1020 | 73.915 | 6.434 |
| normal-262144 | window_pipe | 1024 | 890.45 | 0.9878 | 1.4988 | 0.4369 | 1.0767 | 79.91 | 81.83 | 4 | 1020 | 6.880 | 6.492 |
| normal-1048576 | pipe | 256 | 841.27 | 1.1452 | 1.5374 | 1.5124 | 0.0314 | 84.58 | 87.02 | 1 | 0 | 0.000 | 6.361 |
| normal-1048576 | shared | 256 | 3345.48 | 0.2385 | 0.3842 | 0.3546 | 0.0336 | 83.86 | 84.44 | 1 | 0 | 0.000 | 6.396 |
| normal-1048576 | pool_1 | 256 | 4171.36 | 0.3912 | 0.6494 | 0.2989 | 0.0321 | 83.11 | 83.72 | 1 | 255 | 48.044 | 6.398 |
| normal-1048576 | pool_n | 256 | 6746.45 | 0.5693 | 1.1833 | 0.8427 | 0.1704 | 88.89 | 89.75 | 4 | 252 | 26.008 | 6.378 |
| normal-1048576 | window_pipe | 256 | 934.96 | 3.9047 | 5.4912 | 1.5616 | 3.8938 | 88.38 | 90.02 | 4 | 252 | 2.610 | 6.602 |
| normal-4194304 | pipe | 64 | 903.45 | 3.8845 | 6.0512 | 6.0157 | 0.0406 | 107.17 | 108.23 | 1 | 0 | 0.000 | 6.364 |
| normal-4194304 | shared | 64 | 3567.63 | 1.1052 | 1.2709 | 1.1907 | 0.1645 | 103.75 | 104.83 | 1 | 0 | 0.000 | 6.455 |
| normal-4194304 | pool_1 | 64 | 5078.52 | 1.2136 | 1.5648 | 0.8421 | 0.0426 | 98.92 | 100.67 | 1 | 63 | 38.224 | 6.412 |
| normal-4194304 | pool_n | 64 | 7654.42 | 2.1430 | 4.0495 | 3.4234 | 0.3137 | 123.47 | 124.98 | 4 | 60 | 19.188 | 6.360 |
| normal-4194304 | window_pipe | 64 | 936.44 | 14.2278 | 21.4214 | 5.9421 | 15.5482 | 119.58 | 120.03 | 4 | 60 | 1.063 | 6.392 |
| slow-16384 | pipe | 129 | 10.64 | 1.3574 | 1.9772 | 1.9639 | 0.0420 | 78.31 | 78.59 | 1 | 0 | 0.000 | 8.088 |
| slow-16384 | shared | 129 | 11.45 | 1.3083 | 1.6801 | 1.6672 | 0.0452 | 78.41 | 78.56 | 1 | 0 | 0.000 | 6.421 |
| slow-16384 | pool_1 | 129 | 11.11 | 2.6529 | 3.0275 | 1.4688 | 0.0451 | 78.22 | 78.69 | 1 | 128 | 178.360 | 6.666 |
| slow-16384 | pool_n | 129 | 11.76 | 6.4268 | 7.3382 | 5.9242 | 0.0653 | 78.36 | 78.62 | 4 | 125 | 164.846 | 6.468 |
| slow-16384 | window_pipe | 129 | 11.21 | 5.3709 | 6.9987 | 3.5120 | 3.6903 | 78.25 | 78.92 | 4 | 125 | 1.921 | 6.696 |
| slow-1048576 | pipe | 129 | 365.65 | 2.4007 | 3.2367 | 3.2043 | 0.0462 | 84.39 | 86.36 | 1 | 0 | 0.000 | 6.452 |
| slow-1048576 | shared | 129 | 594.78 | 1.5475 | 1.9483 | 1.9147 | 0.0489 | 83.95 | 84.44 | 1 | 0 | 0.000 | 6.414 |
| slow-1048576 | pool_1 | 129 | 632.90 | 2.8953 | 3.6432 | 1.8793 | 0.0473 | 82.86 | 83.38 | 1 | 128 | 194.427 | 6.438 |
| slow-1048576 | pool_n | 129 | 669.15 | 6.9680 | 9.3009 | 7.3910 | 0.1566 | 88.72 | 89.39 | 4 | 125 | 176.786 | 6.533 |
| slow-1048576 | window_pipe | 129 | 391.96 | 9.9720 | 12.2632 | 4.5488 | 7.8084 | 88.66 | 89.66 | 4 | 125 | 1.515 | 6.399 |

All within-block throughput ratios: median [observed min, max], not a confidence interval.

| Case | Numerator / denominator | Ratio |
|---|---|---|
| normal-64 | pool_1 / shared | 0.832 [0.760, 0.850] |
| normal-64 | pool_n / shared | 2.368 [1.619, 3.116] |
| normal-64 | pool_n / pipe | 2.930 [2.029, 3.847] |
| normal-64 | pool_n / window_pipe | 1.214 [0.777, 1.713] |
| normal-1024 | pool_1 / shared | 1.000 [0.836, 1.182] |
| normal-1024 | pool_n / shared | 1.909 [1.206, 2.787] |
| normal-1024 | pool_n / pipe | 1.970 [1.403, 4.889] |
| normal-1024 | pool_n / window_pipe | 1.233 [0.738, 2.096] |
| normal-16384 | pool_1 / shared | 1.044 [0.798, 1.197] |
| normal-16384 | pool_n / shared | 1.549 [1.370, 2.213] |
| normal-16384 | pool_n / pipe | 2.559 [2.138, 3.754] |
| normal-16384 | pool_n / window_pipe | 1.948 [1.886, 2.788] |
| normal-262144 | pool_1 / shared | 1.039 [0.749, 1.367] |
| normal-262144 | pool_n / shared | 1.180 [0.974, 1.716] |
| normal-262144 | pool_n / pipe | 4.284 [3.472, 5.643] |
| normal-262144 | pool_n / window_pipe | 3.189 [2.851, 5.426] |
| normal-1048576 | pool_1 / shared | 1.134 [0.951, 1.911] |
| normal-1048576 | pool_n / shared | 2.024 [0.915, 2.647] |
| normal-1048576 | pool_n / pipe | 8.822 [3.827, 9.521] |
| normal-1048576 | pool_n / window_pipe | 7.682 [3.581, 8.624] |
| normal-4194304 | pool_1 / shared | 1.654 [1.396, 1.756] |
| normal-4194304 | pool_n / shared | 2.219 [2.075, 3.210] |
| normal-4194304 | pool_n / pipe | 8.433 [5.684, 9.575] |
| normal-4194304 | pool_n / window_pipe | 7.910 [5.566, 8.940] |
| slow-16384 | pool_1 / shared | 0.982 [0.910, 1.150] |
| slow-16384 | pool_n / shared | 1.055 [0.957, 1.151] |
| slow-16384 | pool_n / pipe | 1.146 [0.981, 1.322] |
| slow-16384 | pool_n / window_pipe | 1.062 [1.019, 1.087] |
| slow-1048576 | pool_1 / shared | 1.064 [0.941, 1.246] |
| slow-1048576 | pool_n / shared | 1.070 [1.057, 1.282] |
| slow-1048576 | pool_n / pipe | 1.772 [1.681, 1.971] |
| slow-1048576 | pool_n / window_pipe | 1.713 [1.610, 1.960] |

- Identical float32 recipe, sequence order, warmup count, message count and consumer delay within each case; full exact-value validation plus CRC and ACK in every profile. No drops or outlier exclusions.
- pipe/shared are the existing stop-and-wait protocols with one payload in flight. shared copies a staging array into its slot. pool_1/pool_n fill loaned shared slots in place. window_pipe fills local loaned slots in place and uses the same publication/release protocol and capacity as pool_n. All Pipe payloads use recv_bytes plus a copy to a preallocated consumer target.
- Pool and windowed Pipe carry additional slot/generation metadata. Pool_n versus legacy baselines includes changes in copy count, window and protocol. The equal-window Pipe control separates window size from transport more closely, but receiver allocation/copy behavior still differs. No end-to-end zero-copy claim: base/reference generation, validation and CRC remain included.
- Closed-loop, finite SPSC saturation traces, not a shared arrival schedule, inference service or production capacity estimate. Every block rotates profile order; five blocks balance all five positions. Partial subsets are never called a full grid.
- ACK-observed latency starts before loan acquisition or legacy generation and ends when its valid ACK is processed by the producer. Pool latency includes capacity waiting and ACK collection scheduling. Capacity-reclaim counts mean no locally free slot, even if an ACK is already queued; reclaim time includes ACK processing, not only consumer waiting. Admitted-to-ready timing starts at slot acquisition (legacy generation start) and ends in the consumer after full validation and any declared delay, before sending ACK. Attempt-to-ready additionally includes admission waiting. ACK-observation lag includes ACK transmission and producer scheduling/reclamation. These are distinct clocks, not application latency under a common arrival schedule or pure transport RTT. Drain of the final partial window is included in throughput.
- Workers are fresh per trial; eight transfers warm protocol state before measurement, fully drained before start. Artificial consumer delay is applied only to measured messages after validation and before ACK in all profiles; requested sleep is not exact service time.
- RSS samples include two worker runtimes, arrays, touched pool pages, records and result serialization; baseline is after warmup. Shared pages may be counted twice. Sequential 5 ms requested samples can miss peaks; actual gaps are retained. Controller/resource tracker are excluded. Pool payload allocation is bounded; per-message evidence records still grow with the finite message count. RSS is not unique physical memory or total deployment size.
- Single host, fixed case order, uncontrolled CPU/cache/thermals and short trials. Ratios are medians of all within-block ratios with observed min/max, not confidence intervals or universal effects. Controller-managed worker-crash cleanup is tested; controller kill and power loss are outside the guarantee.


Full JSON, offline HTML and raw exchanges are retained locally with the run ID in receipt.json.
