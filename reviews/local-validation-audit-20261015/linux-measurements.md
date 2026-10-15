Virtualized Linux ARM64 inside Colima; 4 CPU / 4 GiB container, 6 GiB VM. Worker RSS excludes VM/daemon overhead; it is not native-host memory usage.

# Bounded IPC pool comparison

Five-profile verified exchanges; all blocks retained. ACK-observed latency includes loan waiting and ACK collection; admitted-to-ready and ACK-observation lag are reported separately. RSS is sampled two-worker RSS, not unique physical RAM.

| Case | Profile | Count | MiB/s median | ACK-observed p50 ms | ACK-observed p95 ms | Admitted-to-ready p95 ms | ACK-observation lag p95 ms | Baseline RSS MiB median | Peak RSS MiB max | Slots max | ACK-reclaim events median | Reclaim ms total median | Max RSS gap ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal-64 | pipe | 8192 | 1.57 | 0.0390 | 0.0451 | 0.0275 | 0.0177 | 73.49 | 80.74 | 1 | 0 | 0.000 | 7.884 |
| normal-64 | shared | 8192 | 1.59 | 0.0362 | 0.0445 | 0.0268 | 0.0184 | 73.47 | 80.32 | 1 | 0 | 0.000 | 7.396 |
| normal-64 | pool_1 | 8192 | 1.55 | 0.0669 | 0.0791 | 0.0269 | 0.0175 | 73.50 | 84.81 | 1 | 8191 | 257.468 | 7.816 |
| normal-64 | pool_n | 8192 | 6.40 | 0.0291 | 0.0369 | 0.0264 | 0.0194 | 73.50 | 84.45 | 4 | 8188 | 55.372 | 7.959 |
| normal-64 | window_pipe | 8192 | 5.15 | 0.0398 | 0.0549 | 0.0363 | 0.0152 | 73.49 | 84.82 | 4 | 8188 | 65.047 | 6.383 |
| normal-1024 | pipe | 8192 | 23.52 | 0.0401 | 0.0495 | 0.0300 | 0.0200 | 73.46 | 79.82 | 1 | 0 | 0.000 | 7.141 |
| normal-1024 | shared | 8192 | 25.22 | 0.0365 | 0.0449 | 0.0273 | 0.0193 | 73.48 | 79.82 | 1 | 0 | 0.000 | 6.375 |
| normal-1024 | pool_1 | 8192 | 24.63 | 0.0677 | 0.0836 | 0.0284 | 0.0192 | 73.49 | 84.43 | 1 | 8191 | 260.357 | 8.003 |
| normal-1024 | pool_n | 8192 | 103.20 | 0.0303 | 0.0692 | 0.0333 | 0.0207 | 73.50 | 84.66 | 4 | 8188 | 53.171 | 8.296 |
| normal-1024 | window_pipe | 8192 | 70.69 | 0.0429 | 0.1028 | 0.0468 | 0.0244 | 73.50 | 84.38 | 4 | 8188 | 74.886 | 7.499 |
| normal-16384 | pipe | 8192 | 324.17 | 0.0463 | 0.0560 | 0.0378 | 0.0199 | 73.48 | 80.07 | 1 | 0 | 0.000 | 7.789 |
| normal-16384 | shared | 8192 | 357.46 | 0.0430 | 0.0526 | 0.0336 | 0.0198 | 73.49 | 80.08 | 1 | 0 | 0.000 | 7.836 |
| normal-16384 | pool_1 | 8192 | 345.69 | 0.0770 | 0.0909 | 0.0331 | 0.0184 | 73.51 | 84.71 | 1 | 8191 | 286.034 | 7.931 |
| normal-16384 | pool_n | 8192 | 1203.29 | 0.0437 | 0.0590 | 0.0420 | 0.0188 | 73.61 | 84.84 | 4 | 8188 | 59.471 | 7.850 |
| normal-16384 | window_pipe | 8192 | 953.39 | 0.0607 | 0.0809 | 0.0568 | 0.0232 | 73.52 | 84.29 | 4 | 8188 | 73.681 | 7.924 |
| normal-262144 | pipe | 1024 | 1081.91 | 0.2163 | 0.2389 | 0.2151 | 0.0244 | 74.82 | 75.95 | 1 | 0 | 0.000 | 7.766 |
| normal-262144 | shared | 1024 | 1815.02 | 0.1219 | 0.1398 | 0.1185 | 0.0222 | 75.00 | 75.70 | 1 | 0 | 0.000 | 6.661 |
| normal-262144 | pool_1 | 1024 | 1823.26 | 0.1940 | 0.2223 | 0.1150 | 0.0218 | 74.76 | 76.08 | 1 | 1023 | 93.586 | 6.390 |
| normal-262144 | pool_n | 1024 | 3415.75 | 0.2207 | 0.5676 | 0.2157 | 0.0454 | 76.25 | 77.54 | 4 | 1020 | 33.515 | 12.180 |
| normal-262144 | window_pipe | 1024 | 1583.62 | 0.5801 | 0.6597 | 0.2706 | 0.3795 | 75.58 | 77.06 | 4 | 1020 | 7.105 | 7.735 |
| normal-1048576 | pipe | 256 | 1384.72 | 0.6685 | 0.7468 | 0.7255 | 0.0259 | 78.73 | 81.18 | 1 | 0 | 0.000 | 6.402 |
| normal-1048576 | shared | 256 | 2274.84 | 0.3829 | 0.4094 | 0.3834 | 0.0243 | 79.73 | 79.82 | 1 | 0 | 0.000 | 8.003 |
| normal-1048576 | pool_1 | 256 | 2329.16 | 0.5731 | 1.7031 | 0.3935 | 0.0281 | 78.74 | 78.93 | 1 | 255 | 67.614 | 8.051 |
| normal-1048576 | pool_n | 256 | 3855.38 | 0.7873 | 3.1747 | 0.9207 | 0.8599 | 84.73 | 84.93 | 4 | 252 | 24.190 | 7.909 |
| normal-1048576 | window_pipe | 256 | 1864.93 | 1.9669 | 2.7124 | 0.9231 | 1.6202 | 81.73 | 83.73 | 4 | 252 | 1.964 | 7.040 |
| normal-4194304 | pipe | 64 | 1928.13 | 1.8872 | 2.5955 | 2.5683 | 0.0385 | 98.14 | 104.80 | 1 | 0 | 0.000 | 6.412 |
| normal-4194304 | shared | 64 | 2664.94 | 1.4307 | 1.4755 | 1.4432 | 0.0361 | 98.48 | 98.62 | 1 | 0 | 0.000 | 7.376 |
| normal-4194304 | pool_1 | 64 | 2746.76 | 2.1335 | 2.4058 | 1.4800 | 0.0535 | 94.49 | 94.52 | 1 | 63 | 51.893 | 7.163 |
| normal-4194304 | pool_n | 64 | 4497.59 | 3.0133 | 7.4052 | 4.5179 | 2.8494 | 118.46 | 118.50 | 4 | 60 | 11.897 | 6.412 |
| normal-4194304 | window_pipe | 64 | 2062.01 | 7.6827 | 8.6378 | 3.8307 | 5.3690 | 110.38 | 116.96 | 4 | 60 | 0.728 | 6.453 |
| slow-16384 | pipe | 129 | 11.33 | 1.4362 | 1.4603 | 1.4051 | 0.0613 | 73.48 | 73.52 | 1 | 0 | 0.000 | 8.000 |
| slow-16384 | shared | 129 | 11.54 | 1.4300 | 1.4544 | 1.3977 | 0.0596 | 73.52 | 73.57 | 1 | 0 | 0.000 | 7.879 |
| slow-16384 | pool_1 | 129 | 11.56 | 2.8152 | 2.8835 | 1.3967 | 0.0579 | 73.48 | 73.61 | 1 | 128 | 171.130 | 6.455 |
| slow-16384 | pool_n | 129 | 11.88 | 6.8943 | 6.9970 | 5.5576 | 0.0589 | 73.60 | 73.71 | 4 | 125 | 162.666 | 6.465 |
| slow-16384 | window_pipe | 129 | 11.78 | 6.9092 | 7.0240 | 5.5865 | 0.0594 | 73.51 | 73.59 | 4 | 125 | 163.587 | 7.936 |
| slow-1048576 | pipe | 129 | 481.57 | 2.0080 | 2.3496 | 2.3170 | 0.0617 | 78.72 | 80.48 | 1 | 0 | 0.000 | 8.352 |
| slow-1048576 | shared | 129 | 539.16 | 1.8392 | 2.0060 | 1.9563 | 0.0627 | 79.73 | 79.76 | 1 | 0 | 0.000 | 7.838 |
| slow-1048576 | pool_1 | 129 | 543.28 | 3.4450 | 3.7936 | 1.8970 | 0.0629 | 78.74 | 78.82 | 1 | 128 | 209.055 | 7.455 |
| slow-1048576 | pool_n | 129 | 620.78 | 7.8013 | 8.2176 | 6.6556 | 0.0639 | 84.72 | 84.82 | 4 | 125 | 176.088 | 7.028 |
| slow-1048576 | window_pipe | 129 | 530.11 | 7.3092 | 8.2321 | 3.7613 | 4.3775 | 81.74 | 83.42 | 4 | 125 | 1.328 | 7.818 |

All within-block throughput ratios: median [observed min, max], not a confidence interval.

| Case | Numerator / denominator | Ratio |
|---|---|---|
| normal-64 | pool_1 / shared | 1.017 [0.963, 1.066] |
| normal-64 | pool_n / shared | 3.983 [3.315, 4.671] |
| normal-64 | pool_n / pipe | 4.143 [3.492, 4.285] |
| normal-64 | pool_n / window_pipe | 1.262 [1.008, 1.361] |
| normal-1024 | pool_1 / shared | 0.981 [0.928, 1.008] |
| normal-1024 | pool_n / shared | 4.066 [3.650, 4.273] |
| normal-1024 | pool_n / pipe | 4.205 [3.872, 4.695] |
| normal-1024 | pool_n / window_pipe | 1.460 [1.070, 1.579] |
| normal-16384 | pool_1 / shared | 1.015 [0.956, 1.049] |
| normal-16384 | pool_n / shared | 3.283 [3.244, 3.532] |
| normal-16384 | pool_n / pipe | 3.678 [3.524, 3.825] |
| normal-16384 | pool_n / window_pipe | 1.265 [1.231, 1.302] |
| normal-262144 | pool_1 / shared | 1.004 [0.981, 1.065] |
| normal-262144 | pool_n / shared | 1.840 [1.651, 2.011] |
| normal-262144 | pool_n / pipe | 3.177 [2.588, 3.597] |
| normal-262144 | pool_n / window_pipe | 2.151 [1.792, 2.338] |
| normal-1048576 | pool_1 / shared | 1.017 [0.900, 1.070] |
| normal-1048576 | pool_n / shared | 1.695 [1.667, 1.787] |
| normal-1048576 | pool_n / pipe | 2.810 [2.651, 2.940] |
| normal-1048576 | pool_n / window_pipe | 2.144 [2.054, 2.249] |
| normal-4194304 | pool_1 / shared | 1.024 [0.942, 1.067] |
| normal-4194304 | pool_n / shared | 1.700 [1.622, 1.749] |
| normal-4194304 | pool_n / pipe | 2.272 [2.240, 2.892] |
| normal-4194304 | pool_n / window_pipe | 2.191 [2.029, 2.274] |
| slow-16384 | pool_1 / shared | 0.990 [0.970, 1.022] |
| slow-16384 | pool_n / shared | 1.031 [1.008, 1.042] |
| slow-16384 | pool_n / pipe | 1.048 [1.036, 1.058] |
| slow-16384 | pool_n / window_pipe | 1.005 [0.996, 1.033] |
| slow-1048576 | pool_1 / shared | 1.008 [0.997, 1.020] |
| slow-1048576 | pool_n / shared | 1.150 [1.103, 1.192] |
| slow-1048576 | pool_n / pipe | 1.325 [1.244, 1.350] |
| slow-1048576 | pool_n / window_pipe | 1.161 [1.138, 1.202] |

- Identical float32 recipe, sequence order, warmup count, message count and consumer delay within each case; full exact-value validation plus CRC and ACK in every profile. No drops or outlier exclusions.
- pipe/shared are the existing stop-and-wait protocols with one payload in flight. shared copies a staging array into its slot. pool_1/pool_n fill loaned shared slots in place. window_pipe fills local loaned slots in place and uses the same publication/release protocol and capacity as pool_n. All Pipe payloads use recv_bytes plus a copy to a preallocated consumer target.
- Pool and windowed Pipe carry additional slot/generation metadata. Pool_n versus legacy baselines includes changes in copy count, window and protocol. The equal-window Pipe control separates window size from transport more closely, but receiver allocation/copy behavior still differs. No end-to-end zero-copy claim: base/reference generation, validation and CRC remain included.
- Closed-loop, finite SPSC saturation traces, not a shared arrival schedule, inference service or production capacity estimate. Every block rotates profile order; five blocks balance all five positions. Partial subsets are never called a full grid.
- ACK-observed latency starts before loan acquisition or legacy generation and ends when its valid ACK is processed by the producer. Pool latency includes capacity waiting and ACK collection scheduling. Capacity-reclaim counts mean no locally free slot, even if an ACK is already queued; reclaim time includes ACK processing, not only consumer waiting. Admitted-to-ready timing starts at slot acquisition (legacy generation start) and ends in the consumer after full validation and any declared delay, before sending ACK. Attempt-to-ready additionally includes admission waiting. ACK-observation lag includes ACK transmission and producer scheduling/reclamation. These are distinct clocks, not application latency under a common arrival schedule or pure transport RTT. Drain of the final partial window is included in throughput.
- Workers are fresh per trial; eight transfers warm protocol state before measurement, fully drained before start. Artificial consumer delay is applied only to measured messages after validation and before ACK in all profiles; requested sleep is not exact service time.
- RSS samples include two worker runtimes, arrays, touched pool pages, records and result serialization; baseline is after warmup. Shared pages may be counted twice. Sequential 5 ms requested samples can miss peaks; actual gaps are retained. Controller/resource tracker are excluded. Pool payload allocation is bounded; per-message evidence records still grow with the finite message count. RSS is not unique physical memory or total deployment size.
- Single host, fixed case order, uncontrolled CPU/cache/thermals and short trials. Ratios are medians of all within-block ratios with observed min/max, not confidence intervals or universal effects. Controller-managed worker-crash cleanup is tested; controller kill and power loss are outside the guarantee.


Full JSON, offline HTML and raw exchanges are retained locally with the run ID in receipt.json.
