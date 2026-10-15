# Pre-publication review — 2026-10-15

Reviewed main commit `7c8ef16fd95c196d5b91b13fc0154b33a220a566`, with production
source SHA-256 `5cc142fee7e35f3f5a9f109c8631e3e47257cf1bbafe85707b693958c4ef2b3d`.
No implementation or performance-calculation mismatch requiring a code change
was found. This review adds documentation/evidence; it does not change production
code, dependencies, licenses, history, collaborators or repository visibility.

## Code, tests and retained measurements

The clean main snapshot completed the same 17-step local suite on native macOS
ARM64 and Colima Linux ARM64. Each environment passed 59 normal tests, 59
optimized-Python tests and all ten named behavioral source faults. Import paths,
production file hashes, executed commands/test IDs and Python/dependency versions
were checked. The fresh smoke used 40 actual trials / 680 exchanges per
environment; it is not a new full performance study or a performance threshold.
Actual zero container exit, no OOM/error, evidence export, container removal and VM
shutdown were verified. See [the receipt and scope](audit.json) and sanitized logs
under `logs/`. Full original logs, canonical JSON/HTML and raw smoke records remain
locally under its recorded run ID.

All five retained benchmark directories, immutable original/pool audits and RSS
diagnostic evidence were verified again. The primary README table is generated
and checked against every primary block. The historical schema-2 1 MiB paired
ratios independently rebuild to 4.411 and 4.186; corresponding separate 4 MiB Pipe
RSS maxima rebuild to 358.52 and 107.28 MiB. Original 4.101, 2.309 and 8.399 ratios
remain tied to their producing revisions. These are descriptive observations,
not universal speedups, pure transport bandwidth or physical-memory savings.

Both committed local-record sets (46-test schema 1 and 59-test schema 2) were
compared with their original local files: receipts, original/sanitized log hashes,
every derived observation/comparison and every measurement table matched. Each
of their four full environment runs retains 200 trials / 654,450 exchanges.
Historical schema-1 records do not acquire schema-2 cleanup/import guarantees.
The previous actual timeout-cleanup probe still refers to the current helper
bytes; no remeasurement or source identity was relabelled.

Native and VM observations remain separate. RSS sums two sampled worker values,
can double-count shared pages, excludes controller/resource tracker and VM/daemon
overhead, and may miss peaks. Linux ARM64 is not x86_64 or GitHub-hosted runner
validation. Public readers can recompute tables/ratios from committed derived
observations and run fresh experiments, but cannot independently regenerate the
original local raw records from the compact receipts alone. The primary native
run and older benchmark directories do include their raw files in Git.

## Publication surface and privacy

The review fetched the five unmerged Dependabot branches without merging them.
All reachable objects across main and those branches were scanned: 990 objects,
898 blobs including 744 expanded gzip records, and 11 commit objects. No targeted
home-path, credential/private-key, excluded-file, generated-package-metadata or
unexpected binary pattern was found. Commit email identities were GitHub noreply
or known tool identities. The [receipt](audit.json) records reviewed refs and
scanner scope. This is a heuristic review, not a comprehensive secret detector.

Tracked Markdown links and publication hygiene passed. No personal guidance,
credentials, Docker configuration/socket, VM disk, downloaded runtime binary,
virtual environment or full setup log is committed. Published test logs have
private home/runtime/temporary prefixes redacted. GitHub had no release assets or
Actions artifacts and only the owner as collaborator. The repository remains
Private; no branch/tag/history rewrite or new access grant was performed.

## License state at the reviewed revision

At reviewed revision `7c8ef16`, original contributions had **no selected project
license**, LICENSE file or package license declaration. The owner subsequently
adopted [MIT](../../LICENSE); the current [third-party notice](../../THIRD_PARTY_NOTICES.md)
describes that grant. The historical `audit.json` retains its original
`not-selected` field and is not rewritten as if MIT existed during that review.

The workload is generated synthetic tensors, with no external model/dataset or
vendored dependency binaries. Upstream pinned sources confirm
[NumPy's BSD terms](https://github.com/numpy/numpy/blob/v1.26.4/LICENSE.txt),
[psutil BSD-3-Clause](https://github.com/giampaolo/psutil/blob/release-7.0.0/LICENSE),
[Colima MIT](https://github.com/abiosoft/colima/blob/v0.10.3/LICENSE) and
[Lima Apache-2.0](https://github.com/lima-vm/lima/blob/v2.2.1/LICENSE).
Installed/downloaded components retain their own notices; no image is published.

GitHub-hosted CI was previously prevented from starting by account
payments/spending-limit restrictions. Local verification is the recorded
alternative, not a claim that hosted CI passed. SIGKILL, power loss and a broken
hypervisor/daemon remain outside complete-cleanup guarantees.
