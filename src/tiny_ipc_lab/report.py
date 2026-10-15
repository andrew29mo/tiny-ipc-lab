"""Reconcile retained observations, then render offline JSON/HTML evidence."""

import gzip
import hashlib
import html
import json
import math
from pathlib import Path
import re
from statistics import median
import zlib

import numpy as np

from .experiment import fingerprint, source_hash
from .protocol import RECIPE, WARMUP, check_config

SCOPE = [
    "Single producer, single consumer, spawn processes, one acknowledged payload in flight, one fixed shared slot; no pipelining or lock-free claim.",
    "Pipe uses send_bytes with a declared public receive API: recv_bytes_into, or recv_bytes plus a copy into the same preallocated target. No arrays are pickled. Shared mode copies into one shared slot. Both use the same header, validation and acknowledgement.",
    "Every received tensor is checked by exact value equality against independently generated expected values before acknowledgement. CRC32 is additional accounting, not the sole correctness check.",
    "Measured round trip includes float32 payload generation, producer CRC, shared copy or Pipe transfer, receiver expected-value generation/full validation/CRC and acknowledgement. Overall throughput also includes per-message record keeping. This is not pure transport, a model inference benchmark or a zero-copy end-to-end claim.",
    "Eight identical warmups precede measurement. Fresh processes and alternating mode order are used per pair; startup is excluded. Fixed size order, shared-host interference, allocator state, caches and thermals remain uncontrolled. Finite single-host observations are descriptive, not confidence intervals or universal speedups.",
    "The controller samples producer/consumer RSS sequentially at a requested 5 ms cadence, with actual gaps and read duration retained. Paired RSS can double-count shared pages and miss spikes. Warm baseline, input/reference arrays, record buffers and result serialization are included; controller/resource-tracker memory is excluded. It is not unique physical RAM or total deployment memory.",
    "Workers stay alive after measurement until the controller takes the final sample. The controller closes/unlinks its owned segment after workers exit and probes that its name cannot be reopened. Worker-crash cleanup is tested. Controller kill, machine failure and platform-wide leak freedom are outside this guarantee.",
]


def need(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def distribution(values):
    values = sorted(values)
    need(bool(values), "Empty distribution")
    def q(fraction):
        position = (len(values) - 1) * fraction
        i = int(position)
        return values[i] + (values[min(i + 1, len(values) - 1)] - values[i]) * (position - i)
    return {"min": values[0], "p50": q(.5), "p95": q(.95), "p99": q(.99), "max": values[-1]}


def summarize(run, *, check_values=True):
    mode, size, count = run["mode"], run["payload_bytes"], run["count"]
    check_config(mode, size, count)
    need(run["pipe_receive"] in ("into", "bytes"), "Unknown receive API")
    need(run["warmup"] == WARMUP, "Warmup policy changed")
    producer, consumer = run["producer"], run["consumer"]
    need(producer["event"] == consumer["event"] == "done", "Unfinished trial")
    need(finite(producer["start_s"]) and finite(producer["end_s"]) and finite(consumer["end_s"]), "Invalid worker clock")
    rows, received = producer["records"], consumer["records"]
    need(len(rows) == len(received) == count, "Missing or extra tensor records")
    expected_sequence = list(range(WARMUP, WARMUP + count))
    need([r["sequence"] for r in rows] == [r["sequence"] for r in received] == expected_sequence, "Missing, repeated or reordered sequence")
    base = np.arange(size // 4, dtype=np.float64) if check_values else None
    previous = producer["start_s"]
    latencies = []
    for sent, got in zip(rows, received):
        need(finite(sent["start_s"]) and finite(sent["end_s"])
             and previous <= sent["start_s"] < sent["end_s"] <= producer["end_s"], "Invalid round-trip chronology")
        previous = sent["end_s"]
        expected_crc = zlib.crc32((base + sent["sequence"]).astype(np.float32)) & 0xffffffff if check_values else sent["input_crc32"]
        need(type(expected_crc) is int and 0 <= expected_crc <= 0xffffffff
             and sent["input_crc32"] == sent["ack_crc32"] == got["crc32"] == expected_crc
             and got["verified_elements"] == size // 4, "Payload or validation accounting differs")
        latencies.append((sent["end_s"] - sent["start_s"]) * 1000)
    # The consumer's last bookkeeping can finish just after its ACK was received.
    end = max(producer["end_s"], consumer["end_s"])
    need(rows[-1]["start_s"] <= consumer["end_s"] and producer["end_s"] > producer["start_s"], "Invalid duration")
    duration = end - producer["start_s"]
    for worker in (producer, consumer):
        need(finite(worker["cpu_s"]) and worker["cpu_s"] >= 0
             and type(worker["high_water_rss_bytes"]) is int and worker["high_water_rss_bytes"] > 0, "Invalid process resource record")
    window, samples = run["memory_window"], run["rss_samples"]
    need(finite(window["start_s"]) and finite(window["end_s"])
         and window["start_s"] <= producer["start_s"] < end <= window["end_s"], "Incomplete memory window")
    need(len(samples) >= 2 and samples[0]["end_s"] <= producer["start_s"]
         and samples[-1]["start_s"] >= end, "RSS samples do not bracket traffic")
    previous = window["start_s"]
    for sample in samples:
        need(finite(sample["start_s"]) and finite(sample["end_s"])
             and previous <= sample["start_s"] <= sample["end_s"] <= window["end_s"], "Invalid memory chronology")
        need(all(type(sample[k]) is int and sample[k] > 0 for k in ("producer_rss_bytes", "consumer_rss_bytes")), "Invalid RSS")
        previous = sample["end_s"]
    need(run["cleanup"] == {"exitcodes": [0, 0], "forced_termination": False,
                           "all_workers_exited": True, "control_readers_exited": True,
                           "segment_unlinked": True if mode == "shared" else None}, "Cleanup incomplete")
    sums = [s["producer_rss_bytes"] + s["consumer_rss_bytes"] for s in samples]
    gaps = [samples[0]["start_s"] - window["start_s"], window["end_s"] - samples[-1]["start_s"]]
    gaps += [b["start_s"] - a["start_s"] for a, b in zip(samples, samples[1:])]
    return {"verified_messages": count, "verified_payload_bytes": size * count,
            "duration_s": duration, "messages_per_s": count / duration,
            "payload_mib_per_s": size * count / duration / 1048576,
            "round_trip_ms": distribution(latencies), "producer_cpu_s": producer["cpu_s"],
            "consumer_cpu_s": consumer["cpu_s"], "baseline_paired_rss_bytes": sums[0],
            "peak_paired_rss_bytes": max(sums), "rss_sample_count": len(samples),
            "max_rss_gap_ms": max(gaps) * 1000,
            "max_paired_read_ms": max(s["end_s"] - s["start_s"] for s in samples) * 1000}


def default_count(size):
    return max(64, min(8192, 256 * 1048576 // size))


def resolve(stub, directory):
    need(set(stub) == {"mode", "pipe_receive", "trial", "payload_bytes", "count", "summary", "file", "sha256"}
         and bool(re.fullmatch(r"raw/case-[0-9]+-trial-[0-9]+-(?:pipe|shared)\.json\.gz", stub["file"])), "Invalid raw index")
    path = Path(directory) / stub["file"]
    need(not path.is_symlink() and not path.parent.is_symlink(), "Linked raw evidence")
    data = path.read_bytes()
    need(hashlib.sha256(data).hexdigest() == stub["sha256"], "Raw evidence digest differs")
    run = json.loads(gzip.decompress(data))
    need(all(run[k] == stub[k] for k in ("mode", "pipe_receive", "trial", "payload_bytes", "count")), "Index/raw identity differs")
    need(summarize(run) == stub["summary"], "Summary differs from raw records")
    return run


def verify(report, directory):
    need(report["schema_version"] == 2 and report["source_sha256"] == source_hash()
         and report["scope"] == SCOPE and report["recipe"] == RECIPE, "Stale source or measurement scope")
    need(report["pipe_receive"] in ("into", "bytes"), "Unknown receive API")
    need(type(report["pairs"]) is int and 1 <= report["pairs"] <= 8, "Invalid pair count")
    sizes = [c["payload_bytes"] for c in report["cases"]]
    need(bool(sizes) and sizes == sorted(set(sizes)), "Invalid size grid")
    need(report["count_override"] is None or type(report["count_override"]) is int, "Invalid count policy")
    environment = None
    order = []
    for case in report["cases"]:
        size = case["payload_bytes"]
        count = report["count_override"] if report["count_override"] is not None else default_count(size)
        check_config("pipe", size, count)
        need(case["count"] == count and case["workload_sha256"] == fingerprint({"payload_bytes": size, "count": count, "warmup": WARMUP, "recipe": RECIPE}), "Workload policy differs")
        expected = [(trial, mode) for trial in range(report["pairs"])
                    for mode in (("pipe", "shared") if trial % 2 == 0 else ("shared", "pipe"))]
        need([(s["trial"], s["mode"]) for s in case["runs"]] == expected, "Missing pairs or unbalanced order")
        for stub in case["runs"]:
            need(stub["payload_bytes"] == size and stub["count"] == count, "Unequal work")
            run = resolve(stub, directory)
            need(run["pipe_receive"] == report["pipe_receive"], "Unequal receive API policy")
            environment = run["environment"] if environment is None else environment
            need(run["environment"] == environment, "Unequal software environments")
            order.append({"payload_bytes": size, "trial": run["trial"], "mode": run["mode"]})
    need(report["execution_order"] == order, "Execution order differs")
    need(report["comparisons"] == comparisons(report), "Paired comparison differs from all raw summaries")


def comparisons(report):
    result = []
    for case in report["cases"]:
        ratios = []
        for trial in range(report["pairs"]):
            group = [r for r in case["runs"] if r["trial"] == trial]
            need(len(group) == 2 and {r["mode"] for r in group} == {"pipe", "shared"}, "Missing or repeated comparison pair")
            values = {r["mode"]: r["summary"]["payload_mib_per_s"] for r in group}
            ratios.append(values["shared"] / values["pipe"])
        result.append({"payload_bytes": case["payload_bytes"], "basis": "all_prespecified_pairs",
                       "ratios": ratios, "median": median(ratios), "min": min(ratios), "max": max(ratios),
                       "assessment": "descriptive_single_host_verified_round_trips"})
    return result


def table_rows(report):
    rows = []
    for case in report["cases"]:
        for mode in ("pipe", "shared"):
            stats = [s["summary"] for s in case["runs"] if s["mode"] == mode]
            rows.append([case["payload_bytes"], mode, case["count"],
                         f'{median(s["payload_mib_per_s"] for s in stats):.2f}',
                         f'{median(s["round_trip_ms"]["p50"] for s in stats):.4f}',
                         f'{median(s["round_trip_ms"]["p95"] for s in stats):.4f}',
                         f'{median(s["baseline_paired_rss_bytes"] for s in stats)/1048576:.2f}',
                         f'{max(s["peak_paired_rss_bytes"] for s in stats)/1048576:.2f}',
                         f'{max(s["max_rss_gap_ms"] for s in stats):.3f}'])
    return rows


HEADERS = ["Payload bytes", "Mode", "Messages/trial", "Payload MiB/s", "RTT p50 ms", "RTT p95 ms", "Warm baseline RSS MiB", "Peak paired RSS MiB", "Max RSS gap ms"]


def overview(report):
    lines = ["# Recorded verified IPC round trips", "", f'Pipe receive API: `{report["pipe_receive"]}` (into: recv_bytes_into; bytes: recv_bytes plus target copy).', "", "Actual spawn-process observations. All prespecified pairs are retained. Medians of per-trial throughput/latency/baseline; maximum paired sampled RSS/gap. No universal speedup or unique-physical-memory claim.", "",
             "| " + " | ".join(HEADERS) + " |", "|" + "---|" * len(HEADERS)]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in table_rows(report)]
    lines += ["", "Paired shared/Pipe throughput ratios: median [min, max] over every prespecified pair, not a ratio of table medians or a confidence interval.", "", "| Payload bytes | Paired descriptive ratio |", "|---:|---:|"]
    lines += [f'| {c["payload_bytes"]} | {c["median"]:.3f} [{c["min"]:.3f}, {c["max"]:.3f}] |' for c in comparisons(report)]
    lines += ["", "RTT includes generation, CRC, transport/copy, complete receiver validation and ACK. One payload in flight in both modes. RSS includes warm arrays and measurement buffers and can double-count shared pages. Sampling can miss spikes. These finite traces do not establish maximum sustainable capacity.", "", "- [JSON index](report.json)", "- [Offline HTML](report.html)", ""]
    return "\n".join(lines)


def render(report):
    esc = lambda value: html.escape(str(value))
    rows = "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>" for row in table_rows(report))
    pairs = []
    for case in report["cases"]:
        for trial in range(report["pairs"]):
            group = {s["mode"]: s["summary"] for s in case["runs"] if s["trial"] == trial}
            pairs.append({"payload_bytes": case["payload_bytes"], "trial": trial,
                          "descriptive_shared_over_pipe_throughput": group["shared"]["payload_mib_per_s"] / group["pipe"]["payload_mib_per_s"]})
    details = {"host": report["host"], "source_sha256": report["source_sha256"],
               "pipe_receive": report["pipe_receive"], "comparisons": report["comparisons"],
               "all_pair_descriptive_ratios": pairs, "cases": report["cases"]}
    links = "".join(f'<li><a href="{esc(s["file"])}">{esc(s["file"])}</a> SHA-256 {esc(s["sha256"])}</li>' for c in report["cases"] for s in c["runs"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tiny IPC Lab measurements</title><style>body{{font:16px/1.6 system-ui;max-width:1200px;margin:36px auto;padding:0 20px;background:#f5f7fa;color:#162638}}section{{background:white;padding:22px;margin:18px 0;border:1px solid #dce4ec;border-radius:10px}}table{{border-collapse:collapse;white-space:nowrap}}td,th{{padding:9px;border-bottom:1px solid #ddd;text-align:right}}.scroll{{overflow:auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style>
<h1>Tiny IPC Lab</h1><p>{esc(report["generated_utc"])} · {report["pairs"]} alternating fresh-process pairs per size · float32 tensors · Pipe receive API: {esc(report["pipe_receive"])}</p>
<section><h2>Verified end-to-end round trips</h2><p>Median per-trial payload throughput, RTT percentiles and warm baseline RSS; maximum paired sampled RSS and sampling gap. Every message is fully checked. One acknowledged payload is in flight in both modes. Shared mode includes a producer-to-shared-buffer copy; Pipe uses the declared public receive API and a preallocated target. These are descriptive observations, not pure-transport or universal speedup claims.</p><div class="scroll"><table><tr>{''.join(f'<th>{esc(h)}</th>' for h in HEADERS)}</tr>{rows}</table></div></section>
<section><h2>All-pair descriptive throughput ratios</h2><p>Shared / Pipe, median [min, max] across every prespecified pair. Not ratios of table medians, confidence intervals or universal effects.</p><table><tr><th>Payload bytes</th><th>Median</th><th>Min</th><th>Max</th></tr>{''.join('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [c['payload_bytes'],f"{c['median']:.3f}",f"{c['min']:.3f}",f"{c['max']:.3f}"])+'</tr>' for c in comparisons(report))}</table></section>
<section><h2>Scope and limitations</h2><ul>{''.join(f'<li>{esc(v)}</li>' for v in report["scope"])}</ul></section>
<section><h2>Complete evidence</h2><p><a href="report.json">JSON index</a> · Every message, worker outcome and RSS sample is retained in the lossless files below. SHA-256 checks and deterministic rendering reconcile the files with this page.</p><ul>{links}</ul><details><summary>All paired observations, summaries and provenance</summary><pre>{esc(json.dumps(details,indent=2))}</pre></details></section></html>'''


def write_report(report, directory):
    directory = Path(directory)
    verify(report, directory)
    (directory / "report.json").write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
    (directory / "report.html").write_text(render(report))
    (directory / "README.md").write_text(overview(report))
