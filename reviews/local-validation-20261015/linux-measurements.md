Virtualized Linux ARM64 inside Colima; 4 CPU / 4 GiB container, 6 GiB VM. Worker RSS excludes VM/daemon overhead; it is not native-host memory usage.

# Bounded IPC pool comparison

Five-profile verified exchanges; all blocks retained. ACK-observed latency includes loan waiting and ACK collection; admitted-to-ready and ACK-observation lag are reported separately. RSS is sampled two-worker RSS, not unique physical RAM.

| Case | Profile | Count | MiB/s median | ACK-observed p50 ms | ACK-observed p95 ms | Admitted-to-ready p95 ms | ACK-observation lag p95 ms | Baseline RSS MiB median | Peak RSS MiB max | Slots max | ACK-reclaim events median | Reclaim ms total median | Max RSS gap ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal-64 | pipe | 8192 | 1.55 | 0.0387 | 0.0480 | 0.0288 | 0.0202 | 73.46 | 80.52 | 1 | 0 | 0.000 | 6.730 |
| normal-64 | shared | 8192 | 1.58 | 0.0360 | 0.0452 | 0.0272 | 0.0191 | 73.50 | 79.81 | 1 | 0 | 0.000 | 7.977 |
| normal-64 | pool_1 | 8192 | 1.57 | 0.0659 | 0.0814 | 0.0277 | 0.0187 | 73.52 | 85.62 | 1 | 8191 | 257.683 | 8.007 |
| normal-64 | pool_n | 8192 | 5.88 | 0.0295 | 0.0435 | 0.0301 | 0.0184 | 73.50 | 84.37 | 4 | 8188 | 60.336 | 7.830 |
| normal-64 | window_pipe | 8192 | 5.47 | 0.0397 | 0.0681 | 0.0394 | 0.0197 | 73.46 | 84.79 | 4 | 8188 | 59.362 | 6.960 |
| normal-1024 | pipe | 8192 | 24.67 | 0.0375 | 0.0501 | 0.0312 | 0.0204 | 73.49 | 80.37 | 1 | 0 | 0.000 | 7.859 |
| normal-1024 | shared | 8192 | 24.07 | 0.0355 | 0.0547 | 0.0328 | 0.0228 | 73.45 | 79.82 | 1 | 0 | 0.000 | 21.504 |
| normal-1024 | pool_1 | 8192 | 25.03 | 0.0656 | 0.0822 | 0.0286 | 0.0195 | 73.50 | 83.70 | 1 | 8191 | 255.503 | 7.184 |
| normal-1024 | pool_n | 8192 | 98.16 | 0.0312 | 0.0461 | 0.0293 | 0.0180 | 73.50 | 84.84 | 4 | 8188 | 56.221 | 9.148 |
| normal-1024 | window_pipe | 8192 | 79.69 | 0.0414 | 0.0571 | 0.0388 | 0.0201 | 73.49 | 84.96 | 4 | 8188 | 62.279 | 7.839 |
| normal-16384 | pipe | 8192 | 316.70 | 0.0482 | 0.0540 | 0.0360 | 0.0185 | 73.48 | 80.16 | 1 | 0 | 0.000 | 7.914 |
| normal-16384 | shared | 8192 | 357.17 | 0.0432 | 0.0497 | 0.0320 | 0.0179 | 73.51 | 80.10 | 1 | 0 | 0.000 | 7.534 |
| normal-16384 | pool_1 | 8192 | 337.19 | 0.0778 | 0.0935 | 0.0347 | 0.0197 | 73.52 | 84.67 | 1 | 8191 | 291.379 | 7.827 |
| normal-16384 | pool_n | 8192 | 1216.48 | 0.0421 | 0.0563 | 0.0403 | 0.0215 | 73.61 | 85.46 | 4 | 8188 | 58.801 | 7.889 |
| normal-16384 | window_pipe | 8192 | 944.33 | 0.0596 | 0.0706 | 0.0536 | 0.0174 | 73.54 | 84.28 | 4 | 8188 | 73.692 | 7.537 |
| normal-262144 | pipe | 1024 | 1099.41 | 0.2127 | 0.2290 | 0.2072 | 0.0228 | 74.81 | 75.87 | 1 | 0 | 0.000 | 7.997 |
| normal-262144 | shared | 1024 | 1811.83 | 0.1206 | 0.1347 | 0.1153 | 0.0220 | 74.99 | 75.70 | 1 | 0 | 0.000 | 6.420 |
| normal-262144 | pool_1 | 1024 | 1835.09 | 0.1925 | 0.2144 | 0.1136 | 0.0208 | 74.77 | 76.09 | 1 | 1023 | 92.862 | 7.871 |
| normal-262144 | pool_n | 1024 | 3340.00 | 0.2207 | 0.5758 | 0.2153 | 0.0444 | 76.25 | 77.56 | 4 | 1020 | 35.190 | 6.354 |
| normal-262144 | window_pipe | 1024 | 1553.62 | 0.5875 | 0.6324 | 0.2614 | 0.3605 | 75.58 | 76.85 | 4 | 1020 | 6.948 | 7.932 |
| normal-1048576 | pipe | 256 | 1330.57 | 0.6855 | 0.9224 | 0.8932 | 0.0296 | 78.73 | 81.64 | 1 | 0 | 0.000 | 9.992 |
| normal-1048576 | shared | 256 | 2321.06 | 0.3858 | 0.4134 | 0.3874 | 0.0254 | 79.74 | 79.83 | 1 | 0 | 0.000 | 7.040 |
| normal-1048576 | pool_1 | 256 | 2316.54 | 0.5755 | 1.3855 | 0.3727 | 0.0254 | 78.73 | 78.93 | 1 | 255 | 64.922 | 7.846 |
| normal-1048576 | pool_n | 256 | 3850.77 | 0.7880 | 3.0814 | 2.1879 | 0.7508 | 84.74 | 85.05 | 4 | 252 | 23.813 | 7.409 |
| normal-1048576 | window_pipe | 256 | 1769.15 | 1.9808 | 3.2908 | 1.1680 | 1.5491 | 81.73 | 84.25 | 4 | 252 | 2.038 | 6.541 |
| normal-4194304 | pipe | 64 | 1565.03 | 2.4547 | 3.0752 | 3.0394 | 0.0673 | 100.30 | 107.05 | 1 | 0 | 0.000 | 6.678 |
| normal-4194304 | shared | 64 | 2719.36 | 1.4662 | 1.5151 | 1.4819 | 0.0430 | 98.48 | 98.50 | 1 | 0 | 0.000 | 6.419 |
| normal-4194304 | pool_1 | 64 | 2825.85 | 2.1486 | 2.3043 | 1.4184 | 0.0432 | 94.48 | 94.52 | 1 | 63 | 49.639 | 6.603 |
| normal-4194304 | pool_n | 64 | 4547.36 | 3.0185 | 8.0056 | 4.8603 | 3.7707 | 118.48 | 118.51 | 4 | 60 | 12.901 | 6.468 |
| normal-4194304 | window_pipe | 64 | 2148.76 | 7.4081 | 9.1778 | 3.7075 | 5.2672 | 109.96 | 119.33 | 4 | 60 | 1.001 | 6.473 |
| slow-16384 | pipe | 129 | 11.31 | 1.4309 | 1.4629 | 1.4055 | 0.0626 | 73.48 | 73.53 | 1 | 0 | 0.000 | 7.184 |
| slow-16384 | shared | 129 | 11.48 | 1.4129 | 1.4679 | 1.4062 | 0.0608 | 73.48 | 73.54 | 1 | 0 | 0.000 | 7.626 |
| slow-16384 | pool_1 | 129 | 11.14 | 2.8212 | 2.9154 | 1.4117 | 0.0632 | 73.50 | 73.61 | 1 | 128 | 176.756 | 6.711 |
| slow-16384 | pool_n | 129 | 11.82 | 6.8933 | 7.0001 | 5.5626 | 0.0617 | 73.61 | 73.70 | 4 | 125 | 163.443 | 6.621 |
| slow-16384 | window_pipe | 129 | 11.81 | 6.9200 | 7.0750 | 5.6210 | 0.0679 | 73.55 | 73.63 | 4 | 125 | 163.085 | 6.921 |
| slow-1048576 | pipe | 129 | 479.95 | 2.0078 | 2.3767 | 2.3329 | 0.0595 | 78.73 | 80.36 | 1 | 0 | 0.000 | 6.499 |
| slow-1048576 | shared | 129 | 537.66 | 1.8466 | 2.0057 | 1.9524 | 0.0611 | 79.73 | 79.78 | 1 | 0 | 0.000 | 7.927 |
| slow-1048576 | pool_1 | 129 | 544.27 | 3.4225 | 3.8045 | 1.9304 | 0.0664 | 78.72 | 78.81 | 1 | 128 | 209.187 | 7.947 |
| slow-1048576 | pool_n | 129 | 625.02 | 7.7755 | 8.1919 | 6.6756 | 0.0633 | 84.72 | 84.82 | 4 | 125 | 173.026 | 7.996 |
| slow-1048576 | window_pipe | 129 | 517.88 | 7.4549 | 8.7949 | 3.8207 | 4.5151 | 81.73 | 84.27 | 4 | 125 | 1.796 | 7.246 |

All within-block throughput ratios: median [observed min, max], not a confidence interval.

| Case | Numerator / denominator | Ratio |
|---|---|---|
| normal-64 | pool_1 / shared | 0.974 [0.929, 1.008] |
| normal-64 | pool_n / shared | 3.713 [2.780, 3.808] |
| normal-64 | pool_n / pipe | 3.855 [2.768, 3.995] |
| normal-64 | pool_n / window_pipe | 1.115 [0.683, 1.226] |
| normal-1024 | pool_1 / shared | 1.040 [0.893, 3.717] |
| normal-1024 | pool_n / shared | 4.703 [2.488, 14.683] |
| normal-1024 | pool_n / pipe | 3.956 [2.720, 5.070] |
| normal-1024 | pool_n / window_pipe | 1.236 [0.822, 1.421] |
| normal-16384 | pool_1 / shared | 0.955 [0.847, 0.981] |
| normal-16384 | pool_n / shared | 3.406 [3.116, 3.955] |
| normal-16384 | pool_n / pipe | 3.823 [3.486, 4.167] |
| normal-16384 | pool_n / window_pipe | 1.369 [1.159, 1.385] |
| normal-262144 | pool_1 / shared | 1.010 [0.991, 1.021] |
| normal-262144 | pool_n / shared | 1.812 [1.720, 1.904] |
| normal-262144 | pool_n / pipe | 3.021 [2.835, 3.163] |
| normal-262144 | pool_n / window_pipe | 2.154 [2.006, 2.192] |
| normal-1048576 | pool_1 / shared | 1.025 [0.992, 1.088] |
| normal-1048576 | pool_n / shared | 1.732 [0.970, 1.905] |
| normal-1048576 | pool_n / pipe | 2.882 [1.725, 4.421] |
| normal-1048576 | pool_n / window_pipe | 2.172 [1.566, 2.393] |
| normal-4194304 | pool_1 / shared | 1.016 [0.944, 1.074] |
| normal-4194304 | pool_n / shared | 1.662 [1.600, 1.702] |
| normal-4194304 | pool_n / pipe | 2.844 [2.707, 3.170] |
| normal-4194304 | pool_n / window_pipe | 2.151 [1.521, 2.483] |
| slow-16384 | pool_1 / shared | 0.977 [0.961, 1.001] |
| slow-16384 | pool_n / shared | 1.029 [1.017, 1.042] |
| slow-16384 | pool_n / pipe | 1.045 [1.025, 1.053] |
| slow-16384 | pool_n / window_pipe | 1.007 [0.990, 1.017] |
| slow-1048576 | pool_1 / shared | 1.009 [0.982, 1.031] |
| slow-1048576 | pool_n / shared | 1.162 [1.091, 1.173] |
| slow-1048576 | pool_n / pipe | 1.288 [1.259, 1.333] |
| slow-1048576 | pool_n / window_pipe | 1.208 [1.135, 1.240] |

- Identical float32 recipe, sequence order, warmup count, message count and consumer delay within each case; full exact-value validation plus CRC and ACK in every profile. No drops or outlier exclusions.
- pipe/shared are the existing stop-and-wait protocols with one payload in flight. shared copies a staging array into its slot. pool_1/pool_n fill loaned shared slots in place. window_pipe fills local loaned slots in place and uses the same publication/release protocol and capacity as pool_n. All Pipe payloads use recv_bytes plus a copy to a preallocated consumer target.
- Pool and windowed Pipe carry additional slot/generation metadata. Pool_n versus legacy baselines includes changes in copy count, window and protocol. The equal-window Pipe control separates window size from transport more closely, but receiver allocation/copy behavior still differs. No end-to-end zero-copy claim: base/reference generation, validation and CRC remain included.
- Closed-loop, finite SPSC saturation traces, not a shared arrival schedule, inference service or production capacity estimate. Every block rotates profile order; five blocks balance all five positions. Partial subsets are never called a full grid.
- ACK-observed latency starts before loan acquisition or legacy generation and ends when its valid ACK is processed by the producer. Pool latency includes capacity waiting and ACK collection scheduling. Capacity-reclaim counts mean no locally free slot, even if an ACK is already queued; reclaim time includes ACK processing, not only consumer waiting. Admitted-to-ready timing starts at slot acquisition (legacy generation start) and ends in the consumer after full validation and any declared delay, before sending ACK. Attempt-to-ready additionally includes admission waiting. ACK-observation lag includes ACK transmission and producer scheduling/reclamation. These are distinct clocks, not application latency under a common arrival schedule or pure transport RTT. Drain of the final partial window is included in throughput.
- Workers are fresh per trial; eight transfers warm protocol state before measurement, fully drained before start. Artificial consumer delay is applied only to measured messages after validation and before ACK in all profiles; requested sleep is not exact service time.
- RSS samples include two worker runtimes, arrays, touched pool pages, records and result serialization; baseline is after warmup. Shared pages may be counted twice. Sequential 5 ms requested samples can miss peaks; actual gaps are retained. Controller/resource tracker are excluded. Pool payload allocation is bounded; per-message evidence records still grow with the finite message count. RSS is not unique physical memory or total deployment size.
- Single host, fixed case order, uncontrolled CPU/cache/thermals and short trials. Ratios are medians of all within-block ratios with observed min/max, not confidence intervals or universal effects. Controller-managed worker-crash cleanup is tested; controller kill and power loss are outside the guarantee.


Full JSON, offline HTML and raw exchanges are retained locally with the run ID in receipt.json.
