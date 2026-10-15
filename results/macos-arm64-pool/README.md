# Bounded IPC pool comparison

Five-profile verified exchanges; all blocks retained. Completion latency includes loan waiting and ACK collection. RSS is sampled two-worker RSS, not unique physical RAM.

| Case | Profile | Count | MiB/s median | Completion p50 ms | Completion p95 ms | Baseline RSS MiB median | Peak RSS MiB max | Slots max | ACK-reclaim events median | Reclaim ms total median |
|---|---|---|---|---|---|---|---|---|---|---|
| normal-64 | pipe | 8192 | 2.64 | 0.0198 | 0.0370 | 78.16 | 85.31 | 1 | 0 | 0.000 |
| normal-64 | shared | 8192 | 2.57 | 0.0195 | 0.0362 | 78.08 | 85.12 | 1 | 0 | 0.000 |
| normal-64 | pool_1 | 8192 | 2.36 | 0.0380 | 0.0692 | 78.09 | 88.86 | 1 | 8191 | 173.870 |
| normal-64 | pool_n | 8192 | 5.42 | 0.0353 | 0.0906 | 78.09 | 89.50 | 4 | 8188 | 61.943 |
| normal-64 | window_pipe | 8192 | 4.91 | 0.0401 | 0.1054 | 78.17 | 89.14 | 4 | 8188 | 62.576 |
| normal-1024 | pipe | 8192 | 36.63 | 0.0197 | 0.0383 | 78.14 | 85.25 | 1 | 0 | 0.000 |
| normal-1024 | shared | 8192 | 42.55 | 0.0191 | 0.0339 | 78.14 | 85.45 | 1 | 0 | 0.000 |
| normal-1024 | pool_1 | 8192 | 40.56 | 0.0377 | 0.0635 | 78.23 | 88.81 | 1 | 8191 | 161.426 |
| normal-1024 | pool_n | 8192 | 94.28 | 0.0359 | 0.0935 | 78.31 | 89.28 | 4 | 8188 | 56.212 |
| normal-1024 | window_pipe | 8192 | 60.30 | 0.0421 | 0.1073 | 78.14 | 89.08 | 4 | 8188 | 89.616 |
| normal-16384 | pipe | 8192 | 310.93 | 0.0390 | 0.0569 | 78.23 | 85.25 | 1 | 0 | 0.000 |
| normal-16384 | shared | 8192 | 585.23 | 0.0224 | 0.0416 | 78.23 | 85.47 | 1 | 0 | 0.000 |
| normal-16384 | pool_1 | 8192 | 535.07 | 0.0429 | 0.0769 | 78.12 | 89.33 | 1 | 8191 | 196.036 |
| normal-16384 | pool_n | 8192 | 1014.97 | 0.0534 | 0.0987 | 78.30 | 89.86 | 4 | 8188 | 88.520 |
| normal-16384 | window_pipe | 8192 | 405.00 | 0.1127 | 0.2308 | 78.25 | 89.58 | 4 | 8188 | 50.713 |
| normal-262144 | pipe | 1024 | 715.89 | 0.2786 | 0.4264 | 79.12 | 80.45 | 1 | 0 | 0.000 |
| normal-262144 | shared | 1024 | 2626.57 | 0.0785 | 0.1326 | 79.14 | 80.22 | 1 | 0 | 0.000 |
| normal-262144 | pool_1 | 1024 | 2560.11 | 0.1574 | 0.2835 | 78.80 | 80.38 | 1 | 1023 | 82.724 |
| normal-262144 | pool_n | 1024 | 4080.32 | 0.2856 | 0.4009 | 80.50 | 81.98 | 4 | 1020 | 48.472 |
| normal-262144 | window_pipe | 1024 | 887.31 | 1.0178 | 1.5293 | 79.95 | 81.78 | 4 | 1020 | 7.415 |
| normal-1048576 | pipe | 256 | 871.29 | 1.0855 | 1.4820 | 85.97 | 87.03 | 1 | 0 | 0.000 |
| normal-1048576 | shared | 256 | 3385.20 | 0.2411 | 0.3742 | 83.72 | 84.28 | 1 | 0 | 0.000 |
| normal-1048576 | pool_1 | 256 | 4408.55 | 0.3451 | 0.6418 | 82.94 | 83.75 | 1 | 255 | 46.142 |
| normal-1048576 | pool_n | 256 | 7866.97 | 0.5692 | 0.6994 | 88.72 | 89.39 | 4 | 252 | 21.230 |
| normal-1048576 | window_pipe | 256 | 961.09 | 4.3121 | 5.3408 | 88.23 | 89.55 | 4 | 252 | 2.636 |
| normal-4194304 | pipe | 64 | 907.43 | 3.8193 | 5.9280 | 107.53 | 107.89 | 1 | 0 | 0.000 |
| normal-4194304 | shared | 64 | 3855.39 | 1.0779 | 1.2449 | 103.59 | 104.83 | 1 | 0 | 0.000 |
| normal-4194304 | pool_1 | 64 | 5579.26 | 1.1502 | 1.4885 | 99.55 | 100.94 | 1 | 63 | 34.341 |
| normal-4194304 | pool_n | 64 | 5773.42 | 2.4022 | 5.9020 | 123.56 | 124.66 | 4 | 60 | 31.315 |
| normal-4194304 | window_pipe | 64 | 918.54 | 16.4948 | 21.3838 | 119.81 | 119.94 | 4 | 60 | 1.144 |
| slow-16384 | pipe | 129 | 10.99 | 1.3386 | 1.4064 | 78.38 | 78.47 | 1 | 0 | 0.000 |
| slow-16384 | shared | 129 | 11.61 | 1.3097 | 1.5253 | 78.31 | 78.48 | 1 | 0 | 0.000 |
| slow-16384 | pool_1 | 129 | 11.14 | 2.6551 | 3.2558 | 78.12 | 78.48 | 1 | 128 | 177.815 |
| slow-16384 | pool_n | 129 | 12.05 | 6.3612 | 7.5911 | 78.47 | 78.73 | 4 | 125 | 160.870 |
| slow-16384 | window_pipe | 129 | 11.12 | 5.3127 | 6.7110 | 78.25 | 78.50 | 4 | 125 | 2.045 |
| slow-1048576 | pipe | 129 | 386.59 | 2.4095 | 3.1734 | 85.00 | 86.44 | 1 | 0 | 0.000 |
| slow-1048576 | shared | 129 | 599.88 | 1.5434 | 1.9146 | 83.69 | 84.22 | 1 | 0 | 0.000 |
| slow-1048576 | pool_1 | 129 | 648.18 | 2.9575 | 3.5277 | 82.97 | 83.39 | 1 | 128 | 190.921 |
| slow-1048576 | pool_n | 129 | 673.96 | 6.9604 | 8.6189 | 88.78 | 89.28 | 4 | 125 | 177.254 |
| slow-1048576 | window_pipe | 129 | 404.59 | 9.6199 | 12.0908 | 88.30 | 89.44 | 4 | 125 | 1.758 |

All within-block throughput ratios: median [observed min, max], not a confidence interval.

| Case | Numerator / denominator | Ratio |
|---|---|---|
| normal-64 | pool_1 / shared | 0.929 [0.583, 1.120] |
| normal-64 | pool_n / shared | 2.096 [1.240, 2.634] |
| normal-64 | pool_n / pipe | 2.066 [1.296, 3.787] |
| normal-64 | pool_n / window_pipe | 1.020 [0.745, 1.429] |
| normal-1024 | pool_1 / shared | 0.951 [0.686, 1.191] |
| normal-1024 | pool_n / shared | 2.261 [1.329, 2.355] |
| normal-1024 | pool_n / pipe | 2.516 [1.419, 2.843] |
| normal-1024 | pool_n / window_pipe | 1.301 [0.968, 1.624] |
| normal-16384 | pool_1 / shared | 0.896 [0.777, 1.105] |
| normal-16384 | pool_n / shared | 1.729 [1.297, 2.526] |
| normal-16384 | pool_n / pipe | 3.394 [2.402, 4.195] |
| normal-16384 | pool_n / window_pipe | 2.598 [2.010, 3.221] |
| normal-262144 | pool_1 / shared | 0.889 [0.881, 1.143] |
| normal-262144 | pool_n / shared | 1.943 [1.350, 2.398] |
| normal-262144 | pool_n / pipe | 5.283 [4.949, 8.799] |
| normal-262144 | pool_n / window_pipe | 5.303 [4.371, 7.025] |
| normal-1048576 | pool_1 / shared | 1.302 [0.621, 1.895] |
| normal-1048576 | pool_n / shared | 2.309 [1.341, 3.489] |
| normal-1048576 | pool_n / pipe | 9.134 [6.499, 9.968] |
| normal-1048576 | pool_n / window_pipe | 8.399 [5.881, 8.518] |
| normal-4194304 | pool_1 / shared | 1.442 [1.363, 1.615] |
| normal-4194304 | pool_n / shared | 1.483 [0.833, 2.381] |
| normal-4194304 | pool_n / pipe | 7.874 [3.458, 9.434] |
| normal-4194304 | pool_n / window_pipe | 5.921 [3.527, 9.319] |
| slow-16384 | pool_1 / shared | 0.959 [0.914, 1.036] |
| slow-16384 | pool_n / shared | 1.022 [0.998, 1.044] |
| slow-16384 | pool_n / pipe | 1.054 [1.035, 1.403] |
| slow-16384 | pool_n / window_pipe | 1.089 [1.018, 1.105] |
| slow-1048576 | pool_1 / shared | 1.096 [1.014, 1.312] |
| slow-1048576 | pool_n / shared | 1.086 [1.074, 1.405] |
| slow-1048576 | pool_n / pipe | 1.785 [1.693, 1.983] |
| slow-1048576 | pool_n / window_pipe | 1.678 [1.606, 1.734] |

- Identical float32 recipe, sequence order, warmup count, message count and consumer delay within each case; full exact-value validation plus CRC and ACK in every profile. No drops or outlier exclusions.
- pipe/shared are the existing stop-and-wait protocols with one payload in flight. shared copies a staging array into its slot. pool_1/pool_n fill loaned shared slots in place. window_pipe fills local loaned slots in place and uses the same publication/release protocol and capacity as pool_n. All Pipe payloads use recv_bytes plus a copy to a preallocated consumer target.
- Pool and windowed Pipe carry additional slot/generation metadata. Pool_n versus legacy baselines includes changes in copy count, window and protocol. The equal-window Pipe control separates window size from transport more closely, but receiver allocation/copy behavior still differs. No end-to-end zero-copy claim: base/reference generation, validation and CRC remain included.
- Closed-loop, finite SPSC saturation traces, not a shared arrival schedule, inference service or production capacity estimate. Every block rotates profile order; five blocks balance all five positions. Partial subsets are never called a full grid.
- Message completion latency starts before loan acquisition or legacy generation and ends when its valid ACK is processed by the producer. Pool latency includes capacity waiting and ACK collection scheduling. Capacity-reclaim counts mean no locally free slot, even if an ACK is already queued; reclaim time includes ACK processing, not only consumer waiting. It is not transport RTT or consumer service time. Drain of the final partial window is included in throughput.
- Workers are fresh per trial; eight transfers warm protocol state before measurement, fully drained before start. Artificial consumer delay is applied only to measured messages after validation and before ACK in all profiles; requested sleep is not exact service time.
- RSS samples include two worker runtimes, arrays, touched pool pages, records and result serialization; baseline is after warmup. Shared pages may be counted twice. Sequential 5 ms requested samples can miss peaks; actual gaps are retained. Controller/resource tracker are excluded. Pool payload allocation is bounded; per-message evidence records still grow with the finite message count. RSS is not unique physical memory or total deployment size.
- Single host, fixed case order, uncontrolled CPU/cache/thermals and short trials. Ratios are medians of all within-block ratios with observed min/max, not confidence intervals or universal effects. Controller-managed worker-crash cleanup is tested; controller kill and power loss are outside the guarantee.

[JSON evidence](report.json) · [Offline HTML](report.html)
