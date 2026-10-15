# Tiny IPC Lab

A single-machine verification bench for transferring float32 tensors between two processes using **Pipe raw bytes** or **one reusable shared-memory buffer**.

The question is: **At what payload sizes does sharing a buffer justify its ownership and cleanup complexity?** This project measures a complete verified round trip, including real data generation, copies, validation and acknowledgements. It does not assume a shared-memory speedup.

## MVP

- One spawned producer, one spawned consumer, and an external controller that samples RSS and owns cleanup.
- One payload in flight in both modes. A sequence/length header and sequence/CRC acknowledgement travel over the same kind of Pipe.
- Pipe uses `send_bytes` with a declared public receive API: the original `recv_bytes_into`, or `recv_bytes` plus copying into the same preallocated target. It does not pickle NumPy arrays.
- Shared mode copies the producer's array into a fixed buffer, publishes its header, then waits for acknowledgement before reuse. The consumer reads a read-only NumPy view; this API guard is not OS-level isolation.
- Every value must exactly match an independently generated expected tensor before acknowledgement. CRC32 provides additional sender/receiver/evidence accounting.
- Tests exercise stale/repeated/skipped sequences, middle-value corruption, short payloads, premature buffer reuse, wrong acknowledgements, real worker crashes, stalled workers and shared-segment cleanup.
- Lossless compressed raw observations, independently regenerated expected CRCs, canonical JSON/HTML/README, and alternating paired trials.

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

## Measurements and limits

[Original receive-into API profile](results/macos-arm64/README.md) and [public receive-bytes plus copy profile](results/macos-arm64-pipe-bytes/README.md) each retain six sizes, four alternating pairs, 207,360 measured tensors (7.066 GiB) and their own JSON/HTML/raw records. All 96 revised trials remain visible. The profiles were executed sequentially, each with alternating mode order; differences between profiles are sensitivity observations, not an independently randomized causal API-ranking experiment.

The revised Apple M5 Pro / Python 3.12.14 1 MiB shared/Pipe throughput ratios are 4.411 [3.833, 4.551] for receive-into and 4.186 [2.361, 4.307] for receive-bytes plus copy: medians [observed min, max] over all four pairs, not confidence intervals or ratios of table medians. Small payloads include pairs favoring either mode. The benefit remains conditional on this protocol, validation workload, host and runtime; it is not pure transport bandwidth, a universal crossover or production speedup.

The original approximately 4.10x observation remains a valid descriptive median of every original 1 MiB pair. The [immutable-source/data review](reviews/README.md) reopens commit `d2ca56d` and rechecks all 48 original raw trials and 207,360 messages. Original timings are not relabeled as measurements of this revision.

The [RSS diagnosis](reviews/rss-diagnosis.md) reproduces 4 MiB receive-into growth with both NumPy and bytearray targets, low traced live allocations and a plateau. Three rounds show that disabling macOS's large-allocation cache in the diagnostic child eliminates the growth; GC does not. This supports retention of freed temporary receive buffers by that cache as the main cause on this host/runtime, rather than accumulated live tensors. The public receive-bytes plus copy control also avoids the growth without an allocator override. In revised formal trials, the maximum paired sampled RSS at 4 MiB is 358.52 MiB for receive-into Pipe, versus 107.28 MiB for receive-bytes Pipe. These separate maxima are not paired physical-memory savings. No tracing, GC or allocator override is inserted into either formal timing profile. See [review evidence](reviews/README.md) for the source inspection, raw controls and limits.

Tables show median per-trial payload throughput and RTT percentiles, median warm baseline RSS, maximum paired sampled RSS and actual maximum sampling gap. Ratios and all underlying pairs are stored and verified in schema-2 JSON and rendered in HTML/README; no outlier/passing-only subset is selected.

Round-trip latency includes producer array generation and CRC, shared-buffer copy or Pipe transfer, receiver expected-value generation/full equality check/CRC and the acknowledgement. Throughput includes loop bookkeeping and ends after both workers finish measured bookkeeping. This is an end-to-end verified exchange workload, not pure IPC bandwidth, inference throughput or a zero-copy end-to-end implementation. Exact validation can mask a transport-only advantage; it is performed identically in both modes.

RSS samples add near-contemporaneous observations of producer and consumer. They include NumPy/runtime allocations, warm input/reference arrays, receive/shared buffers, per-message records and result serialization. They exclude the controller and multiprocessing resource tracker. Shared pages can be counted twice; RSS is not unique physical RAM, model-only memory, or total deployment memory. Sampling requests 5 ms but retains actual gaps/read durations and may miss short peaks. Per-process lifetime high-water observations are retained separately and are never summed as a simultaneous peak.

Workers stay alive until after a forced final sample. Dedicated control-reader threads keep a partially written result from blocking the controller's deadline checks. The controller reaps workers/readers, closes Pipe/Process/shared-memory handles, unlinks its segment and verifies that its name cannot be reopened, including startup-allocation failure paths. Tests independently reopen captured names after actual worker kills, exercise a real partial result, and check descriptor counts across repeated trials. This covers controller-managed normal/worker-failure exit, not killing the controller or power failure.

These are warm, finite, single-host observations with fixed size order, uncontrolled caches/thermals and no CPU pinning. Neither a universal speedup, production capacity nor a memory-efficiency ranking follows from them. This MVP has no pipelined ring, multiple producers, lock-free algorithm, network transfer or GPU path.

## Verify

```sh
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests
python tools/run_mutations.py
python tools/check_project.py
python tools/check_project.py --directory results/macos-arm64-pipe-bytes
python tools/diagnose_rss.py --verify
python tools/audit_original.py --verify
```

Tests call the production sender/receiver, actual spawn-process supervisor, benchmark and report verifier. A hand-calculated metric oracle checks latency, complete-trial duration and paired RSS. Deliberately forged consistent CRCs, summaries and file digests must still fail independent data regeneration. Five deliberate protocol source faults must fail behavioral assertions rather than import/hash checks. Linux/macOS CI also executes real-process smoke measurements; their timings are not performance gates.

Historical verification needs full Git history. The diagnostic verifier checks retained controls rather than rerunning instrumented probes in CI. Both public receive API profiles also get actual-process smoke tests in CI.

See [methodology](docs/METHODOLOGY.md), [related systems and next experiments](docs/RELATED_WORK.md), [security scope](SECURITY.md) and [third-party materials](THIRD_PARTY_NOTICES.md).

## License status

No license has been selected for original project contributions. Installed dependencies retain their upstream licenses. No license from a sibling project is implicitly assigned here.
