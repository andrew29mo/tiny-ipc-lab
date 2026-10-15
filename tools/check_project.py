"""Recompute every retained value/checksum/metric and check canonical reports."""

import argparse
import gzip
import json
from pathlib import Path
import re
import subprocess

from tiny_ipc_lab.cli import DEFAULT_SIZES
from tiny_ipc_lab.report import verify, render, overview

ROOT = Path(__file__).resolve().parents[1]


def check(directory, smoke=False):
    directory = Path(directory)
    report = json.loads((directory / "report.json").read_text())
    verify(report, directory)
    if not smoke and (report["pairs"] != 4 or report["count_override"] is not None
                      or [c["payload_bytes"] for c in report["cases"]] != DEFAULT_SIZES):
        raise ValueError("Recorded experiment is not the fixed full grid")
    if ((directory / "report.html").read_text() != render(report)
            or (directory / "README.md").read_text() != overview(report)
            or (directory / "report.json").read_text() != json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n"):
        raise ValueError("JSON/HTML/README differs from retained evidence")
    print("Verified every sequence/value CRC, timing/RSS statistic, clean exit, fair workload and canonical JSON/HTML/README.")


def publication():
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    private = re.compile(rb"/(?:Users|home)/[A-Za-z0-9_.-]+/|[A-Za-z]:\\Users\\")
    secret = re.compile(rb"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
    banned = {"AGENTS.md", ".env", ".venv", ".codex", ".agents", "__pycache__", ".DS_Store", "codex-notes", "backups"}
    for name in filter(None, names):
        path = ROOT / name
        if path.is_symlink() or any(part in banned or part.startswith(".env.") for part in path.parts):
            raise ValueError("Private or linked file: " + name)
        data = path.read_bytes()
        if name.endswith(".gz"):
            if not re.fullmatch(r"results/macos-arm64(?:-pipe-bytes)?/raw/case-[0-9]+-trial-[0-9]+-(?:pipe|shared)\.json\.gz", name):
                raise ValueError("Unexpected compressed file")
            data = gzip.decompress(data)
        if b"\0" in data or private.search(data) or secret.search(data):
            raise ValueError("Targeted private/generated content pattern: " + name)
        text = data.decode("utf-8")
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" not in target and not target.startswith("#") and not (path.parent / target.split("#")[0]).exists():
                    raise ValueError("Broken local link in " + name)
    print("Tracked files: no targeted personal/secret/generated patterns or broken Markdown links.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "results/macos-arm64")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    check(args.directory, args.smoke)
    publication()
