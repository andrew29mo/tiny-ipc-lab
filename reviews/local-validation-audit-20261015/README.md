# Reviewed macOS / Linux validation record

Both environments completed the same 17-step suite from one Git-tracked source
snapshot: 59 normal and 59 optimized-Python tests each, ten detected behavioral
source faults each, historical evidence / RSS / audit verification, both legacy
Pipe APIs, and a full 200-trial / 654,450-exchange pool measurement each.

- [Receipt, source file hashes and actual container configuration](receipt.json)
- [Native macOS measurements](native-measurements.md)
- [Linux VM measurements](linux-measurements.md)
- [Native derived observations](native-measurement-summary.json)
- [Linux derived observations](linux-measurement-summary.json)

The receipt identifies the actual tested snapshot, including staged workflow
changes on its recorded base commit. It does not claim that subsequently added
receipts/documentation were already present during execution. Log files under
`logs/` have host home/temporary prefixes redacted; original and sanitized hashes
are separate. Full original logs, raw exchanges and canonical JSON/HTML remain in
ignored local storage, not in this compact record. Schema-1 records are retained historically; this run uses schema 2 and the reviewed failure/cleanup checks.

Native and virtualized performance/RSS are separate observations. These runs do
not establish x86_64 compatibility, whole-VM memory consumption, controlled
cross-environment speedups or a GitHub-hosted CI success. No repository visibility
or original-project license change was made. See AUDIT.md for the corrected gaps and remaining limits. See the local-validation guide in the
main repository for reproduction and integrity checks.

- [Review findings, counterexamples and limits](AUDIT.md)
- [Actual live-container timeout and cleanup probe](cleanup-probe.json)

The new local run also contains a labelled `validation.html` entry point. Original
setup/inspection logs and full raw JSON/HTML remain local. Published cleanup probe
logs are separate from formal-test and performance logs.
