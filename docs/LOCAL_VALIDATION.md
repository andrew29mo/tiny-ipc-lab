# Local macOS / Linux validation

From a macOS host with Python 3.12 and a Docker CLI installed:

```sh
./tools/validate-local
```

The existing project `.venv` is preferred as the launcher. Otherwise the launcher
uses `python3.12`. The command installs checksum-pinned official Colima and Lima
binaries under ignored `results/local/toolchain`. It reuses the Docker Desktop CLI
when available; Docker Desktop does not need to run. No Homebrew or paid service
is required. First setup needs internet access to fetch tools, the pinned Python
base image, OS packages and pinned Python dependencies.

The dedicated Colima home is `~/.colima-tipc-<project-path-hash>` to stay below Unix
socket path limits. It uses Apple's Virtualization.framework with the host's
architecture, 4 CPUs, 6 GiB VM memory and a 40 GiB data disk. No host folders or SSH
agent are shared, no Rosetta/binfmt emulation is requested, and no global Docker
context is activated. The actual container settings are inspected and recorded. The profile is stopped before native measurement and after
Linux validation. Tool caches and the stopped VM remain for subsequent runs.

A credential-free snapshot copies **Git-tracked working files only** and bundles
reachable HEAD history for historical-evidence checks. Stage new workflow files
before running; untracked files are deliberately excluded. It does not copy the
host Git configuration, remotes, credentials or untracked personal files.
Both environments use the same snapshot and pinned Python dependencies.

Execution is sequential: a fresh native Python environment runs the formal tests,
optimized-Python tests, ten behavioral source faults, all historical evidence and
RSS/audit checks, both legacy Pipe receive APIs, then the full pool benchmark and
its raw-evidence/report checker. Linux repeats those commands in a non-root
container with no network, no added capabilities, no host bind mount, 4 CPUs,
4 GiB memory and 256 MiB shared memory. The default benchmark has six tensor sizes
plus two slow-consumer cases, five rotating blocks and five profiles (200 trials).

```sh
# Short actual IPC measurement; same formal tests and archived-evidence checks.
./tools/validate-local --benchmark smoke
# Independently check a completed run's logs, raw hashes and shared source.
.venv/bin/python tools/check_validation.py results/local/validation/<run-id>
```

Evidence is retained under ignored `results/local/validation/<UTC-run-id>`:
`combined.json`, `snapshot.json`, `linux-runtime.json`, per-environment
`validation.json`, full step logs and separate `benchmark/report.json`,
`benchmark/report.html`, `benchmark/README.md` and raw records. Nonzero exits,
timeouts, missing test results, missing steps, changed snapshots and cleanup
failures prevent a passing result. A failing container's evidence is copied before
removal; if copying fails, the stopped container is retained for recovery.

Native and VM throughput/RSS are separate observations, **not** a controlled
cross-environment speedup. VM scheduling, the container limit, kernel and allocator
can change both. Worker RSS excludes the VM and Docker daemon overhead and can double-count shared mappings. ARM64 Linux does not establish x86_64 compatibility. Local tests
do not create a GitHub-hosted CI success or validate GitHub runner configuration.
CI uses the same suite with smoke measurement; no absolute performance threshold
is a correctness gate. Raw local setup/test logs can contain host paths and are
not published automatically. Review and sanitize records before uploading.

The Python image is pinned by digest, tool downloads by SHA-256, and Python
packages by version. OS package repositories are not frozen; the recorded image
ID identifies the image actually tested, without promising byte-identical rebuilds.
No image is pushed to a registry and no repository visibility is changed.
