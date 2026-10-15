Native macOS ARM64; dedicated Colima VM stopped during measurement.

# Bounded IPC pool comparison

Five-profile verified exchanges; all blocks retained. ACK-observed latency includes loan waiting and ACK collection; admitted-to-ready and ACK-observation lag are reported separately. RSS is sampled two-worker RSS, not unique physical RAM.

| Case | Profile | Count | MiB/s median | ACK-observed p50 ms | ACK-observed p95 ms | Admitted-to-ready p95 ms | ACK-observation lag p95 ms | Baseline RSS MiB median | Peak RSS MiB max | Slots max | ACK-reclaim events median | Reclaim ms total median | Max RSS gap ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal-64 | pipe | 8192 | 2.37 | 0.0215 | 0.0440 | 0.0285 | 0.0191 | 78.20 | 86.25 | 1 | 0 | 0.000 | 7.461 |
| normal-64 | shared | 8192 | 2.64 | 0.0188 | 0.0386 | 0.0240 | 0.0193 | 78.28 | 86.12 | 1 | 0 | 0.000 | 8.147 |
| normal-64 | pool_1 | 8192 | 2.35 | 0.0384 | 0.0831 | 0.0282 | 0.0206 | 78.34 | 90.80 | 1 | 8191 | 178.729 | 8.548 |
| normal-64 | pool_n | 8192 | 5.32 | 0.0371 | 0.0991 | 0.0490 | 0.0459 | 78.20 | 91.12 | 4 | 8188 | 61.521 | 12.346 |
| normal-64 | window_pipe | 8192 | 5.31 | 0.0405 | 0.1011 | 0.0544 | 0.0480 | 78.34 | 90.70 | 4 | 8188 | 56.706 | 7.915 |
| normal-1024 | pipe | 8192 | 28.75 | 0.0250 | 0.0450 | 0.0287 | 0.0198 | 78.16 | 85.80 | 1 | 0 | 0.000 | 7.637 |
| normal-1024 | shared | 8192 | 42.39 | 0.0191 | 0.0386 | 0.0259 | 0.0188 | 78.20 | 86.39 | 1 | 0 | 0.000 | 7.549 |
| normal-1024 | pool_1 | 8192 | 36.45 | 0.0417 | 0.0777 | 0.0259 | 0.0199 | 78.22 | 90.80 | 1 | 8191 | 180.825 | 17.907 |
| normal-1024 | pool_n | 8192 | 77.11 | 0.0353 | 0.0992 | 0.0492 | 0.0453 | 78.25 | 90.83 | 4 | 8188 | 60.476 | 12.819 |
| normal-1024 | window_pipe | 8192 | 50.07 | 0.0519 | 0.1225 | 0.0591 | 0.0545 | 78.19 | 90.75 | 4 | 8188 | 109.574 | 8.334 |
| normal-16384 | pipe | 8192 | 333.55 | 0.0393 | 0.0643 | 0.0499 | 0.0175 | 78.23 | 86.25 | 1 | 0 | 0.000 | 7.084 |
| normal-16384 | shared | 8192 | 574.03 | 0.0228 | 0.0427 | 0.0267 | 0.0185 | 78.34 | 86.55 | 1 | 0 | 0.000 | 7.308 |
| normal-16384 | pool_1 | 8192 | 536.24 | 0.0429 | 0.0811 | 0.0284 | 0.0190 | 78.41 | 91.20 | 1 | 8191 | 195.466 | 7.990 |
| normal-16384 | pool_n | 8192 | 965.75 | 0.0526 | 0.1121 | 0.0555 | 0.0494 | 78.33 | 91.02 | 4 | 8188 | 87.929 | 6.981 |
| normal-16384 | window_pipe | 8192 | 421.92 | 0.1165 | 0.2316 | 0.0714 | 0.1598 | 78.38 | 90.89 | 4 | 8188 | 50.179 | 11.400 |
| normal-262144 | pipe | 1024 | 787.84 | 0.2783 | 0.4181 | 0.4014 | 0.0245 | 79.28 | 80.62 | 1 | 0 | 0.000 | 9.725 |
| normal-262144 | shared | 1024 | 2485.46 | 0.0950 | 0.1575 | 0.1194 | 0.0263 | 79.33 | 80.42 | 1 | 0 | 0.000 | 6.387 |
| normal-262144 | pool_1 | 1024 | 2718.87 | 0.1559 | 0.2699 | 0.0942 | 0.0248 | 79.14 | 80.95 | 1 | 1023 | 76.820 | 6.487 |
| normal-262144 | pool_n | 1024 | 3965.90 | 0.2723 | 0.4356 | 0.2477 | 0.1846 | 80.56 | 82.33 | 4 | 1020 | 48.139 | 6.701 |
| normal-262144 | window_pipe | 1024 | 896.57 | 0.9467 | 1.4593 | 0.4319 | 1.0519 | 79.95 | 81.70 | 4 | 1020 | 7.396 | 6.466 |
| normal-1048576 | pipe | 256 | 880.09 | 1.0376 | 1.4725 | 1.4482 | 0.0302 | 84.73 | 86.81 | 1 | 0 | 0.000 | 6.546 |
| normal-1048576 | shared | 256 | 3435.56 | 0.2386 | 0.4145 | 0.3752 | 0.0301 | 83.84 | 84.70 | 1 | 0 | 0.000 | 6.674 |
| normal-1048576 | pool_1 | 256 | 3770.53 | 0.3935 | 0.6269 | 0.3023 | 0.0320 | 82.80 | 83.58 | 1 | 255 | 56.076 | 6.440 |
| normal-1048576 | pool_n | 256 | 5963.03 | 0.6285 | 1.3097 | 0.9467 | 0.3356 | 88.81 | 89.64 | 4 | 252 | 30.703 | 6.438 |
| normal-1048576 | window_pipe | 256 | 951.01 | 4.2498 | 5.2244 | 1.4982 | 3.7769 | 87.98 | 89.58 | 4 | 252 | 2.475 | 6.341 |
| normal-4194304 | pipe | 64 | 897.74 | 3.9192 | 6.1074 | 6.0678 | 0.0460 | 106.36 | 107.98 | 1 | 0 | 0.000 | 6.355 |
| normal-4194304 | shared | 64 | 3706.91 | 1.1088 | 1.2253 | 1.1940 | 0.0411 | 103.11 | 104.75 | 1 | 0 | 0.000 | 6.392 |
| normal-4194304 | pool_1 | 64 | 5022.08 | 1.3924 | 1.6314 | 0.8920 | 0.0567 | 99.70 | 100.88 | 1 | 63 | 38.441 | 6.407 |
| normal-4194304 | pool_n | 64 | 7827.02 | 2.1118 | 3.0556 | 2.6301 | 0.1559 | 123.59 | 124.75 | 4 | 60 | 19.461 | 6.448 |
| normal-4194304 | window_pipe | 64 | 961.40 | 16.9146 | 20.6690 | 5.9742 | 15.0400 | 119.80 | 120.17 | 4 | 60 | 1.063 | 6.384 |
| slow-16384 | pipe | 129 | 11.36 | 1.3581 | 1.4309 | 1.3977 | 0.0474 | 78.25 | 78.58 | 1 | 0 | 0.000 | 6.451 |
| slow-16384 | shared | 129 | 11.40 | 1.3322 | 1.5711 | 1.5238 | 0.0544 | 78.28 | 78.55 | 1 | 0 | 0.000 | 6.435 |
| slow-16384 | pool_1 | 129 | 11.61 | 2.6567 | 2.8221 | 1.3922 | 0.0541 | 78.17 | 78.70 | 1 | 128 | 170.398 | 6.603 |
| slow-16384 | pool_n | 129 | 11.99 | 6.4644 | 6.9887 | 5.5005 | 0.0672 | 78.39 | 78.97 | 4 | 125 | 161.059 | 8.627 |
| slow-16384 | window_pipe | 129 | 11.74 | 5.3236 | 5.4758 | 2.6812 | 2.8496 | 78.17 | 78.41 | 4 | 125 | 2.221 | 6.431 |
| slow-1048576 | pipe | 129 | 389.90 | 2.4324 | 3.1592 | 3.1324 | 0.0488 | 84.64 | 86.75 | 1 | 0 | 0.000 | 6.504 |
| slow-1048576 | shared | 129 | 606.14 | 1.5694 | 1.8127 | 1.7573 | 0.0629 | 84.02 | 84.58 | 1 | 0 | 0.000 | 7.642 |
| slow-1048576 | pool_1 | 129 | 652.63 | 2.9030 | 3.3530 | 1.7377 | 0.0501 | 83.17 | 83.59 | 1 | 128 | 189.110 | 6.356 |
| slow-1048576 | pool_n | 129 | 692.97 | 6.8709 | 7.6292 | 6.0988 | 0.0607 | 88.81 | 89.47 | 4 | 125 | 172.350 | 6.416 |
| slow-1048576 | window_pipe | 129 | 396.34 | 9.8710 | 12.0672 | 4.4866 | 7.6556 | 88.98 | 89.78 | 4 | 125 | 1.798 | 6.345 |

All within-block throughput ratios: median [observed min, max], not a confidence interval.

| Case | Numerator / denominator | Ratio |
|---|---|---|
| normal-64 | pool_1 / shared | 0.944 [0.700, 1.081] |
| normal-64 | pool_n / shared | 1.964 [1.206, 2.387] |
| normal-64 | pool_n / pipe | 2.260 [1.086, 2.452] |
| normal-64 | pool_n / window_pipe | 1.005 [0.491, 1.341] |
| normal-1024 | pool_1 / shared | 0.821 [0.505, 1.113] |
| normal-1024 | pool_n / shared | 2.034 [0.918, 2.344] |
| normal-1024 | pool_n / pipe | 2.957 [1.534, 3.363] |
| normal-1024 | pool_n / window_pipe | 1.327 [0.936, 2.046] |
| normal-16384 | pool_1 / shared | 0.889 [0.715, 1.072] |
| normal-16384 | pool_n / shared | 1.682 [1.227, 2.353] |
| normal-16384 | pool_n / pipe | 2.895 [2.236, 3.975] |
| normal-16384 | pool_n / window_pipe | 2.234 [1.822, 3.355] |
| normal-262144 | pool_1 / shared | 1.221 [0.692, 1.663] |
| normal-262144 | pool_n / shared | 1.605 [1.545, 2.331] |
| normal-262144 | pool_n / pipe | 5.237 [4.741, 8.052] |
| normal-262144 | pool_n / window_pipe | 4.683 [3.945, 6.236] |
| normal-1048576 | pool_1 / shared | 1.080 [0.448, 1.975] |
| normal-1048576 | pool_n / shared | 1.736 [0.848, 2.253] |
| normal-1048576 | pool_n / pipe | 6.673 [4.144, 7.980] |
| normal-1048576 | pool_n / window_pipe | 6.091 [3.460, 7.385] |
| normal-4194304 | pool_1 / shared | 1.355 [1.259, 1.377] |
| normal-4194304 | pool_n / shared | 1.910 [0.734, 2.332] |
| normal-4194304 | pool_n / pipe | 8.708 [3.061, 9.567] |
| normal-4194304 | pool_n / window_pipe | 7.875 [2.829, 9.317] |
| slow-16384 | pool_1 / shared | 1.018 [0.981, 1.080] |
| slow-16384 | pool_n / shared | 1.048 [1.024, 1.109] |
| slow-16384 | pool_n / pipe | 1.055 [1.037, 1.215] |
| slow-16384 | pool_n / window_pipe | 1.033 [1.017, 1.247] |
| slow-1048576 | pool_1 / shared | 1.061 [1.026, 1.165] |
| slow-1048576 | pool_n / shared | 1.150 [1.056, 1.159] |
| slow-1048576 | pool_n / pipe | 1.777 [1.699, 1.932] |
| slow-1048576 | pool_n / window_pipe | 1.765 [1.618, 2.118] |

- Identical float32 recipe, sequence order, warmup count, message count and consumer delay within each case; full exact-value validation plus CRC and ACK in every profile. No drops or outlier exclusions.
- pipe/shared are the existing stop-and-wait protocols with one payload in flight. shared copies a staging array into its slot. pool_1/pool_n fill loaned shared slots in place. window_pipe fills local loaned slots in place and uses the same publication/release protocol and capacity as pool_n. All Pipe payloads use recv_bytes plus a copy to a preallocated consumer target.
- Pool and windowed Pipe carry additional slot/generation metadata. Pool_n versus legacy baselines includes changes in copy count, window and protocol. The equal-window Pipe control separates window size from transport more closely, but receiver allocation/copy behavior still differs. No end-to-end zero-copy claim: base/reference generation, validation and CRC remain included.
- Closed-loop, finite SPSC saturation traces, not a shared arrival schedule, inference service or production capacity estimate. Every block rotates profile order; five blocks balance all five positions. Partial subsets are never called a full grid.
- ACK-observed latency starts before loan acquisition or legacy generation and ends when its valid ACK is processed by the producer. Pool latency includes capacity waiting and ACK collection scheduling. Capacity-reclaim counts mean no locally free slot, even if an ACK is already queued; reclaim time includes ACK processing, not only consumer waiting. Admitted-to-ready timing starts at slot acquisition (legacy generation start) and ends in the consumer after full validation and any declared delay, before sending ACK. Attempt-to-ready additionally includes admission waiting. ACK-observation lag includes ACK transmission and producer scheduling/reclamation. These are distinct clocks, not application latency under a common arrival schedule or pure transport RTT. Drain of the final partial window is included in throughput.
- Workers are fresh per trial; eight transfers warm protocol state before measurement, fully drained before start. Artificial consumer delay is applied only to measured messages after validation and before ACK in all profiles; requested sleep is not exact service time.
- RSS samples include two worker runtimes, arrays, touched pool pages, records and result serialization; baseline is after warmup. Shared pages may be counted twice. Sequential 5 ms requested samples can miss peaks; actual gaps are retained. Controller/resource tracker are excluded. Pool payload allocation is bounded; per-message evidence records still grow with the finite message count. RSS is not unique physical memory or total deployment size.
- Single host, fixed case order, uncontrolled CPU/cache/thermals and short trials. Ratios are medians of all within-block ratios with observed min/max, not confidence intervals or universal effects. Controller-managed worker-crash cleanup is tested; controller kill and power loss are outside the guarantee.


Full JSON, offline HTML and raw exchanges are retained locally with the run ID in receipt.json.
