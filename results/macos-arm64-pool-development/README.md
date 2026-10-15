# Bounded IPC pool comparison

Five-profile verified exchanges; all blocks retained. Completion latency includes loan waiting and ACK collection. RSS is sampled two-worker RSS, not unique physical RAM.

| Case | Profile | Count | MiB/s median | Completion p50 ms | Completion p95 ms | Baseline RSS MiB median | Peak RSS MiB max | Slots max | ACK-reclaim events median | Reclaim ms total median |
|---|---|---|---|---|---|---|---|---|---|---|
| normal-64 | pipe | 8192 | 2.34 | 0.0217 | 0.0413 | 78.12 | 85.19 | 1 | 0 | 0.000 |
| normal-64 | shared | 8192 | 2.55 | 0.0196 | 0.0352 | 78.14 | 85.39 | 1 | 0 | 0.000 |
| normal-64 | pool_1 | 8192 | 2.35 | 0.0383 | 0.0699 | 78.27 | 89.67 | 1 | 8191 | 172.572 |
| normal-64 | pool_n | 8192 | 6.33 | 0.0360 | 0.0933 | 78.05 | 88.97 | 4 | 8188 | 50.027 |
| normal-64 | window_pipe | 8192 | 4.05 | 0.0428 | 0.1057 | 78.14 | 89.00 | 4 | 8188 | 77.851 |
| normal-1024 | pipe | 8192 | 37.51 | 0.0222 | 0.0402 | 78.28 | 85.06 | 1 | 0 | 0.000 |
| normal-1024 | shared | 8192 | 42.11 | 0.0185 | 0.0365 | 78.22 | 85.42 | 1 | 0 | 0.000 |
| normal-1024 | pool_1 | 8192 | 39.20 | 0.0388 | 0.0676 | 78.28 | 89.22 | 1 | 8191 | 167.357 |
| normal-1024 | pool_n | 8192 | 91.33 | 0.0367 | 0.0968 | 78.28 | 89.44 | 4 | 8188 | 58.366 |
| normal-1024 | window_pipe | 8192 | 68.56 | 0.0525 | 0.1118 | 78.25 | 89.41 | 4 | 8188 | 65.393 |
| normal-16384 | pipe | 8192 | 353.03 | 0.0402 | 0.0600 | 78.23 | 85.30 | 1 | 0 | 0.000 |
| normal-16384 | shared | 8192 | 630.09 | 0.0208 | 0.0398 | 78.23 | 85.66 | 1 | 0 | 0.000 |
| normal-16384 | pool_1 | 8192 | 565.39 | 0.0418 | 0.0804 | 78.25 | 89.30 | 1 | 8191 | 183.015 |
| normal-16384 | pool_n | 8192 | 1016.56 | 0.0527 | 0.1091 | 78.34 | 89.92 | 4 | 8188 | 86.463 |
| normal-16384 | window_pipe | 8192 | 407.33 | 0.1429 | 0.2360 | 78.22 | 89.31 | 4 | 8188 | 51.366 |
| normal-262144 | pipe | 1024 | 794.46 | 0.2816 | 0.4312 | 79.17 | 80.41 | 1 | 0 | 0.000 |
| normal-262144 | shared | 1024 | 2543.58 | 0.0816 | 0.1357 | 79.14 | 80.39 | 1 | 0 | 0.000 |
| normal-262144 | pool_1 | 1024 | 2723.80 | 0.1582 | 0.2895 | 78.92 | 80.52 | 1 | 1023 | 78.499 |
| normal-262144 | pool_n | 1024 | 3918.14 | 0.2827 | 0.4701 | 80.48 | 82.12 | 4 | 1020 | 48.724 |
| normal-262144 | window_pipe | 1024 | 877.83 | 1.0292 | 1.5345 | 80.14 | 81.92 | 4 | 1020 | 7.646 |
| normal-1048576 | pipe | 256 | 801.75 | 1.1007 | 1.5360 | 85.09 | 86.44 | 1 | 0 | 0.000 |
| normal-1048576 | shared | 256 | 3491.98 | 0.2553 | 0.3989 | 84.06 | 84.44 | 1 | 0 | 0.000 |
| normal-1048576 | pool_1 | 256 | 4647.81 | 0.3508 | 0.5813 | 82.81 | 83.70 | 1 | 255 | 43.189 |
| normal-1048576 | pool_n | 256 | 3612.89 | 0.6126 | 3.2740 | 88.80 | 89.66 | 4 | 252 | 58.625 |
| normal-1048576 | window_pipe | 256 | 962.79 | 4.1831 | 5.5172 | 88.08 | 89.48 | 4 | 252 | 3.037 |
| normal-4194304 | pipe | 64 | 892.25 | 3.9935 | 5.8773 | 107.11 | 107.97 | 1 | 0 | 0.000 |
| normal-4194304 | shared | 64 | 3847.13 | 1.0867 | 1.2238 | 103.48 | 104.98 | 1 | 0 | 0.000 |
| normal-4194304 | pool_1 | 64 | 5080.35 | 1.2549 | 1.5053 | 99.11 | 100.72 | 1 | 63 | 38.174 |
| normal-4194304 | pool_n | 64 | 8346.35 | 2.1337 | 2.8646 | 123.62 | 124.81 | 4 | 60 | 17.958 |
| normal-4194304 | window_pipe | 64 | 942.15 | 14.6548 | 21.0444 | 119.75 | 120.05 | 4 | 60 | 1.493 |
| slow-16384 | pipe | 129 | 11.49 | 1.3473 | 1.4208 | 78.42 | 78.58 | 1 | 0 | 0.000 |
| slow-16384 | shared | 129 | 11.50 | 1.3177 | 1.6827 | 78.22 | 78.59 | 1 | 0 | 0.000 |
| slow-16384 | pool_1 | 129 | 11.55 | 2.6418 | 3.2672 | 78.38 | 78.55 | 1 | 128 | 171.717 |
| slow-16384 | pool_n | 129 | 11.65 | 6.4517 | 7.4533 | 78.25 | 78.50 | 4 | 125 | 166.244 |
| slow-16384 | window_pipe | 129 | 11.44 | 5.3137 | 6.6322 | 78.27 | 78.75 | 4 | 125 | 1.948 |
| slow-1048576 | pipe | 129 | 393.79 | 2.3912 | 3.1619 | 84.89 | 86.83 | 1 | 0 | 0.000 |
| slow-1048576 | shared | 129 | 616.39 | 1.5671 | 1.7814 | 83.77 | 84.06 | 1 | 0 | 0.000 |
| slow-1048576 | pool_1 | 129 | 616.51 | 3.0547 | 3.5523 | 82.72 | 83.41 | 1 | 128 | 199.182 |
| slow-1048576 | pool_n | 129 | 667.12 | 7.1412 | 9.0314 | 89.05 | 89.47 | 4 | 125 | 177.485 |
| slow-1048576 | window_pipe | 129 | 410.62 | 9.1815 | 11.7153 | 88.61 | 89.66 | 4 | 125 | 2.316 |

All within-block throughput ratios: median [observed min, max], not a confidence interval.

| Case | Numerator / denominator | Ratio |
|---|---|---|
| normal-64 | pool_1 / shared | 0.895 [0.702, 1.388] |
| normal-64 | pool_n / shared | 2.145 [1.280, 3.708] |
| normal-64 | pool_n / pipe | 2.503 [1.353, 2.889] |
| normal-64 | pool_n / window_pipe | 1.460 [0.807, 1.955] |
| normal-1024 | pool_1 / shared | 0.913 [0.857, 1.052] |
| normal-1024 | pool_n / shared | 2.186 [1.997, 2.510] |
| normal-1024 | pool_n / pipe | 2.390 [2.329, 3.402] |
| normal-1024 | pool_n / window_pipe | 1.300 [1.024, 1.432] |
| normal-16384 | pool_1 / shared | 0.903 [0.693, 1.130] |
| normal-16384 | pool_n / shared | 1.652 [0.865, 1.887] |
| normal-16384 | pool_n / pipe | 2.885 [1.565, 3.499] |
| normal-16384 | pool_n / window_pipe | 2.481 [1.360, 2.896] |
| normal-262144 | pool_1 / shared | 0.947 [0.810, 1.552] |
| normal-262144 | pool_n / shared | 1.577 [0.627, 2.925] |
| normal-262144 | pool_n / pipe | 5.073 [2.601, 7.014] |
| normal-262144 | pool_n / window_pipe | 4.289 [2.354, 7.026] |
| normal-1048576 | pool_1 / shared | 1.370 [0.568, 2.360] |
| normal-1048576 | pool_n / shared | 1.012 [0.668, 2.025] |
| normal-1048576 | pool_n / pipe | 4.506 [2.963, 7.006] |
| normal-1048576 | pool_n / window_pipe | 4.057 [2.422, 6.342] |
| normal-4194304 | pool_1 / shared | 1.239 [0.777, 2.308] |
| normal-4194304 | pool_n / shared | 2.040 [0.891, 3.354] |
| normal-4194304 | pool_n / pipe | 9.045 [3.916, 9.461] |
| normal-4194304 | pool_n / window_pipe | 8.887 [3.542, 9.293] |
| slow-16384 | pool_1 / shared | 0.986 [0.876, 1.010] |
| slow-16384 | pool_n / shared | 1.003 [0.918, 1.058] |
| slow-16384 | pool_n / pipe | 1.043 [0.952, 1.111] |
| slow-16384 | pool_n / window_pipe | 1.019 [0.911, 1.072] |
| slow-1048576 | pool_1 / shared | 1.014 [0.887, 1.068] |
| slow-1048576 | pool_n / shared | 1.080 [1.022, 1.122] |
| slow-1048576 | pool_n / pipe | 1.694 [1.615, 1.999] |
| slow-1048576 | pool_n / window_pipe | 1.641 [1.443, 2.970] |

- Identical float32 recipe, sequence order, warmup count, message count and consumer delay within each case; full exact-value validation plus CRC and ACK in every profile. No drops or outlier exclusions.
- pipe/shared are the existing stop-and-wait protocols with one payload in flight. shared copies a staging array into its slot. pool_1/pool_n fill loaned shared slots in place. window_pipe fills local loaned slots in place and uses the same publication/release protocol and capacity as pool_n. All Pipe payloads use recv_bytes plus a copy to a preallocated consumer target.
- Pool and windowed Pipe carry additional slot/generation metadata. Pool_n versus legacy baselines includes changes in copy count, window and protocol. The equal-window Pipe control separates window size from transport more closely, but receiver allocation/copy behavior still differs. No end-to-end zero-copy claim: base/reference generation, validation and CRC remain included.
- Closed-loop, finite SPSC saturation traces, not a shared arrival schedule, inference service or production capacity estimate. Every block rotates profile order; five blocks balance all five positions. Partial subsets are never called a full grid.
- Message completion latency starts before loan acquisition or legacy generation and ends when its valid ACK is processed by the producer. Pool latency includes capacity waiting and ACK collection scheduling. Capacity-reclaim counts mean no locally free slot, even if an ACK is already queued; reclaim time includes ACK processing, not only consumer waiting. It is not transport RTT or consumer service time. Drain of the final partial window is included in throughput.
- Workers are fresh per trial; eight transfers warm protocol state before measurement, fully drained before start. Artificial consumer delay is applied only to measured messages after validation and before ACK in all profiles; requested sleep is not exact service time.
- RSS samples include two worker runtimes, arrays, touched pool pages, records and result serialization; baseline is after warmup. Shared pages may be counted twice. Sequential 5 ms requested samples can miss peaks; actual gaps are retained. Controller/resource tracker are excluded. Pool payload allocation is bounded; per-message evidence records still grow with the finite message count. RSS is not unique physical memory or total deployment size.
- Single host, fixed case order, uncontrolled CPU/cache/thermals and short trials. Ratios are medians of all within-block ratios with observed min/max, not confidence intervals or universal effects. Controller-managed worker-crash cleanup is tested; controller kill and power loss are outside the guarantee.

[JSON evidence](report.json) · [Offline HTML](report.html)
