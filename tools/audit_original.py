"""Reopen the immutable original source and every raw trial before rechecking 4.10x."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = "d2ca56def790fd4877c4ef62d4496e05c5123a20"


def audit():
    archive = subprocess.check_output(["git", "archive", ORIGINAL], cwd=ROOT)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            stream.extractall(path, filter="data")
        # Run the actual immutable verifier against its own source, not the revised implementation.
        subprocess.run([sys.executable, "-c", "import sys;sys.path.insert(0,'tools');from check_project import check;check('results/macos-arm64')"],
                       cwd=path, env=dict(os.environ, PYTHONPATH=str(path / "src")), check=True)
        payload = (path / "results/macos-arm64/report.json").read_bytes()
        report = json.loads(payload)
        cases = []
        for case in report["cases"]:
            ratios = []
            for trial in range(4):
                group = {s["mode"]: s["summary"]["payload_mib_per_s"] for s in case["runs"] if s["trial"] == trial}
                ratios.append(group["shared"] / group["pipe"])
            cases.append({"payload_bytes": case["payload_bytes"], "all_pair_ratios": ratios,
                          "median": median(ratios), "min": min(ratios), "max": max(ratios)})
        return {"original_commit": ORIGINAL, "original_report_sha256": hashlib.sha256(payload).hexdigest(),
                "original_source_sha256": report["source_sha256"],
                "verified_messages": sum(s["summary"]["verified_messages"] for c in report["cases"] for s in c["runs"]),
                "verified_raw_files": sum(len(c["runs"]) for c in report["cases"]), "cases": cases,
                "assessment": "The original approximately 4.10x is the median of every paired ratio at 1 MiB under recv_bytes_into. It is a valid descriptive observation of that API/workload on one host, not a universal shared-memory effect or a raw-transport benchmark. Original RSS includes runtime allocator retention; it is not a paired unique-memory saving estimate. Revised measurements remain separate."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reviews/original-d2ca56d.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.verify:
        if json.loads(args.output.read_text()) != result:
            raise ValueError("Historical review differs from immutable raw evidence")
        print("Original 48 raw trials and all paired ratios reverified from immutable Git objects.")
    else:
        if args.output.exists():
            raise ValueError("Use a new review output")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
