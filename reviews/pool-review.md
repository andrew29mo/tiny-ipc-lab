# Bounded-pool review

## Original claims and independent reconstruction

[The immutable d0ba9c0 audit](pool-original-d0ba9c0.json) reopens the producing source and data, executes its original verifier, and independently reconstructs throughput, p95 ACK-observed latency (NumPy linear quantile), and paired RSS for all 200 trials / 654,450 measured tensors. The 392,670 streaming-profile messages also pass an additional FIFO ACK-timestamp check.

The original 1 MiB pool-4 / copied-single-buffer ratio is 2.309 [1.341, 3.489]; pool-4 / equal-window Pipe is 8.399 [5.881, 8.518]. Each is the median [observed min, max] of all five within-block ratios. None is a confidence interval, ratio of independently aggregated medians, universal effect or model inference speedup.

The first ratio changes slot capacity, generation/copy behavior and protocol. The second holds capacity, producer loan handling, header/release identity and validation constant, but includes the actual Python Pipe receive allocation/copy and kernel transport costs. It is a comparison against this public-API Pipe implementation, not against every optimized IPC implementation. The old development round remains separately labeled because it overlapped test work; it was not filtered using a performance threshold.

## Findings and repairs

1. **Producer ACK observation is not consumer completion.** The original timestamps end only when the producer reads an ACK. A pool producer reads ACKs while reclaiming a slot or draining, so an already completed consumer can wait for its ACK to be observed. Also, pool message attempt timestamps precede waiting for a free slot, while legacy messages begin after the preceding exchange. The original labels and documented definitions describe a real measurement, but those numbers cannot establish application-latency superiority or pure transport RTT. Original consumer-ready timestamps were never recorded and are not reconstructed.

   Schema 4 adds actual consumer timestamps after full equality/CRC and the declared delay, immediately before sending ACK. It separately reports attempt-to-ACK-observation, admitted-to-consumer-ready, attempt-to-consumer-ready, admission waiting and ACK-observation lag. Every row must have consistent monotonic phase times; requested consumer delay must really elapse. A common externally scheduled arrival trace is still absent, so these metrics are not offered-load-matched application latency.

2. **The old ownership verifier omitted global FIFO ACK chronology.** [A retained synthetic counterexample](pool-fifo-counterexample.json), explicitly not measurement evidence, has the second FIFO ACK observed before the first. The immutable original `summarize` accepts it; the new verifier rejects it specifically for FIFO ordering. Every original measured streaming trace passes the stronger ordering check: this was a false-negative validation gap, not an observed transport-ordering failure.

3. **The old in-place unit test did not directly challenge the production generator destination.** New actual-process instrumentation wraps the real producer's constructor and generation function without replacing the generation algorithm or transfer. It checks that every warm and measured generation output shares storage with the current owned shared slot. The real consumer still checks the full tensor. A source mutation that correctly generates into a staging array and copies it into the slot must fail this test, even though numerical output would remain correct.

4. **Protocol rejection and tail/startup coverage were incomplete.** Added tests independently vary ACK sequence, slot, generation, CRC and length, and send a duplicate release. Rejection must leave ownership pending. Invalid publication fields must neither ACK nor advance the consumer. Actual processes cover counts below capacity, exact windows and partial tails, including capacity 16 with one measured message after eight warmups. Pool allocation followed by Pipe-allocation failure must unlink the captured name.

5. **Legacy protocol constructors accepted the new pool mode names.** They could then skip the legacy payload path when directly called with a pool mode. The actual benchmark dispatcher already selected the correct pool classes, so retained benchmark data was unaffected. Legacy constructors now reject pool modes explicitly instead of accepting a misrouted call.

## Fresh measured findings

The reviewed full grid again retains 200 trials and 654,450 measured tensors. At 1 MiB normal load, pool-4 / single-buffer is 1.921 [1.836, 3.350], and pool-4 / equal-window Pipe is 7.303 [6.399, 8.507]. These are new all-five-block descriptive throughput ratios; instrumentation and host conditions differ from the original run, and the change in ratio is not an isolated causal estimate of the instrumentation overhead.

At 1 MiB normal load, median per-trial admitted-to-ready p95 is 0.359 ms for single-buffer, 0.857 ms for pool-4 and 1.546 ms for windowed Pipe. Corresponding maximum sampled paired RSS is 84.55, 89.67 and 90.30 MiB. Pool throughput benefits do not imply lower latency or physical-memory savings.

The 1 ms delayed-ACK case makes the clock distinction especially clear: admitted-to-ready p95 is 6.472 ms for pool-4 versus 4.503 ms for equal-window Pipe, while producer ACK-observed p95 is 8.195 versus 11.837 ms. The relative latency ordering reverses depending on the clock. Pool-4's throughput ratio versus single-buffer falls to 1.088 [0.951, 1.269], including a slower pair. These finite closed-loop observations do not establish application latency under a common externally scheduled workload.

## Ownership, backpressure and crash conclusions

The production pool directly fills borrowed slots and publishes only after generation/CRC. The receiver checks exact values and the expected sequence/slot/generation; only a matching release of the oldest pending publication frees a slot. A full pool waits for an ACK without growing payload capacity, dropping or overwriting. A retained borrowed view becomes read-only at publication, and receiver views are read-only; other aliases and hostile peers remain outside this API guard.

The blocked-acquire test holds two published slots without ACKs, proves a third acquisition cannot return, then releases one and checks its new generation. Actual-process crash tests suspend the consumer, observe four measured publications through the real producer, kill either worker, reap both workers/readers and independently probe that the captured segment name cannot be reopened. Timeout, repeated descriptor counts and startup-allocation failure are also covered. There is no individual-slot recovery or continued service after a peer crash. Killing the controller or the machine is outside the cleanup guarantee.

Ten deliberate source faults now include replacing real worker in-place generation with staging plus copy. Normal and optimized Python suites challenge the production implementation; correctness does not rely on Python `assert` statements being enabled.

## RSS, reporting and provenance

RSS is the maximum near-contemporaneous sum of two sequential worker samples, bracketed before measured traffic and after both workers finish while they remain alive. It includes warm arrays, touched pool pages, runtime/internal Pipe allocations, evidence records and result serialization. Shared pages can be counted twice, controller/resource-tracker memory is excluded, and spikes can be missed. Separate maximum RSS values are not paired or deduplicated physical-memory savings. The HTML now exposes maximum recorded sampling gaps alongside the RSS values; JSON retains every sample.

Original schema-2 and schema-3 data remain bound to immutable c91bfef and d0ba9c0 implementations, respectively. The [reviewed schema-4 measurements](../results/macos-arm64-pool-reviewed/README.md) were executed anew as one complete prespecified grid, without concurrent tests or validation processes launched by this task. No old timestamp, speed ratio or source hash was relabeled. All five rotating blocks remain visible. README findings are generated from those complete blocks and checked against JSON/HTML/raw evidence in CI.

```sh
python tools/audit_pool_original.py --verify
python tools/check_project.py --directory results/macos-arm64-pool-reviewed
python tools/run_mutations.py
```
