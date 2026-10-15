# Tiny IPC Lab

A single-machine verification bench for transferring float32 tensors between two processes using **Pipe raw bytes** or **one reusable shared-memory buffer**.

The question is: **At what payload sizes does sharing a buffer justify its ownership and cleanup complexity?** This project measures a complete verified round trip, including real data generation, copies, validation and acknowledgements. It does not assume a shared-memory speedup.

## MVP

- One spawned producer, one spawned consumer, and an external controller that samples RSS and owns cleanup.
- One payload in flight in both modes. A sequence/length header and sequence/CRC acknowledgement travel over the same kind of Pipe.
- Pipe uses `send_bytes` and a preallocated `recv_bytes_into` array; it does not pickle NumPy arrays.
- Shared mode copies the producer's array into a fixed buffer, publishes its header, then waits for acknowledgement before reuse. The consumer reads a NumPy view of that buffer.
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
```

The default grid is 64 B, 1 KiB, 16 KiB, 256 KiB, 1 MiB and 4 MiB, each with four fresh-process pairs in alternating Pipe/shared order. A fixed size-dependent message budget is used: `max(64, min(8192, 256 MiB // payload_bytes))`. Each mode receives the same sequence of tensors and message count at a given size. Eight identical warmups precede each measured trial. There is no model or external dataset.

A small actual-process smoke run:

```sh
tiny-ipc-lab --output results/local/smoke --sizes 64 4096 --count 17 --pairs 2
python tools/check_project.py --directory results/local/smoke --smoke
```

Output directories must be new. Completed raw trials survive a later failure; an incomplete index and supervised-failure cleanup metadata are retained, without inventing the failed trial's missing observations. Custom sizes/counts are explicitly recorded; they are not the retained full-grid experiment.

## Measurements and limits

[Recorded macOS observations](results/macos-arm64/README.md) include all prespecified trial pairs, raw records and an offline HTML report. The table shows median per-trial payload throughput and RTT percentiles, median warm baseline RSS, maximum paired sampled RSS and the actual maximum sampling gap. Individual trials and every paired throughput ratio remain available in HTML details and JSON; no outlier/passing-only subset is selected.

The retained Apple M5 Pro / Python 3.12.14 run verified 207,360 measured tensors (7.066 GiB of payload) across 48 trials. The median of the four paired shared/Pipe throughput ratios was 1.027 [0.725, 1.312] at 64 B, 3.265 [2.389, 3.682] at 256 KiB, and 4.101 [3.701, 4.575] at 1 MiB. Brackets are observed min/max, not confidence intervals. The smallest case includes pairs favoring either mode; larger-payload observations do not establish a universal crossover or production speedup. Ratios are paired medians, not ratios of the table's independently aggregated medians.

The 4 MiB Pipe case had variable resident memory, with a maximum paired sampled RSS of 358.30 MiB, versus 104.44 MiB for shared mode. These maxima may come from different trials; they are not a paired saving estimate. The cause of the Pipe RSS variation is not established. The preallocated receive array does not make Python's internal Pipe receive path allocation-free. Retain this observation without labeling it a leak or a deduplicated-memory advantage.

Round-trip latency includes producer array generation and CRC, shared-buffer copy or Pipe transfer, receiver expected-value generation/full equality check/CRC and the acknowledgement. Throughput includes loop bookkeeping and ends after both workers finish measured bookkeeping. This is an end-to-end verified exchange workload, not pure IPC bandwidth, inference throughput or a zero-copy end-to-end implementation. Exact validation can mask a transport-only advantage; it is performed identically in both modes.

RSS samples add near-contemporaneous observations of producer and consumer. They include NumPy/runtime allocations, warm input/reference arrays, receive/shared buffers, per-message records and result serialization. They exclude the controller and multiprocessing resource tracker. Shared pages can be counted twice; RSS is not unique physical RAM, model-only memory, or total deployment memory. Sampling requests 5 ms but retains actual gaps/read durations and may miss short peaks. Per-process lifetime high-water observations are retained separately and are never summed as a simultaneous peak.

Workers stay alive until after a forced final sample. The controller reaps both workers, closes its own shared-memory handle, unlinks the segment and verifies that its name cannot be reopened. Crash tests independently reopen captured names after actual worker kills. This covers controller-managed normal/worker-failure exit, not killing the controller or power failure.

These are warm, finite, single-host observations with fixed size order, uncontrolled caches/thermals and no CPU pinning. Neither a universal speedup, production capacity nor a memory-efficiency ranking follows from them. This MVP has no pipelined ring, multiple producers, lock-free algorithm, network transfer or GPU path.

## Verify

```sh
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests
python tools/run_mutations.py
python tools/check_project.py
```

Tests call the production sender/receiver, actual spawn-process supervisor, benchmark and report verifier. A hand-calculated metric oracle checks latency, complete-trial duration and paired RSS. Deliberately forged consistent CRCs, summaries and file digests must still fail independent data regeneration. Five deliberate protocol source faults must fail behavioral assertions rather than import/hash checks. Linux/macOS CI also executes real-process smoke measurements; their timings are not performance gates.

See [methodology and references](docs/METHODOLOGY.md), [security scope](SECURITY.md) and [third-party materials](THIRD_PARTY_NOTICES.md).

## License status

No license has been selected for original project contributions. Installed dependencies retain their upstream licenses. No license from a sibling project is implicitly assigned here.
