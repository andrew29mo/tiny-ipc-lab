# Protocol and measurement contract

## Workload

Every payload is a contiguous one-dimensional float32 tensor. Element `i` of sequence `s` is exactly `float32(i + s)`. Sizes and sequence limits keep all integers exactly representable in float32. Sequences 0..7 warm both modes; measured sequences are 8..count+7. Every generation changes every value, making stale reuse observable. There is no external model or dataset and no injected delay in performance measurements.

The producer fills its source array and computes CRC32. Both modes publish a fixed 16-byte sequence/length header; Pipe then sends raw tensor bytes into a preallocated receiver array, while shared mode copies into the shared slot before publishing the header. The consumer generates its expected array separately, compares every value, computes CRC32, and returns a fixed 12-byte sequence/CRC acknowledgement. The producer validates the acknowledgement before advancing or overwriting the slot. There is one logical payload in flight for either mode, not an unbounded queue or batched transfer.

The shared-memory API avoids sending payload bytes through the Pipe but does not eliminate the producer's input copy. Pipe uses `send_bytes`/`recv_bytes_into`, not Python object pickling. NumPy generation/equality/CRC cost is intentionally common to both paths. This compares a fully verified exchange under a specific protocol; it cannot isolate raw transport bandwidth by subtraction.

A preallocated Pipe target is not a guarantee of allocation-free internals: the installed CPython `recv_bytes_into` first obtains an internal received buffer before copying it into the caller's target. Its temporary buffers and runtime/allocator behavior are part of this actual API comparison. This source observation does not establish the cause of any particular RSS peak; the retained 4 MiB Pipe trials show substantial variation that needs separate profiling before attributing a leak or memory-efficiency result.

## Supervision and ownership

All children use `spawn`, including on Linux. The external controller creates and owns the optional shared segment, spawns the two measured workers, waits for initialization and eight warmups, and starts the producer. Worker control channels are separate from the measured data/acknowledgement Pipe. Each worker waits after sending its complete result, letting the controller take a final RSS observation before releasing both for graceful exit.

The controller bounds a trial's total startup/warmup/execution time (default 30 s). Protocol reads also have 10 s wait checks; a blocked send is bounded by external supervision. On failure it terminates/reaps surviving workers, closes Pipe endpoints and exited Process handles, closes/unlinks its shared segment and probes absence. Actual crash and suspended-consumer tests exercise this production path. Fault injection is limited to tests; no fault callback is passed by the benchmark. A killed controller, OS crash or machine power failure is outside the cleanup guarantee. All peers are trusted local code, not an exposed remote protocol.

## Evidence and fairness

The default six sizes each retain four pairs, alternating Pipe/shared and shared/Pipe. Fresh processes, payload sizes, generation recipe, counts, warmups and software versions are identical within comparisons. Size order is fixed. There is no selective rerun, post-run filtering, confidence interval or statistical-significance claim. Host scheduler contention, caches, allocator state and thermals remain uncontrolled.

RTT starts before producer generation/CRC and ends after acknowledgement validation. Each raw row retains sequence, start/end and input/ack CRC. Every consumer row retains sequence, observed CRC and verified element count. Overall duration covers the producer loop and final consumer bookkeeping, including gaps between messages. CPU seconds are per-worker process CPU time, not energy/power. Startup and warmup are excluded from timing; resident warm allocations remain in memory measurements.

The controller samples RSS at a requested 5 ms cadence, retaining actual start/end, ordered sample gaps and both process values. A sample before the producer starts and after both workers complete is mandatory. Sampling continues during result collection/serialization; large gaps remain visible. Paired peak means the maximum sum within one near-contemporaneous observation, never the sum of unrelated per-process peaks. Shared pages may be double-counted; allocator-retained pages and transient missed spikes prevent unique-physical-memory conclusions. The controller/resource tracker are excluded. Baseline is the first post-warmup pair of process observations; it is not a model-only or incremental-buffer allocation measurement.

Each raw trial is losslessly stored as gzip JSON with a digest in the report index. The verifier checks all expected sequences and counts, regenerates expected CRCs using a separate float64 expression cast to float32, reconstructs timing/RSS summaries and requires clean exits and unlink evidence. It verifies exact balanced order, workload fingerprints and equal software versions, then regenerates JSON/HTML/README exactly. A SHA-256 alone does not prove that measurements were honestly made; behavioral tests challenge the production transfer and complete-value verification paths.

## Primary references

- [Python 3.12 SharedMemory](https://docs.python.org/3.12/library/multiprocessing.shared_memory.html): sharing a buffer, close versus unlink and NumPy views. One controller owns unlink; no private resource-tracker manipulation is used.
- [Python Connection objects](https://docs.python.org/3.12/library/multiprocessing.html#connection-objects): raw-byte sending/receiving and bounded read checks.
- [psutil](https://psutil.io/): process RSS observations. Aggregated RSS is not deduplicated physical memory.

These are API references, not results from benchmarked competing projects.
