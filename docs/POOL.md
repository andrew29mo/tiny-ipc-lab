# Bounded loans and comparison contract

The production implementation is in `tiny_ipc_lab.pool`, used by the actual spawned workers in `tiny_ipc_lab.experiment`. The five-profile runner is `tiny_ipc_lab.pool_bench`.

## Ownership

A single producer and single consumer share one controller-owned segment containing `capacity * payload_bytes` bytes, with capacity restricted to 1..16. The default pool has four slots. The producer keeps a bounded free-slot deque and FIFO pending publications. There is at most one unpublished producer loan. Each slot progresses through:

```text
FREE -> LOANED (fill in place) -> PUBLISHED (immutable borrowed view)
     -> consumer checks every value -> matching ACK -> FREE
```

Each publication carries a 32-byte sequence/slot/generation/length header. The 28-byte ACK repeats sequence/slot/generation and the validated CRC. Slot `sequence % capacity` must have generation `sequence // capacity + 1`, including the eight warmup messages. Neither stale ACKs nor stale headers can authorize reuse, even when the slot number is the same. Invalid data receives no ACK. Rejected releases leave the pending loan owned; the trial fails and the controller tears down the whole exchange. This MVP does not recover an individual slot and continue after a peer crash.

`acquire` waits for the oldest ACK when no free slot exists. It does not allocate more payload storage, overwrite, drop, or enqueue an unbounded set of publications. `publish` revokes the returned NumPy view's write flag and sends the header only after the caller finishes generation and CRC. The consumer's shared views are read-only. These flags prevent accidental writes through those views, not writes through other aliases or hostile peers; they are not OS isolation. Retaining an alias to a loan after publication is outside the ownership contract.

The producer directly calls NumPy generation with the owned shared slot as `out`; it retains a base array but no separate staging frame for pool profiles. The windowed Pipe control fills local slots in the same way, then transmits raw bytes. All Pipe payloads in the new comparison use the public `recv_bytes` API plus a copy into a preallocated consumer target. No private Connection internals or allocator overrides are used.

Eight warmup messages are drained before measured messages begin. Every measured message is drained at the end, including counts smaller than the pool or not divisible by its capacity. Capacity bounds payload slots, not the total worker footprint: retained evidence records grow with message count, and the Python runtime and Pipe can have internal buffers.

## Five profiles

| Profile | Slots / maximum logical in flight | Producer generation | Payload transfer |
|---|---:|---|---|
| pipe | 1 | staging array | existing sequence/length protocol, raw Pipe bytes |
| shared | 1 | staging array, then shared copy | existing single-buffer protocol |
| pool_1 | 1 | shared loan, in place | slot/generation publication and release |
| pool_n | 4 by default | shared loan, in place | slot/generation publication and release |
| window_pipe | same as pool_n | local loan, in place | same slot/generation protocol and window, raw Pipe bytes |

`pool_1 / shared` explores in-place writing with a capacity-one control, but also includes the new metadata/state overhead. `pool_n / shared` combines in-place writing, pipelining and protocol changes. `pool_n / window_pipe` is the equal-window comparison: metadata, capacity, producer loan behavior and validation are common; transport, consumer buffer allocation/copy, and shared page accounting still differ. It is inappropriate to label all three ratios a pure shared-memory effect.

## Fixed experiment

The first complete development run overlapped local test execution near its end. It is retained separately in [development evidence](../results/macos-arm64-pool-development/README.md) for transparency, and is not used for the primary findings. The complete primary grid was then executed once with no concurrent validation/test processes launched by this task. Both rounds retain every block and bind to the same package source; this separation was based on known workload interference rather than a performance threshold. Normal desktop/OS interference remains uncontrolled.

The normal grid retains 64 B, 1 KiB, 16 KiB, 256 KiB, 1 MiB and 4 MiB. Message counts use the existing size-dependent policy. Two additional slow-consumer cases use 16 KiB and 1 MiB, with 129 messages and a requested 1 ms sleep after full validation but before ACK for each measured message. That delay is explicitly recorded; it does not apply to warmup and is not an exact service-time guarantee.

Every case has five blocks, each containing all five profiles in rotating order. Every profile occupies each order position once. Fresh processes, values, sequence order, message count, warmups, receive API and consumer delay match within a case. All blocks remain in the report, including unfavorable results; there is no pass-only filter. Fixed case order and shared-host interference remain uncontrolled.

The workload is closed-loop and offered as fast as capacity permits. It is not an externally scheduled arrival replay. Completion latency starts immediately before legacy generation or pool acquisition and ends after the producer processes the valid ACK. It includes capacity waiting, generation, validation, and ACK scheduling. The producer consumes ACKs when it needs a slot or drains the final window, so completion latency can exceed consumer-ready latency. The stored `round_trip_ms` summary key is retained for compatibility; the new tables label it **completion latency**.

Capacity-reclaim events mean that no slot was locally free; the ACK may already be queued. Reclaim time includes ACK processing and bookkeeping, not only time blocked on a slow consumer. Throughput ends after both workers finish measured bookkeeping and includes tail drain. It excludes process startup and warmup. Process CPU seconds, sampled RSS, lifetime high-water RSS, actual sampling gaps and all message timings remain in raw records.

Memory sampling uses the same supervisor for every profile, with a pre-traffic sample and a final sample while both workers remain alive. Baseline includes warm allocations. Paired RSS can double-count shared pages, excludes controller/resource-tracker memory, and may miss spikes between sequential samples. It is not unique physical RAM or a payload-only allocation count.

## Tests and retained history

Tests invoke actual sender/receiver classes, spawn workers and the production report runner. Protocol tests hold a full pool without returning ACKs, verify that a third acquisition blocks, then check reuse with a new generation. Stale header/release tests use otherwise valid data and identity fields. Actual-process tests use capacity three and 17 messages, covering partial final windows after eight warmups, capacity-one controls, slow consumers, timeouts and descriptor cleanup. Crash tests first observe four actual measured publications while the consumer is suspended, then kill either worker and independently check that the shared name cannot be reopened.

Nine source mutations challenge the old and new protocols. Report tests reject forged statistics, missing blocks, inconsistent workloads, wrong generations, early slot reuse and self-consistent wrong CRCs. The final verifier independently regenerates expected CRCs with float64 arithmetic cast to float32, rebuilds ownership/timing/RSS statistics and requires canonical JSON/HTML/README.

Schema-2 reports remain measurements of immutable revision `c91bfef`, verified with that revision's source and verifier. They are retained as history, not relabeled as pool measurements. Schema 3 binds the new five-profile observations to the complete current package source hash. Historical checks require full Git history. The original `d2ca56d` audit and RSS diagnostic remain independently available.
