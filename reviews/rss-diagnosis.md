# 4 MiB Pipe RSS diagnosis

Actual instrumented, fresh-process controls; three rounds with reversed control order in the middle round. These are diagnosis observations, not throughput measurements. Each run verifies 128 payload CRCs; all samples and post-GC observations are retained in JSON.

| Round | Receive API | Target | MallocLargeCache override | Initial RSS MiB | Final RSS MiB | Final traced live bytes |
|---:|---|---|---|---:|---:|---:|
| 0 | into | numpy | None | 38.92 | 303.14 | 1795 |
| 0 | into | bytearray | None | 42.83 | 301.91 | 1723 |
| 0 | bytes | numpy | None | 38.83 | 51.16 | 1899 |
| 0 | into | numpy | 0 | 38.20 | 44.33 | 1795 |
| 1 | into | numpy | 0 | 38.28 | 44.39 | 1795 |
| 1 | bytes | numpy | None | 38.67 | 52.17 | 1899 |
| 1 | into | bytearray | None | 42.81 | 303.19 | 1723 |
| 1 | into | numpy | None | 38.70 | 301.80 | 1795 |
| 2 | into | numpy | None | 38.77 | 301.69 | 1795 |
| 2 | into | bytearray | None | 42.80 | 303.06 | 1723 |
| 2 | bytes | numpy | None | 38.89 | 51.42 | 1899 |
| 2 | into | numpy | 0 | 38.14 | 44.22 | 1795 |

Default-cache controls explicitly remove MallocLargeCache for their child; the parent's environment is restored after spawn. The cache-off control is macOS-only and diagnostic-only. No GC, tracing or allocator overrides are inserted into the formal timing runs. Tracemalloc does not account for every native allocation; the cache intervention and source inspection are additional evidence. These finite observations do not establish leak freedom on other runtimes or hosts.
