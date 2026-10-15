# Bounded IPC pool comparison

Five-profile verified exchanges; all blocks retained. ACK-observed latency includes loan waiting and ACK collection; admitted-to-ready and ACK-observation lag are reported separately. RSS is sampled two-worker RSS, not unique physical RAM.

| Case | Profile | Count | MiB/s median | ACK-observed p50 ms | ACK-observed p95 ms | Admitted-to-ready p95 ms | ACK-observation lag p95 ms | Baseline RSS MiB median | Peak RSS MiB max | Slots max | ACK-reclaim events median | Reclaim ms total median | Max RSS gap ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal-64 | pipe | 8192 | 2.53 | 0.0201 | 0.0384 | 0.0283 | 0.0157 | 78.28 | 86.16 | 1 | 0 | 0.000 | 6.515 |
| normal-64 | shared | 8192 | 2.30 | 0.0194 | 0.0361 | 0.0215 | 0.0140 | 78.25 | 86.06 | 1 | 0 | 0.000 | 6.589 |
| normal-64 | pool_1 | 8192 | 2.36 | 0.0379 | 0.0750 | 0.0234 | 0.0171 | 78.17 | 90.44 | 1 | 8191 | 174.886 | 7.505 |
| normal-64 | pool_n | 8192 | 4.41 | 0.0348 | 0.0926 | 0.0462 | 0.0415 | 78.19 | 90.98 | 4 | 8188 | 84.059 | 7.480 |
| normal-64 | window_pipe | 8192 | 4.10 | 0.0469 | 0.1034 | 0.0539 | 0.0493 | 78.11 | 90.73 | 4 | 8188 | 81.551 | 7.760 |
| normal-1024 | pipe | 8192 | 35.78 | 0.0205 | 0.0419 | 0.0297 | 0.0177 | 78.19 | 86.20 | 1 | 0 | 0.000 | 7.006 |
| normal-1024 | shared | 8192 | 41.48 | 0.0194 | 0.0357 | 0.0228 | 0.0170 | 78.20 | 86.48 | 1 | 0 | 0.000 | 7.345 |
| normal-1024 | pool_1 | 8192 | 40.36 | 0.0386 | 0.0715 | 0.0233 | 0.0170 | 78.23 | 91.02 | 1 | 8191 | 162.697 | 7.699 |
| normal-1024 | pool_n | 8192 | 68.02 | 0.0375 | 0.0923 | 0.0456 | 0.0385 | 78.34 | 90.95 | 4 | 8188 | 88.086 | 7.481 |
| normal-1024 | window_pipe | 8192 | 72.38 | 0.0487 | 0.0954 | 0.0536 | 0.0482 | 78.14 | 90.95 | 4 | 8188 | 69.892 | 6.491 |
| normal-16384 | pipe | 8192 | 354.43 | 0.0392 | 0.0576 | 0.0470 | 0.0159 | 78.12 | 86.23 | 1 | 0 | 0.000 | 6.541 |
| normal-16384 | shared | 8192 | 603.15 | 0.0229 | 0.0393 | 0.0239 | 0.0147 | 78.22 | 86.08 | 1 | 0 | 0.000 | 6.522 |
| normal-16384 | pool_1 | 8192 | 575.99 | 0.0437 | 0.0715 | 0.0251 | 0.0156 | 78.17 | 91.39 | 1 | 8191 | 182.299 | 7.279 |
| normal-16384 | pool_n | 8192 | 963.85 | 0.0599 | 0.1139 | 0.0554 | 0.0501 | 78.39 | 91.06 | 4 | 8188 | 92.070 | 15.537 |
| normal-16384 | window_pipe | 8192 | 419.16 | 0.1246 | 0.2311 | 0.0718 | 0.1596 | 78.23 | 91.23 | 4 | 8188 | 50.956 | 7.949 |
| normal-262144 | pipe | 1024 | 692.74 | 0.2657 | 0.4086 | 0.3958 | 0.0228 | 79.30 | 80.66 | 1 | 0 | 0.000 | 6.743 |
| normal-262144 | shared | 1024 | 1900.71 | 0.1017 | 0.1332 | 0.1093 | 0.0232 | 79.06 | 80.45 | 1 | 0 | 0.000 | 7.449 |
| normal-262144 | pool_1 | 1024 | 2348.15 | 0.1614 | 0.2894 | 0.1019 | 0.0308 | 78.95 | 80.67 | 1 | 1023 | 93.478 | 6.415 |
| normal-262144 | pool_n | 1024 | 2496.62 | 0.2866 | 0.4739 | 0.2800 | 0.1657 | 80.53 | 82.27 | 4 | 1020 | 84.727 | 6.414 |
| normal-262144 | window_pipe | 1024 | 790.80 | 0.9530 | 1.5151 | 0.4425 | 1.0946 | 80.12 | 81.84 | 4 | 1020 | 7.543 | 6.496 |
| normal-1048576 | pipe | 256 | 858.00 | 1.1043 | 1.5086 | 1.4834 | 0.0314 | 85.34 | 86.86 | 1 | 0 | 0.000 | 6.357 |
| normal-1048576 | shared | 256 | 3187.00 | 0.2362 | 0.3895 | 0.3593 | 0.0282 | 83.97 | 84.55 | 1 | 0 | 0.000 | 6.350 |
| normal-1048576 | pool_1 | 256 | 3231.81 | 0.4949 | 0.6376 | 0.3084 | 0.0354 | 82.94 | 83.64 | 1 | 255 | 67.542 | 6.442 |
| normal-1048576 | pool_n | 256 | 6773.52 | 0.5710 | 1.1214 | 0.8568 | 0.1771 | 88.91 | 89.67 | 4 | 252 | 23.825 | 6.959 |
| normal-1048576 | window_pipe | 256 | 928.50 | 4.1861 | 5.3854 | 1.5458 | 3.9068 | 87.98 | 90.30 | 4 | 252 | 2.555 | 6.335 |
| normal-4194304 | pipe | 64 | 857.37 | 4.0445 | 6.0999 | 6.0666 | 0.0611 | 107.70 | 107.84 | 1 | 0 | 0.000 | 7.126 |
| normal-4194304 | shared | 64 | 3698.28 | 1.0929 | 1.2625 | 1.2034 | 0.0515 | 103.69 | 104.86 | 1 | 0 | 0.000 | 6.457 |
| normal-4194304 | pool_1 | 64 | 5794.36 | 1.1548 | 1.3799 | 0.7447 | 0.0359 | 99.47 | 100.95 | 1 | 63 | 32.870 | 6.436 |
| normal-4194304 | pool_n | 64 | 5303.66 | 2.6807 | 9.1584 | 8.3365 | 0.1198 | 123.52 | 125.23 | 4 | 60 | 27.030 | 11.705 |
| normal-4194304 | window_pipe | 64 | 918.16 | 17.2173 | 21.1776 | 6.0548 | 15.4611 | 119.67 | 120.11 | 4 | 60 | 1.162 | 6.513 |
| slow-16384 | pipe | 129 | 11.30 | 1.3396 | 1.6276 | 1.5961 | 0.0439 | 78.23 | 78.44 | 1 | 0 | 0.000 | 8.462 |
| slow-16384 | shared | 129 | 11.39 | 1.3138 | 1.4642 | 1.4281 | 0.0467 | 78.33 | 78.73 | 1 | 0 | 0.000 | 6.469 |
| slow-16384 | pool_1 | 129 | 11.15 | 2.6999 | 3.2581 | 1.6548 | 0.0517 | 78.16 | 78.81 | 1 | 128 | 177.454 | 7.028 |
| slow-16384 | pool_n | 129 | 11.58 | 6.3806 | 7.7895 | 6.3237 | 0.0630 | 78.31 | 78.59 | 4 | 125 | 167.571 | 6.466 |
| slow-16384 | window_pipe | 129 | 11.55 | 5.3074 | 5.5948 | 2.6908 | 2.9279 | 78.11 | 78.64 | 4 | 125 | 2.374 | 6.461 |
| slow-1048576 | pipe | 129 | 384.56 | 2.4125 | 3.2045 | 3.1751 | 0.0477 | 84.84 | 86.42 | 1 | 0 | 0.000 | 6.457 |
| slow-1048576 | shared | 129 | 574.59 | 1.5709 | 2.2649 | 2.2289 | 0.0505 | 83.69 | 84.11 | 1 | 0 | 0.000 | 6.742 |
| slow-1048576 | pool_1 | 129 | 666.53 | 2.8700 | 3.3731 | 1.6585 | 0.0478 | 82.77 | 83.48 | 1 | 128 | 185.323 | 6.428 |
| slow-1048576 | pool_n | 129 | 636.19 | 7.0181 | 8.1952 | 6.4724 | 0.1432 | 88.95 | 89.59 | 4 | 125 | 186.247 | 6.454 |
| slow-1048576 | window_pipe | 129 | 408.58 | 9.1234 | 11.8373 | 4.5030 | 7.4831 | 88.11 | 89.52 | 4 | 125 | 1.804 | 7.662 |

All within-block throughput ratios: median [observed min, max], not a confidence interval.

| Case | Numerator / denominator | Ratio |
|---|---|---|
| normal-64 | pool_1 / shared | 0.886 [0.674, 1.354] |
| normal-64 | pool_n / shared | 1.810 [1.335, 3.212] |
| normal-64 | pool_n / pipe | 1.829 [1.405, 2.959] |
| normal-64 | pool_n / window_pipe | 1.314 [0.766, 1.621] |
| normal-1024 | pool_1 / shared | 0.949 [0.839, 1.176] |
| normal-1024 | pool_n / shared | 1.645 [1.319, 2.491] |
| normal-1024 | pool_n / pipe | 2.053 [1.442, 2.824] |
| normal-1024 | pool_n / window_pipe | 0.996 [0.684, 1.608] |
| normal-16384 | pool_1 / shared | 0.916 [0.675, 1.143] |
| normal-16384 | pool_n / shared | 1.575 [1.354, 2.208] |
| normal-16384 | pool_n / pipe | 2.604 [2.439, 3.229] |
| normal-16384 | pool_n / window_pipe | 2.315 [1.948, 2.623] |
| normal-262144 | pool_1 / shared | 1.165 [0.874, 1.541] |
| normal-262144 | pool_n / shared | 1.207 [1.015, 1.933] |
| normal-262144 | pool_n / pipe | 3.604 [2.548, 5.416] |
| normal-262144 | pool_n / window_pipe | 3.157 [2.557, 4.759] |
| normal-1048576 | pool_1 / shared | 0.931 [0.575, 1.636] |
| normal-1048576 | pool_n / shared | 1.921 [1.836, 3.350] |
| normal-1048576 | pool_n / pipe | 7.908 [7.157, 8.960] |
| normal-1048576 | pool_n / window_pipe | 7.303 [6.399, 8.507] |
| normal-4194304 | pool_1 / shared | 1.539 [0.520, 2.267] |
| normal-4194304 | pool_n / shared | 1.524 [0.845, 2.670] |
| normal-4194304 | pool_n / pipe | 6.052 [3.419, 10.045] |
| normal-4194304 | pool_n / window_pipe | 5.962 [3.245, 8.796] |
| slow-16384 | pool_1 / shared | 0.961 [0.926, 1.246] |
| slow-16384 | pool_n / shared | 1.064 [0.953, 1.169] |
| slow-16384 | pool_n / pipe | 1.065 [0.976, 1.097] |
| slow-16384 | pool_n / window_pipe | 1.050 [0.976, 1.132] |
| slow-1048576 | pool_1 / shared | 1.168 [1.011, 1.239] |
| slow-1048576 | pool_n / shared | 1.088 [0.951, 1.269] |
| slow-1048576 | pool_n / pipe | 1.654 [1.520, 1.923] |
| slow-1048576 | pool_n / window_pipe | 1.591 [1.461, 1.689] |

- Identical float32 recipe, sequence order, warmup count, message count and consumer delay within each case; full exact-value validation plus CRC and ACK in every profile. No drops or outlier exclusions.
- pipe/shared are the existing stop-and-wait protocols with one payload in flight. shared copies a staging array into its slot. pool_1/pool_n fill loaned shared slots in place. window_pipe fills local loaned slots in place and uses the same publication/release protocol and capacity as pool_n. All Pipe payloads use recv_bytes plus a copy to a preallocated consumer target.
- Pool and windowed Pipe carry additional slot/generation metadata. Pool_n versus legacy baselines includes changes in copy count, window and protocol. The equal-window Pipe control separates window size from transport more closely, but receiver allocation/copy behavior still differs. No end-to-end zero-copy claim: base/reference generation, validation and CRC remain included.
- Closed-loop, finite SPSC saturation traces, not a shared arrival schedule, inference service or production capacity estimate. Every block rotates profile order; five blocks balance all five positions. Partial subsets are never called a full grid.
- ACK-observed latency starts before loan acquisition or legacy generation and ends when its valid ACK is processed by the producer. Pool latency includes capacity waiting and ACK collection scheduling. Capacity-reclaim counts mean no locally free slot, even if an ACK is already queued; reclaim time includes ACK processing, not only consumer waiting. Admitted-to-ready timing starts at slot acquisition (legacy generation start) and ends in the consumer after full validation and any declared delay, before sending ACK. Attempt-to-ready additionally includes admission waiting. ACK-observation lag includes ACK transmission and producer scheduling/reclamation. These are distinct clocks, not application latency under a common arrival schedule or pure transport RTT. Drain of the final partial window is included in throughput.
- Workers are fresh per trial; eight transfers warm protocol state before measurement, fully drained before start. Artificial consumer delay is applied only to measured messages after validation and before ACK in all profiles; requested sleep is not exact service time.
- RSS samples include two worker runtimes, arrays, touched pool pages, records and result serialization; baseline is after warmup. Shared pages may be counted twice. Sequential 5 ms requested samples can miss peaks; actual gaps are retained. Controller/resource tracker are excluded. Pool payload allocation is bounded; per-message evidence records still grow with the finite message count. RSS is not unique physical memory or total deployment size.
- Single host, fixed case order, uncontrolled CPU/cache/thermals and short trials. Ratios are medians of all within-block ratios with observed min/max, not confidence intervals or universal effects. Controller-managed worker-crash cleanup is tested; controller kill and power loss are outside the guarantee.

[JSON evidence](report.json) · [Offline HTML](report.html)
