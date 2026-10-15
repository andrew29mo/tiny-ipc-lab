"""A clearly labelled entry point; canonical production benchmark reports stay intact."""
import html
from statistics import median


def render(summary, reports):
    esc = lambda value: html.escape(str(value))
    sections = []
    for name, label, report in zip(('native', 'linux'), ('Native macOS', 'Linux inside Colima VM'), reports, strict=True):
        rows = []
        for case in report['cases']:
            for profile in report['profiles']:
                values = [run['summary'] for run in case['runs'] if run['profile'] == profile]
                row = [case['id'], profile, f"{median(v['payload_mib_per_s'] for v in values):.2f}",
                       f"{median(v['round_trip_ms']['p95'] for v in values):.4f}",
                       f"{max(v['peak_paired_rss_bytes'] for v in values)/1048576:.2f}"]
                rows.append('<tr>' + ''.join('<td>' + esc(value) + '</td>' for value in row) + '</tr>')
        scope = ('VM verified stopped during native measurements.' if name == 'native' else
                 'Virtualized native-architecture Linux; 4 CPU / 4 GiB container, 256 MiB shared memory. Worker RSS excludes VM and Docker daemon overhead. Whole-VM host memory was not measured.')
        host = report['host']
        sections.append(f'<section id="{name}"><h2>{esc(label)}</h2><p>{esc(scope)}</p>'
                        f'<p>{esc(host["os"])} / {esc(host["machine"])} / Python {esc(host["python"])}</p>'
                        '<div class="scroll"><table><tr><th>Case</th><th>Profile</th><th>Median MiB/s</th><th>Median per-trial ACK p95 ms</th><th>Maximum sampled worker RSS sum MiB</th></tr>'
                        + ''.join(rows) + f'</table></div><p><a href="{name}/benchmark/report.json">Full JSON</a> · <a href="{name}/benchmark/report.html">Canonical HTML and raw record links</a></p></section>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Native macOS and virtualized Linux validation</title><style>body{font:16px/1.6 system-ui;max-width:1150px;margin:30px auto;padding:20px;color:#172b3b}section{margin-top:40px}table{border-collapse:collapse;white-space:nowrap}td,th{padding:8px;text-align:right;border-bottom:1px solid #ccc}.scroll{overflow:auto}</style>'
            '<h1>Native macOS / virtualized Linux validation</h1><p>Separate observations, not a controlled cross-environment speedup. All blocks are retained. Sampled two-worker RSS can double-count shared pages; it is not unique physical RAM or an exact peak.</p>'
            '<p>ACK-observed latency includes admission waiting and ACK collection. Full reports also contain consumer-ready and ACK-observation timing.</p>'
            f'<p>Benchmark: {esc(summary["benchmark_kind"])} · Source SHA-256: <code>{esc(summary["source_sha256"])}</code></p>'
            '<p><a href="combined.json">Validation and cleanup receipt</a> · <a href="#native">Native macOS</a> · <a href="#linux">Linux VM</a></p>'
            + ''.join(sections) + '</html>')
