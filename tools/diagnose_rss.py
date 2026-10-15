"""Isolate public Pipe receive APIs and macOS large-allocation cache retention.

Instrumentation is excluded from performance trials. No private Connection API is used.
"""

import argparse
import gc
import hashlib
import json
import multiprocessing as mp
import multiprocessing.connection as connection_module
import os
from pathlib import Path
import platform
import time
import tracemalloc
import zlib

import numpy as np
import psutil

SIZE = 4194304
COUNT = 128
CHECKPOINTS = (0, 8, 16, 32, 64, 96, 128)


def receive(data, control, api, target_kind):
    target = np.empty(SIZE // 4, dtype=np.float32) if target_kind == "numpy" else bytearray(SIZE)
    process = psutil.Process()
    samples = []
    tracemalloc.start()
    def sample(count):
        current, peak = tracemalloc.get_traced_memory()
        samples.append({"count": count, "rss_bytes": process.memory_info().rss,
                        "traced_current_bytes": current, "traced_peak_bytes": peak})
    sample(0)
    for index in range(COUNT):
        if api == "into":
            if data.recv_bytes_into(target) != SIZE:
                raise ValueError("Incomplete tensor")
        else:
            raw = data.recv_bytes(SIZE)
            if len(raw) != SIZE:
                raise ValueError("Incomplete tensor")
            np.copyto(target, np.frombuffer(raw, dtype=np.float32))
            del raw
        data.send(zlib.crc32(target) & 0xffffffff)
        if index + 1 in CHECKPOINTS:
            sample(index + 1)
    before_gc = process.memory_info().rss
    collected = gc.collect()
    after_gc = process.memory_info().rss
    control.send({"samples": samples, "gc_collected": collected, "before_gc_rss_bytes": before_gc,
                  "after_gc_rss_bytes": after_gc, "malloc_large_cache": os.environ.get("MallocLargeCache")})
    data.close()
    control.close()


def measure(api, target, cache, trial):
    context = mp.get_context("spawn")
    left, right = context.Pipe()
    result, child_result = context.Pipe()
    payload = np.arange(SIZE // 4, dtype=np.float32).tobytes()
    expected = zlib.crc32(payload) & 0xffffffff
    worker = context.Process(target=receive, args=(right, child_result, api, target))
    previous = os.environ.get("MallocLargeCache")
    try:
        if cache is None:
            os.environ.pop("MallocLargeCache", None)
        else:
            os.environ["MallocLargeCache"] = cache
        worker.start()
    finally:
        if previous is None:
            os.environ.pop("MallocLargeCache", None)
        else:
            os.environ["MallocLargeCache"] = previous
    right.close()
    child_result.close()
    try:
        for _ in range(COUNT):
            left.send_bytes(payload)
            if not left.poll(10) or left.recv() != expected:
                raise ValueError("Diagnostic transfer/CRC failed")
        if not result.poll(10):
            raise TimeoutError("Diagnostic result missing")
        record = result.recv()
        worker.join(5)
        if worker.exitcode != 0:
            raise ValueError("Diagnostic worker did not exit cleanly")
        return {"api": api, "target": target, "cache_override": cache, "trial": trial,
                "verified_messages": COUNT, "payload_crc32": expected, "exitcode": worker.exitcode, **record}
    finally:
        if worker.is_alive():
            worker.kill()
            worker.join(3)
        worker.close()
        left.close()
        result.close()


def verify(report):
    if report["payload_bytes"] != SIZE or report["count"] != COUNT or report["script_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError("Diagnostic provenance differs")
    profiles = [("into", "numpy", None), ("into", "bytearray", None), ("bytes", "numpy", None)]
    if report["host"]["os"] == "Darwin":
        profiles.append(("into", "numpy", "0"))
    expected = [(trial, *profile) for trial in range(3) for profile in (profiles if trial % 2 == 0 else list(reversed(profiles)))]
    if [(r["trial"], r["api"], r["target"], r["cache_override"]) for r in report["runs"]] != expected:
        raise ValueError("Missing diagnostic controls")
    checksum = zlib.crc32(np.arange(SIZE // 4, dtype=np.float32)) & 0xffffffff
    for run in report["runs"]:
        if run["verified_messages"] != COUNT or run["payload_crc32"] != checksum or run["exitcode"] != 0 or run["malloc_large_cache"] != run["cache_override"]:
            raise ValueError("Diagnostic workload/outcome differs")
        if [s["count"] for s in run["samples"]] != list(CHECKPOINTS):
            raise ValueError("Incomplete diagnostic observations")
        for sample in run["samples"]:
            if not all(type(sample[k]) is int and sample[k] >= 0 for k in ("rss_bytes", "traced_current_bytes", "traced_peak_bytes")):
                raise ValueError("Invalid diagnostic memory observation")


def render(report):
    rows = []
    for r in report["runs"]:
        first, last = r["samples"][0], r["samples"][-1]
        rows.append(f'| {r["trial"]} | {r["api"]} | {r["target"]} | {r["cache_override"]} | {first["rss_bytes"]/1048576:.2f} | {last["rss_bytes"]/1048576:.2f} | {last["traced_current_bytes"]} |')
    return "\n".join(["# 4 MiB Pipe RSS diagnosis", "", "Actual instrumented, fresh-process controls; three rounds with reversed control order in the middle round. These are diagnosis observations, not throughput measurements. Each run verifies 128 payload CRCs; all samples and post-GC observations are retained in JSON.", "", "| Round | Receive API | Target | MallocLargeCache override | Initial RSS MiB | Final RSS MiB | Final traced live bytes |", "|---:|---|---|---|---:|---:|---:|", *rows, "", "Default-cache controls explicitly remove MallocLargeCache for their child; the parent's environment is restored after spawn. The cache-off control is macOS-only and diagnostic-only. No GC, tracing or allocator overrides are inserted into the formal timing runs. Tracemalloc does not account for every native allocation; the cache intervention and source inspection are additional evidence. These finite observations do not establish leak freedom on other runtimes or hosts.", ""])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reviews/rss-diagnosis.json"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        report = json.loads(args.output.read_text())
        verify(report)
        if args.output.with_suffix(".md").read_text() != render(report):
            raise ValueError("Diagnostic overview differs")
        print("Retained RSS diagnosis controls, checksums and summary verified; probes are not rerun.")
    else:
        if args.output.exists():
            raise ValueError("Use a new diagnostic output; never overwrite retained observations")
        report = {"schema_version": 1, "payload_bytes": SIZE, "count": COUNT,
                  "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "connection_source_sha256": hashlib.sha256(Path(connection_module.__file__).read_bytes()).hexdigest(),
                  "host": {"os": platform.system(), "release": platform.release(), "machine": platform.machine(),
                           "python": platform.python_version(), "numpy": np.__version__, "psutil": psutil.__version__}, "runs": []}
        profiles = [("into", "numpy", None), ("into", "bytearray", None), ("bytes", "numpy", None)]
        if platform.system() == "Darwin":
            profiles.append(("into", "numpy", "0"))
        for trial in range(3):
            for api, target, cache in (profiles if trial % 2 == 0 else reversed(profiles)):
                print("Diagnosing", trial, api, target, cache, flush=True)
                report["runs"].append(measure(api, target, cache, trial))
        verify(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".md").write_text(render(report))
