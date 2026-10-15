"""Five-profile blocked comparison, including equal-window Pipe sensitivity control."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import html
import json
from pathlib import Path
import platform
from statistics import median
import subprocess
import sys

import psutil

from .experiment import fingerprint, run_trial, source_hash, TrialFailure
from .protocol import RECIPE, WARMUP, check_config
from .report import default_count, distribution, need, summarize
from .pool import check_capacity

PROFILES = ("pipe", "shared", "pool_1", "pool_n", "window_pipe")
LIMITS = [
    "Identical float32 recipe, sequence order, warmup count, message count and consumer delay within each case; full exact-value validation plus CRC and ACK in every profile. No drops or outlier exclusions.",
    "pipe/shared are the existing stop-and-wait protocols with one payload in flight. shared copies a staging array into its slot. pool_1/pool_n fill loaned shared slots in place. window_pipe fills local loaned slots in place and uses the same publication/release protocol and capacity as pool_n. All Pipe payloads use recv_bytes plus a copy to a preallocated consumer target.",
    "Pool and windowed Pipe carry additional slot/generation metadata. Pool_n versus legacy baselines includes changes in copy count, window and protocol. The equal-window Pipe control separates window size from transport more closely, but receiver allocation/copy behavior still differs. No end-to-end zero-copy claim: base/reference generation, validation and CRC remain included.",
    "Closed-loop, finite SPSC saturation traces, not a shared arrival schedule, inference service or production capacity estimate. Every block rotates profile order; five blocks balance all five positions. Partial subsets are never called a full grid.",
    "Message completion latency starts before loan acquisition or legacy generation and ends when its valid ACK is processed by the producer. Pool latency includes capacity waiting and ACK collection scheduling. Capacity-reclaim counts mean no locally free slot, even if an ACK is already queued; reclaim time includes ACK processing, not only consumer waiting. It is not transport RTT or consumer service time. Drain of the final partial window is included in throughput.",
    "Workers are fresh per trial; eight transfers warm protocol state before measurement, fully drained before start. Artificial consumer delay is applied only to measured messages after validation and before ACK in all profiles; requested sleep is not exact service time.",
    "RSS samples include two worker runtimes, arrays, touched pool pages, records and result serialization; baseline is after warmup. Shared pages may be counted twice. Sequential 5 ms requested samples can miss peaks; actual gaps are retained. Controller/resource tracker are excluded. Pool payload allocation is bounded; per-message evidence records still grow with the finite message count. RSS is not unique physical memory or total deployment size.",
    "Single host, fixed case order, uncontrolled CPU/cache/thermals and short trials. Ratios are medians of all within-block ratios with observed min/max, not confidence intervals or universal effects. Controller-managed worker-crash cleanup is tested; controller kill and power loss are outside the guarantee.",
]


def profile_config(profile, capacity):
    if profile == "pool_1":
        return "pool", 1
    if profile == "pool_n":
        return "pool", capacity
    return profile, capacity if profile == "window_pipe" else 1


def block_order(block):
    i = block % len(PROFILES)
    return list(PROFILES[i:] + PROFILES[:i])


def ratios(report):
    comparisons = (("pool_1", "shared"), ("pool_n", "shared"), ("pool_n", "pipe"), ("pool_n", "window_pipe"))
    result = []
    for case in report["cases"]:
        for numerator, denominator in comparisons:
            values = []
            for block in range(report["blocks"]):
                group = {r["profile"]: r["summary"]["payload_mib_per_s"] for r in case["runs"] if r["block"] == block}
                need(len(group) == len(PROFILES), "Incomplete comparison block")
                values.append(group[numerator] / group[denominator])
            result.append({"case": case["id"], "numerator": numerator, "denominator": denominator,
                           "all_block_ratios": values, "median": median(values), "min": min(values), "max": max(values)})
    return result


def workloads(sizes, *, smoke=False):
    cases = [{"id": f"normal-{size}", "payload_bytes": size, "count": 17 if smoke else default_count(size), "consumer_delay_s": 0.} for size in sizes]
    cases += [{"id": f"slow-{size}", "payload_bytes": size, "count": 17 if smoke else 129, "consumer_delay_s": .001}
              for size in (sizes if smoke else [16384, 1048576])]
    return cases


def benchmark(directory, sizes=(64, 1024, 16384, 262144, 1048576, 4194304), blocks=5, capacity=4, *, smoke=False):
    check_capacity(capacity)
    if capacity == 1 or type(blocks) is not int or not 1 <= blocks <= 10 or list(sizes) != sorted(set(sizes)) or not sizes:
        raise ValueError("Require capacity 2..16, 1..10 blocks and sorted unique sizes")
    cases = workloads(sizes, smoke=smoke)
    for c in cases:
        check_config("pipe", c["payload_bytes"], c["count"])
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Use a new output directory")
    (directory / "raw").mkdir(parents=True)
    cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip() if sys.platform == "darwin" else None
    report = {"schema_version": 3, "source_sha256": source_hash(), "generated_utc": datetime.now(timezone.utc).isoformat(),
              "recipe": RECIPE, "scope": LIMITS, "profiles": list(PROFILES), "blocks": blocks,
              "pool_capacity": capacity, "smoke": smoke, "pipe_receive": "bytes", "execution_order": [], "cases": [],
              "host": {"os": platform.system(), "os_release": platform.release(), "machine": platform.machine(),
                       "cpu_model": cpu, "logical_cpus": psutil.cpu_count(), "python": platform.python_version()}}
    for i, workload in enumerate(cases):
        case = dict(workload, workload_sha256=fingerprint(dict(workload, warmup=WARMUP, recipe=RECIPE)), runs=[])
        report["cases"].append(case)
        for block in range(blocks):
            for profile in block_order(block):
                mode, slots = profile_config(profile, capacity)
                print(f"{case['id']} block {block+1}/{blocks}: {profile}", flush=True)
                (directory / "partial.json").write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
                try:
                    run = run_trial(mode, case["payload_bytes"], case["count"], pipe_receive="bytes", capacity=slots,
                                    consumer_delay_s=case["consumer_delay_s"], timeout=60.)
                except TrialFailure as error:
                    (directory / "failure.json").write_text(json.dumps({"case": case["id"], "block": block, "profile": profile,
                                                                        "cleanup": error.cleanup, "error_type": type(error).__name__}) + "\n")
                    raise
                run.update(profile=profile, block=block)
                summary = summarize(run, check_values=False)
                name = f"raw/case-{i}-block-{block}-{profile}.json.gz"
                data = gzip.compress(json.dumps(run, separators=(",", ":"), allow_nan=False).encode(), mtime=0)
                (directory / name).write_bytes(data)
                case["runs"].append({"profile": profile, "block": block, "file": name,
                                     "sha256": hashlib.sha256(data).hexdigest(), "summary": summary})
                report["execution_order"].append({"case": case["id"], "block": block, "profile": profile})
    report["comparisons"] = ratios(report)
    write_report(report, directory)
    (directory / "partial.json").unlink()
    return report


def verify(report, directory):
    need(report["schema_version"] == 3 and report["source_sha256"] == source_hash() and report["scope"] == LIMITS
         and report["recipe"] == RECIPE and report["profiles"] == list(PROFILES) and report["pipe_receive"] == "bytes", "Stale pool experiment source/scope")
    check_capacity(report["pool_capacity"])
    need(report["pool_capacity"] >= 2 and type(report["blocks"]) is int and 1 <= report["blocks"] <= 10
         and type(report["smoke"]) is bool, "Invalid comparison policy")
    sizes = [c["payload_bytes"] for c in report["cases"] if c["consumer_delay_s"] == 0.]
    need(sizes and sizes == sorted(set(sizes)), "Invalid sizes")
    expected_cases = workloads(sizes, smoke=report["smoke"])
    need(len(report["cases"]) == len(expected_cases), "Missing cases")
    order, environment = [], None
    for i, (case, expected) in enumerate(zip(report["cases"], expected_cases)):
        need(all(case[k] == v for k, v in expected.items()) and case["workload_sha256"] == fingerprint(dict(expected, warmup=WARMUP, recipe=RECIPE)), "Unequal workload")
        identities = [(b, p) for b in range(report["blocks"]) for p in block_order(b)]
        need([(s["block"], s["profile"]) for s in case["runs"]] == identities, "Missing/reordered blocks")
        for stub in case["runs"]:
            b, p = stub["block"], stub["profile"]
            need(stub["file"] == f"raw/case-{i}-block-{b}-{p}.json.gz", "Invalid evidence path")
            path = Path(directory) / stub["file"]
            need(not path.is_symlink() and not path.parent.is_symlink(), "Linked evidence")
            data = path.read_bytes()
            need(hashlib.sha256(data).hexdigest() == stub["sha256"], "Digest differs")
            run = json.loads(gzip.decompress(data))
            mode, capacity = profile_config(p, report["pool_capacity"])
            need(run["mode"] == mode and run["capacity"] == capacity and run["profile"] == p and run["block"] == b
                 and run["pipe_receive"] == "bytes" and all(run[k] == case[k] for k in ("payload_bytes", "count", "consumer_delay_s")), "Raw workload/profile differs")
            environment = run["environment"] if environment is None else environment
            need(run["environment"] == environment, "Unequal runtime")
            need(summarize(run) == stub["summary"], "Summary differs from records")
            order.append({"case": case["id"], "block": b, "profile": p})
    need(order == report["execution_order"] and report["comparisons"] == ratios(report), "Comparison or execution order differs")


def overview(report):
    lines = ["# Bounded IPC pool comparison", "", "Five-profile verified exchanges; all blocks retained. Completion latency includes loan waiting and ACK collection. RSS is sampled two-worker RSS, not unique physical RAM.", "",
             "| Case | Profile | Count | MiB/s median | Completion p50 ms | Completion p95 ms | Baseline RSS MiB median | Peak RSS MiB max | Slots max | ACK-reclaim events median | Reclaim ms total median |", "|" + "---|" * 11]
    for case in report["cases"]:
        for profile in PROFILES:
            stats = [r["summary"] for r in case["runs"] if r["profile"] == profile]
            values = [case["id"], profile, case["count"], f'{median(s["payload_mib_per_s"] for s in stats):.2f}',
                      f'{median(s["round_trip_ms"]["p50"] for s in stats):.4f}', f'{median(s["round_trip_ms"]["p95"] for s in stats):.4f}',
                      f'{median(s["baseline_paired_rss_bytes"] for s in stats)/1048576:.2f}', f'{max(s["peak_paired_rss_bytes"] for s in stats)/1048576:.2f}',
                      max(s.get("peak_owned_slots", 1) for s in stats), median(s.get("capacity_wait_count", 0) for s in stats), f'{median(s.get("capacity_wait_s", 0.) for s in stats)*1000:.3f}']
            lines.append("| " + " | ".join(map(str, values)) + " |")
    lines += ["", "All within-block throughput ratios: median [observed min, max], not a confidence interval.", "", "| Case | Numerator / denominator | Ratio |", "|---|---|---|"]
    lines += [f'| {r["case"]} | {r["numerator"]} / {r["denominator"]} | {r["median"]:.3f} [{r["min"]:.3f}, {r["max"]:.3f}] |' for r in ratios(report)]
    lines += ["", *["- " + item for item in LIMITS], "", "[JSON evidence](report.json) · [Offline HTML](report.html)", ""]
    return "\n".join(lines)


def render(report):
    esc = html.escape
    # Tables use the same canonical cell text as the Markdown report.
    sections, table, rows = [], False, []
    for line in overview(report).splitlines():
        if line.startswith("|"):
            if set(line) <= set("|- "):
                continue
            tag = "td" if table else "th"
            rows.append("<tr>" + "".join(f"<{tag}>{esc(c.strip())}</{tag}>" for c in line.strip("|").split("|")) + "</tr>")
            table = True
        else:
            if table:
                sections.append('<div class="scroll"><table>' + "".join(rows) + "</table></div>")
                table, rows = False, []
            if line and not line.startswith("[JSON"):
                sections.append(f'<p>{esc(line.lstrip("# "))}</p>')
    links = "".join(f'<li><a href="{esc(s["file"])}">{esc(s["file"])}</a> {s["sha256"]}</li>' for c in report["cases"] for s in c["runs"])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bounded IPC pool evidence</title><style>body{font:16px/1.6 system-ui;max-width:1250px;margin:32px auto;padding:20px;color:#14283b}table{border-collapse:collapse;white-space:nowrap}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:right}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Bounded IPC pool comparison</h1>' + ''.join(sections) + '<h2>Raw evidence</h2><a href="report.json">JSON index</a><ul>' + links + '</ul><details><summary>Host, all observations and provenance</summary><pre>' + esc(json.dumps(report, indent=2, allow_nan=False)) + '</pre></details></html>'


def write_report(report, directory):
    verify(report, directory)
    directory = Path(directory)
    for name, text in (("report.json", json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n"), ("README.md", overview(report)), ("report.html", render(report))):
        temporary = directory / (name + ".tmp")
        temporary.write_text(text)
        temporary.replace(directory / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/local/pool"))
    parser.add_argument("--sizes", type=int, nargs="+", default=[64, 1024, 16384, 262144, 1048576, 4194304])
    parser.add_argument("--blocks", type=int, default=5)
    parser.add_argument("--capacity", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    benchmark(args.output, args.sizes, args.blocks, args.capacity, smoke=args.smoke)


if __name__ == "__main__":
    main()
