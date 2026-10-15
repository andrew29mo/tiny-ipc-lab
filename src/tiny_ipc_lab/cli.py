import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import psutil

from .experiment import fingerprint, run_trial, source_hash, TrialFailure
from .protocol import RECIPE, WARMUP, check_config
from .report import SCOPE, default_count, summarize, write_report

DEFAULT_SIZES = [64, 1024, 16384, 262144, 1048576, 4194304]


def benchmark(directory, sizes=DEFAULT_SIZES, pairs=4, count=None):
    directory = Path(directory)
    if not sizes or sizes != sorted(set(sizes)) or type(pairs) is not int or not 1 <= pairs <= 8:
        raise ValueError("Use sorted unique sizes and 1..8 pairs")
    for size in sizes:
        check_config("pipe", size, default_count(size) if count is None else count)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Use a new output directory; existing measurements are never overwritten")
    (directory / "raw").mkdir(parents=True)
    cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip() if sys.platform == "darwin" else None
    report = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
              "source_sha256": source_hash(), "recipe": RECIPE, "scope": SCOPE,
              "pairs": pairs, "count_override": count, "execution_order": [], "cases": [],
              "host": {"os": platform.system(), "os_release": platform.release(), "machine": platform.machine(),
                       "cpu_model": cpu, "logical_cpus": psutil.cpu_count(), "python": platform.python_version()}}
    for index, size in enumerate(sizes):
        messages = default_count(size) if count is None else count
        case = {"payload_bytes": size, "count": messages,
                "workload_sha256": fingerprint({"payload_bytes": size, "count": messages, "warmup": WARMUP, "recipe": RECIPE}), "runs": []}
        report["cases"].append(case)
        for trial in range(pairs):
            for mode in (("pipe", "shared") if trial % 2 == 0 else ("shared", "pipe")):
                print(f"Measuring {size} bytes, {messages} messages, pair {trial+1}, {mode}", flush=True)
                (directory / "partial.json").write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
                try:
                    run = run_trial(mode, size, messages)
                except TrialFailure as error:
                    (directory / "failure.json").write_text(json.dumps({"mode": mode, "trial": trial,
                        "payload_bytes": size, "error_type": type(error).__name__, "cleanup": error.cleanup}, indent=2) + "\n")
                    raise
                run["trial"] = trial
                stats = summarize(run, check_values=False)  # Formal final verifier regenerates every CRC independently.
                filename = f"raw/case-{index}-trial-{trial}-{mode}.json.gz"
                data = gzip.compress(json.dumps(run, separators=(",", ":"), allow_nan=False).encode(), mtime=0)
                (directory / filename).write_bytes(data)
                case["runs"].append({"mode": mode, "trial": trial, "payload_bytes": size, "count": messages,
                                     "summary": stats, "file": filename, "sha256": hashlib.sha256(data).hexdigest()})
                report["execution_order"].append({"payload_bytes": size, "trial": trial, "mode": mode})
                (directory / "partial.json").write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
    write_report(report, directory)
    (directory / "partial.json").unlink()
    return report


def main():
    parser = argparse.ArgumentParser(description="Verified Pipe/shared-memory round trips; no universal speedup assumed")
    parser.add_argument("--output", type=Path, default=Path("results/local/experiment"))
    parser.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES)
    parser.add_argument("--pairs", type=int, default=4)
    parser.add_argument("--count", type=int, help="Override the default size-dependent message budget; marked in the report")
    args = parser.parse_args()
    benchmark(args.output, args.sizes, args.pairs, args.count)


if __name__ == "__main__":
    main()
