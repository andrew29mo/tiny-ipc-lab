# Local validation review

The original IPC implementation and source hash remain unchanged. Review found
workflow defects, rather than evidence that the previous successful data exchange
trials were miscomputed. Historical schema-1 receipts are preserved as historical
records; they do not establish the new schema-2 failure/cleanup invariants.

## Corrected findings

- **P1: escaped descendants on timeout/cancellation.** The original committed
  `execute` killed only its process group. A child opening another session could
  survive. The original implementation was executed with a bounded fixture:
  [counterexample](original-timeout-counterexample.json) records a real surviving
  descendant after `timeout`; it was then manually terminated. The new actual
  process tests cover another-session descendants ignoring TERM, and SIGTERM of
  the driver. Cleanup captures live descendant identities before parent exit,
  escalates boundedly, reaps its direct child and fails if cleanup cannot be
  verified. Deliberate earlier daemonization/reparenting remains outside scope.
- **P1: stale `passed` after final verification failed.** The old orchestrator
  persisted `passed` before calling the final verifier. The new finalizer writes
  `checking`, verifies, creates the labelled report, and only then writes `passed`;
  exceptions persist `integrity-failed`. An actual finalizer regression test uses
  missing evidence to prove that a prior pass claim is overwritten.
- **P2: unchecked shutdown/removal and unbounded cleanup.** Initial VM shutdown,
  container exit/OOM state, removal and final VM state are now checked. All runtime
  and cleanup commands have deadlines; failed operations are retained. Failed
  removal/export and stop paths are exercised through the production helper with
  simulated CLI failures, alongside real failing/timed-out subprocess commands.
  Unique per-run Docker labels restrict cleanup; an export failure retains the
  owned container for recovery. A per-project file lock rejects concurrent runs.
- **P2: incomplete source and evidence binding.** Both environments now bind
  imported production modules to snapshot paths and file hashes, retain actual
  commands and test IDs, require matching Python/dependency versions and native
  architecture, verify the full named mutation matrix, and independently
  regenerate measurement data / canonical reports during final verification.
  Installed Lima files are checked against the verified archive, rather than only
  trusting a version string. Counterexamples reject outside-snapshot imports,
  incomplete steps, duplicate fault lines, changed logs and hash-consistent but
  semantically invalid measurement data.

## Observed verification

Both environments used one tracked-file snapshot of the reviewed code:
59 normal tests, 59 optimized-Python tests, all ten named source faults, all
historical evidence/audit/RSS checks, both legacy Pipe receive APIs and full
200-trial / 654,450-exchange measurements **per environment**. Executed verbose
test IDs matched exactly. The actual container had four CPUs, 4 GiB memory,
256 MiB shared memory, no network, no capabilities, non-root user and no mounts.
Container exit was zero, with no OOM/error, and actual removal / VM stop passed.
The [receipt](receipt.json) binds source files, runtime and retained logs; full raw
JSON/HTML and original logs remain locally under its run ID.

A separate [actual cleanup probe](cleanup-probe.json) timed out an attached Docker
client while its tagged container intentionally ignored TERM and remained alive.
The production cleanup helper killed that container, exported and checked the
known JSON marker, removed the container and stopped the VM. This probe is not
included in performance/RSS trials. Its [fixture](cleanup_probe.py) can be run from
the repository root after a full validation:

```sh
.venv/bin/python reviews/local-validation-audit-20261015/cleanup_probe.py results/local/validation/<run-id>
```

## Presentation, privacy and limits

The new local `validation.html` explicitly labels native macOS and Colima Linux,
with separate complete workload tables. Throughput, ACK-observed latency and
sampled worker RSS are copied from verified observations. Worker RSS is a sampled
sum, can double-count shared pages, and excludes VM/daemon overhead; whole-VM host
memory was not measured. VM/native differences are not a controlled causal
comparison. No x86_64 or GitHub-hosted runner validation is claimed.

Published logs have home/runtime/temporary prefixes redacted, with original and
sanitized hashes recorded separately. Setup/inspection logs, raw full records,
credentials, runtime binaries, VM disks, Docker configuration and personal guidance
are not uploaded. Source receipts identify the tested snapshot; subsequently
added review receipts/documentation are not claimed to have existed during it.
Hashes are consistency evidence, not signed attestations. SIGKILL, power loss and
a broken daemon/hypervisor cannot guarantee full cleanup.
