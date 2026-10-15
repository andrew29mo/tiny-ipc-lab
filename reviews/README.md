# IPC review evidence

## Original approximately 4.10x observation

[original-d2ca56d.json](original-d2ca56d.json) reopens immutable commit `d2ca56def790fd4877c4ef62d4496e05c5123a20`, including its original verifier, source and all 48 hash-linked raw files. Every original sequence/CRC and timing/RSS summary is rechecked. The original 207,360 measured messages remain accounted for.

At 1 MiB, the four shared/Pipe ratios were 4.575, 3.735, 4.468 and 3.701; their median was 4.101. No pair was excluded. This is a descriptive end-to-end observation of `recv_bytes_into` versus a shared slot, including generation, copies, complete validation and ACK. It is not pure transport bandwidth, a confidence interval or a universal shared-memory effect. A ratio of independently aggregated table medians would be a different statistic.

Revised schema-2 measurements add an explicit receive-API policy, all-pair aggregate verification, bounded control-result supervision and cleanup checks. They are newly executed measurements and do not relabel the original trial timings.

## 4 MiB RSS root cause on this host

[rss-diagnosis.json](rss-diagnosis.json) and [its table](rss-diagnosis.md) retain three fresh-process rounds, reversing control order in the middle round. Each run checks 128 actual 4 MiB transfers, including both NumPy and bytearray receive targets. The workload uses the public Pipe APIs, not a patched runtime or private receive implementation.

The default-cache `recv_bytes_into` receiver grows to approximately 302–303 MiB and plateaus within this finite experiment; traced live allocations remain around 2 KiB after the target is allocated. Changing the destination to bytearray does not remove growth. Explicit GC does not produce the large reduction. Keeping the same API and setting `MallocLargeCache=0` before the diagnostic child starts holds final RSS around 44 MiB. A second public API, `recv_bytes` followed by a copy into the same NumPy target, holds final RSS around 51–52 MiB without changing allocator settings.

These controlled observations support large-allocation-cache retention of temporary receive buffers as the main explanation of the observed resident growth on this macOS/runtime combination. They do not show accumulated live tensors or an unbounded application-level leak. Tracemalloc alone cannot exclude all native allocations or leaks. The cache intervention, repeated controls, plateau, and runtime source inspection strengthen the diagnosis; they are not a cross-platform leak-freedom guarantee.

CPython's [Connection implementation](https://github.com/python/cpython/blob/v3.12.14/Lib/multiprocessing/connection.py) receives payloads into an internal BytesIO buffer even for `recv_bytes_into`. Its [BytesIO implementation](https://github.com/python/cpython/blob/v3.12.14/Modules/_io/bytesio.c) can resize that buffer when exposing its value. Apple's [large-allocation cache](https://github.com/apple-oss-distributions/libmalloc/blob/main/src/magazine_large.c) retains freed allocations for reuse. This explains why preallocating the caller's target does not by itself bound resident temporary-buffer pages. The published allocator source is context; the actual intervention supplies host-specific evidence rather than assuming that every OS release is identical to that source revision.

The cache-off control is diagnostic-only. The main timing experiments retain the original runtime settings and separately measure both public receive APIs. There is no GC, tracing or allocator override in those timing trials. RSS includes warm arrays, internal buffers and bookkeeping, can double-count shared pages, and is not unique physical RAM. Comparisons of separate maximum RSS values are not paired physical-memory saving estimates.

## Verification

```sh
python tools/audit_original.py --verify
python tools/diagnose_rss.py --verify
```

The historical checker requires full Git history. The diagnostic checker verifies retained data and its generating script hash; it does not rerun probes in CI. To rerun instrumentation, use a new output path with `python tools/diagnose_rss.py --output results/local/rss-new.json`.
