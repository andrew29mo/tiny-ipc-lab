# Tiny IPC Lab

A single-machine verification bench for transferring float32 tensors between two processes using **Pipe raw bytes**, **one reusable shared-memory buffer**, or a **bounded pool of loaned buffers filled in place**.

The question is: **When do shared buffers, in-place generation and a bounded window justify their ownership and cleanup complexity?** This project measures a complete verified round trip, including real data generation, copies, validation and acknowledgements. It does not assume a shared-memory speedup.

## Legacy single-buffer baselines

- One spawned producer, one spawned consumer, and an external controller that samples RSS and owns cleanup.
- One payload in flight in both modes. A sequence/length header and sequence/CRC acknowledgement travel over the same kind of Pipe.
- Pipe uses `send_bytes` with a declared public receive API: the original `recv_bytes_into`, or `recv_bytes` plus copying into the same preallocated target. It does not pickle NumPy arrays.
- Shared mode copies the producer's array into a fixed buffer, publishes its header, then waits for acknowledgement before reuse. The consumer reads a read-only NumPy view; this API guard is not OS-level isolation.
- Every value must exactly match an independently generated expected tensor before acknowledgement. CRC32 provides additional sender/receiver/evidence accounting.
- Tests exercise stale/repeated/skipped sequences, middle-value corruption, short payloads, premature buffer reuse, wrong acknowledgements, real worker crashes, stalled workers and shared-segment cleanup.
- Lossless compressed raw observations, independently regenerated expected CRCs, canonical JSON/HTML/README, and alternating paired trials.

## Bounded pool experiment

The production pool has a fixed slot capacity, direct writes into borrowed slots, sequence/slot/generation identities and ACK-controlled ownership. A full pool waits for a valid release; it does not expand, overwrite or drop. Consumer views and published loan views are read-only API guards.

The new experiment compares five profiles using identical data, validation and counts: existing Pipe, existing copied single buffer, in-place pool capacity 1, pool capacity 4, and a **capacity-4 Pipe control using the same loan protocol**. The equal-window control prevents attributing all pipelining gains to shared memory. Slow-consumer cases deliberately delay each measured ACK by 1 ms; all modes use the same delay.

```sh
python -m tiny_ipc_lab.pool_bench --output results/local/pool
python tools/check_project.py --directory results/local/pool
# Actual-process smoke with a non-divisible tail window:
python -m tiny_ipc_lab.pool_bench --output results/local/pool-smoke --sizes 64 4096 --blocks 2 --capacity 3 --smoke
python tools/check_project.py --directory results/local/pool-smoke --smoke
```

[Reviewed native primary-run JSON/HTML and raw evidence](results/macos-arm64-pool-reviewed/README.md) retain every block. See the [pool ownership, fairness and measurement contract](docs/POOL.md). These are closed-loop verified exchanges, not a shared external arrival schedule or pure transport bandwidth. Producer ACK-observed latency includes loan waiting and deferred ACK collection; consumer-ready timing is reported separately and can rank profiles differently; a larger window can improve throughput while worsening completion latency. Payload slots are bounded, while evidence records still grow with the finite message count.

<!-- POOL_RESULTS_START -->
The primary run retains **200 trials and 654,450 verified tensors** across six normal sizes and two slow-consumer cases. Five rotating blocks include every profile at every order position.

| Case | Pool 4 / copied single buffer | Pool 4 / equal-window Pipe |
|---|---:|---:|
| 64 B, normal | 1.810 [1.335, 3.212] | 1.314 [0.766, 1.621] |
| 1 MiB, normal | 1.921 [1.836, 3.350] | 7.303 [6.399, 8.507] |
| 4 MiB, normal | 1.524 [0.845, 2.670] | 5.962 [3.245, 8.796] |
| 1 MiB, 1 ms delayed ACK | 1.088 [0.951, 1.269] | 1.591 [1.461, 1.689] |

Ratios are medians [observed min, max] of all five within-block throughput ratios, not confidence intervals or ratios of table medians.

At 1 MiB normal load, copied single-buffer versus pool-4 median per-trial p95 producer ACK-observed latency is **0.390 vs 1.121 ms** (includes admission waiting and deferred ACK collection); admitted-to-consumer-ready p95 is **0.359 vs 0.857 ms**, and ACK-observation-lag p95 is **0.028 vs 0.177 ms**. Maximum sampled paired RSS is **84.55 vs 89.67 MiB**. Throughput gains can trade off latency and resident memory. These RSS maxima are not paired physical-memory savings.

These are fresh schema-4 observations with separate consumer-ready clocks. The original schema-3 run and its development run remain historical evidence, verified from immutable source. The full reviewed grid was executed once without concurrent test/validation processes launched by this task; OS/desktop interference remains uncontrolled.
<!-- POOL_RESULTS_END -->

## Run

Python 3.12, macOS/Linux:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
tiny-ipc-lab --output results/local/experiment
python tools/check_project.py --directory results/local/experiment
tiny-ipc-lab --pipe-receive bytes --output results/local/bytes-experiment
python tools/check_project.py --directory results/local/bytes-experiment
```

The default grid is 64 B, 1 KiB, 16 KiB, 256 KiB, 1 MiB and 4 MiB, each with four fresh-process pairs in alternating Pipe/shared order. A fixed size-dependent message budget is used: `max(64, min(8192, 256 MiB // payload_bytes))`. Each mode receives the same sequence of tensors and message count at a given size. Eight identical warmups precede each measured trial. There is no model or external dataset.

A small actual-process smoke run:

```sh
tiny-ipc-lab --output results/local/smoke --sizes 64 4096 --count 17 --pairs 2
python tools/check_project.py --directory results/local/smoke --smoke
```

Output directories must be new. Completed raw trials survive a later failure; an incomplete index and supervised-failure cleanup metadata are retained, without inventing the failed trial's missing observations. Custom sizes/counts are explicitly recorded; they are not the retained full-grid experiment.

The original pool extension at `d0ba9c0` observed **2.309×** versus the copied single buffer and **8.399×** versus equal-window Pipe at 1 MiB. [The review](reviews/pool-review.md) reopens all 200 original trials and independently rebuilds throughput, p95 and RSS. Those historical ratios remain descriptive observations; they are not relabeled as results of the new timing instrumentation. Original “completion latency” ended at producer ACK observation and did not directly measure consumer completion.

## Historical measurements and limits

The following schema-2 observations belong to immutable revision `c91bfef`, before the pool extension. They remain verified using that revision’s original source and checker. New measurements are reported separately above.

[Original receive-into API profile](results/macos-arm64/README.md) and [public receive-bytes plus copy profile](results/macos-arm64-pipe-bytes/README.md) each retain six sizes, four alternating pairs, 207,360 measured tensors (7.066 GiB) and their own JSON/HTML/raw records. All 96 revised trials remain visible. The profiles were executed sequentially, each with alternating mode order; differences between profiles are sensitivity observations, not an independently randomized causal API-ranking experiment.

The `c91bfef` Apple M5 Pro / Python 3.12.14 1 MiB shared/Pipe throughput ratios are 4.411 [3.833, 4.551] for receive-into and 4.186 [2.361, 4.307] for receive-bytes plus copy: medians [observed min, max] over all four pairs, not confidence intervals or ratios of table medians. Small payloads include pairs favoring either mode. The benefit remains conditional on this protocol, validation workload, host and runtime; it is not pure transport bandwidth, a universal crossover or production speedup.

The original approximately 4.10x observation remains a valid descriptive median of every original 1 MiB pair. The [immutable-source/data review](reviews/README.md) reopens commit `d2ca56d` and rechecks all 48 original raw trials and 207,360 messages. Original timings are not relabeled as measurements of this revision.

The [RSS diagnosis](reviews/rss-diagnosis.md) reproduces 4 MiB receive-into growth with both NumPy and bytearray targets, low traced live allocations and a plateau. Three rounds show that disabling macOS's large-allocation cache in the diagnostic child eliminates the growth; GC does not. This supports retention of freed temporary receive buffers by that cache as the main cause on this host/runtime, rather than accumulated live tensors. The public receive-bytes plus copy control also avoids the growth without an allocator override. In the `c91bfef` formal trials, the maximum paired sampled RSS at 4 MiB is 358.52 MiB for receive-into Pipe, versus 107.28 MiB for receive-bytes Pipe. These separate maxima are not paired physical-memory savings. No tracing, GC or allocator override is inserted into either formal timing profile. See [review evidence](reviews/README.md) for the source inspection, raw controls and limits.

Tables show median per-trial payload throughput and RTT percentiles, median warm baseline RSS, maximum paired sampled RSS and actual maximum sampling gap. Ratios and all underlying pairs are stored and verified in schema-2 JSON and rendered in HTML/README; no outlier/passing-only subset is selected.

Round-trip latency includes producer array generation and CRC, shared-buffer copy or Pipe transfer, receiver expected-value generation/full equality check/CRC and the acknowledgement. Throughput includes loop bookkeeping and ends after both workers finish measured bookkeeping. This is an end-to-end verified exchange workload, not pure IPC bandwidth, inference throughput or a zero-copy end-to-end implementation. Exact validation can mask a transport-only advantage; it is performed identically in both modes.

RSS samples add near-contemporaneous observations of producer and consumer. They include NumPy/runtime allocations, warm input/reference arrays, receive/shared buffers, per-message records and result serialization. They exclude the controller and multiprocessing resource tracker. Shared pages can be counted twice; RSS is not unique physical RAM, model-only memory, or total deployment memory. Sampling requests 5 ms but retains actual gaps/read durations and may miss short peaks. Per-process lifetime high-water observations are retained separately and are never summed as a simultaneous peak.

Workers stay alive until after a forced final sample. Dedicated control-reader threads keep a partially written result from blocking the controller's deadline checks. The controller reaps workers/readers, closes Pipe/Process/shared-memory handles, unlinks its segment and verifies that its name cannot be reopened, including startup-allocation failure paths. Tests independently reopen captured names after actual worker kills, exercise a real partial result, and check descriptor counts across repeated trials. This covers controller-managed normal/worker-failure exit, not killing the controller or power failure.

These are warm, finite, single-host observations with fixed size order, uncontrolled caches/thermals and no CPU pinning. Neither a universal speedup, production capacity nor a memory-efficiency ranking follows from them. The historical profiles have one payload in flight. The current pool adds a bounded SPSC window; multiple producers, lock-free operation, network transfer and GPUs remain outside scope.

## Verify

```sh
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests
python tools/run_mutations.py
python tools/check_project.py --directory results/macos-arm64-pool-reviewed
python tools/check_project.py --directory results/macos-arm64-pool
python tools/check_project.py --directory results/macos-arm64-pool-development
python tools/check_project.py
python tools/check_project.py --directory results/macos-arm64-pipe-bytes
python tools/diagnose_rss.py --verify
python tools/audit_original.py --verify
python tools/audit_pool_original.py --verify
```

Tests call the production sender/receiver, actual spawn-process supervisor, benchmark and report verifier. A hand-calculated metric oracle checks latency, complete-trial duration and paired RSS. Deliberately forged consistent CRCs, summaries and file digests must still fail independent data regeneration. Ten deliberate protocol source faults must fail behavioral assertions rather than import/hash checks. The Linux/macOS GitHub workflow is configured to execute real-process smoke measurements; their timings are not performance gates.

Historical verification needs full Git history. The diagnostic verifier checks retained controls rather than rerunning instrumented probes in CI. The workflow configures actual-process smoke tests for both public receive API profiles and the five-profile pool comparison.

See [methodology](docs/METHODOLOGY.md), [related systems and next experiments](docs/RELATED_WORK.md), [security scope](SECURITY.md) and [third-party materials](THIRD_PARTY_NOTICES.md).

## License status

No license has been selected for original project contributions. Installed dependencies retain their upstream licenses. No license from a sibling project is implicitly assigned here.

## Local macOS and Linux validation

Run `./tools/validate-local` on macOS to install pinned Colima/Lima tools, validate
one source snapshot natively and in a same-architecture Linux container, and retain
formal test logs plus separate real IPC JSON/HTML/RSS measurements. See
[setup, evidence and VM limitations](docs/LOCAL_VALIDATION.md). This does not require
GitHub Actions minutes; Linux VM measurements are not native-hardware claims.

The [2026-10-15 local validation record](reviews/local-validation-20261015/README.md)
passed all 17 suite steps on native macOS ARM64 and Colima Linux ARM64: each ran
46 normal tests, 46 optimized-Python tests, ten detected source faults, and 200
full measurement trials covering 654,450 exchanges. [Native measurements](reviews/local-validation-20261015/native-measurements.md)
and [virtualized Linux measurements](reviews/local-validation-20261015/linux-measurements.md)
are separate observations; worker RSS excludes VM/daemon overhead. The compact
record includes sanitized logs and derived observations; full raw JSON/HTML and
original logs remain local. This is not a GitHub-hosted CI success or x86_64 validation.

The [reviewed schema-2 validation](reviews/local-validation-audit-20261015/README.md)
adds import-origin binding, executed test IDs/commands, bounded cancellation and
owned-resource cleanup, plus a labelled `validation.html` entry point. Native
macOS ARM64 and Colima Linux ARM64 each passed 59 normal and 59 optimized tests,
ten source faults and the full 200-trial / 654,450-exchange grid. An additional
real Docker client-timeout probe verified evidence recovery, container removal
and VM shutdown. These new observations remain separate from the native primary
run above; no cross-environment speedup or whole-VM memory saving is inferred.

The [pre-publication review](reviews/prepublication-20261015/README.md) rechecked
the retained performance claims, both published local-record sets and all fetched
Git history, and repeated the 59-test suites on both platforms with actual IPC
smoke. Production code and historical numbers were unchanged. The project license
remains unselected; repository visibility has not been changed by that review.
