"""Canonical README findings, derived from every primary block rather than hand-picked trials."""
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
START, END = '<!-- POOL_RESULTS_START -->', '<!-- POOL_RESULTS_END -->'


def findings(report):
    trials = sum(len(c['runs']) for c in report['cases'])
    messages = sum(r['summary']['verified_messages'] for c in report['cases'] for r in c['runs'])
    lines = [START, f'The primary run retains **{trials} trials and {messages:,} verified tensors** across six normal sizes and two slow-consumer cases. Five rotating blocks include every profile at every order position.', '',
             '| Case | Pool 4 / copied single buffer | Pool 4 / equal-window Pipe |', '|---|---:|---:|']
    for case, label in [('normal-64', '64 B, normal'), ('normal-1048576', '1 MiB, normal'), ('normal-4194304', '4 MiB, normal'), ('slow-1048576', '1 MiB, 1 ms delayed ACK')]:
        ratios = []
        for denominator in ['shared', 'window_pipe']:
            r = next(x for x in report['comparisons'] if x['case'] == case and x['numerator'] == 'pool_n' and x['denominator'] == denominator)
            ratios.append(f'{r["median"]:.3f} [{r["min"]:.3f}, {r["max"]:.3f}]')
        lines.append(f'| {label} | ' + ' | '.join(ratios) + ' |')
    case = next(c for c in report['cases'] if c['id'] == 'normal-1048576')
    values = []
    for profile in ['shared', 'pool_n']:
        stats = [r['summary'] for r in case['runs'] if r['profile'] == profile]
        values.append((median(s['round_trip_ms']['p95'] for s in stats), max(s['peak_paired_rss_bytes'] for s in stats)/1048576, median(s['admitted_to_ready_ms']['p95'] for s in stats), median(s['ack_observation_lag_ms']['p95'] for s in stats)))
    lines += ['', 'Ratios are medians [observed min, max] of all five within-block throughput ratios, not confidence intervals or ratios of table medians.', '',
              f'At 1 MiB normal load, copied single-buffer versus pool-4 median per-trial p95 producer ACK-observed latency is **{values[0][0]:.3f} vs {values[1][0]:.3f} ms** (includes admission waiting and deferred ACK collection); admitted-to-consumer-ready p95 is **{values[0][2]:.3f} vs {values[1][2]:.3f} ms**, and ACK-observation-lag p95 is **{values[0][3]:.3f} vs {values[1][3]:.3f} ms**. Maximum sampled paired RSS is **{values[0][1]:.2f} vs {values[1][1]:.2f} MiB**. Throughput gains can trade off latency and resident memory. These RSS maxima are not paired physical-memory savings.', '',
              'These are fresh schema-4 observations with separate consumer-ready clocks. The original schema-3 run and its development run remain historical evidence, verified from immutable source. The full reviewed grid was executed once without concurrent test/validation processes launched by this task; OS/desktop interference remains uncontrolled.', END]
    return '\n'.join(lines)


def check(report):
    expected = findings(report)
    text = (ROOT / 'README.md').read_text()
    if START not in text or END not in text or text[text.index(START):text.index(END)+len(END)] != expected:
        raise ValueError('README primary pool findings differ from retained evidence')


if __name__ == '__main__':
    report = json.loads((ROOT / 'results/macos-arm64-pool-reviewed/report.json').read_text())
    print(findings(report))
