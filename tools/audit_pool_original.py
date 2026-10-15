"""Recheck immutable d0ba9c0 pool data; never relabel it as new timing measurements."""
import argparse
import gzip
import hashlib
import io
import json
import math
import numpy as np
from tiny_ipc_lab.report import summarize
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'd0ba9c0053467d00dd55449c00a4e87c1632e601'


def audit():
    data = subprocess.check_output(['git', 'archive', REVISION], cwd=ROOT)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(root, filter='data')
        subprocess.run([sys.executable, '-c', "import sys;sys.path.insert(0,'tools');from check_project import check;check('results/macos-arm64-pool')"],
                       cwd=root, env=dict(os.environ, PYTHONPATH=str(root / 'src')), check=True)
        counterexample_path = ROOT / 'reviews/pool-fifo-counterexample.json'
        subprocess.run([sys.executable, '-c', "import json,sys;from tiny_ipc_lab.report import summarize;summarize(json.load(open(sys.argv[1]))['run'])", str(counterexample_path)],
                       cwd=root, env=dict(os.environ, PYTHONPATH=str(root / 'src')), check=True)
        try:
            summarize(json.loads(counterexample_path.read_text())['run'])
        except ValueError as error:
            if 'FIFO' not in str(error):
                raise ValueError('Counterexample rejected for an unrelated reason') from error
        else:
            raise ValueError('Current verifier accepted an impossible FIFO trace')
        payload = (root / 'results/macos-arm64-pool/report.json').read_bytes()
        report = json.loads(payload)
        cases = []
        fifo_checked = independently_checked = 0
        max_gap_ms = 0.
        for case in report['cases']:
            for stub in case['runs']:
                run = json.loads(gzip.decompress((root / 'results/macos-arm64-pool' / stub['file']).read_bytes()))
                producer, consumer = run['producer'], run['consumer']
                duration = max(producer['end_s'], consumer['end_s']) - producer['start_s']
                throughput = run['payload_bytes'] * run['count'] / duration / 1048576
                latency95 = float(np.quantile([(x['end_s']-x['start_s'])*1000 for x in producer['records']], .95))
                peak = max(x['producer_rss_bytes']+x['consumer_rss_bytes'] for x in run['rss_samples'])
                if (not math.isclose(throughput, stub['summary']['payload_mib_per_s'], rel_tol=1e-12)
                        or not math.isclose(latency95, stub['summary']['round_trip_ms']['p95'], rel_tol=1e-12)
                        or peak != stub['summary']['peak_paired_rss_bytes']):
                    raise ValueError('Independent throughput/p95/RSS reconstruction differs')
                max_gap_ms = max(max_gap_ms, stub['summary']['max_rss_gap_ms'])
                independently_checked += 1
                if run['mode'] in ('pool', 'window_pipe'):
                    ends = [r['end_s'] for r in run['producer']['records']]
                    if ends != sorted(ends):
                        raise ValueError('Historical FIFO ACK chronology invalid')
                    fifo_checked += len(ends)
            for denominator in ('shared', 'window_pipe'):
                values = []
                for block in range(report['blocks']):
                    group = {r['profile']: r['summary']['payload_mib_per_s'] for r in case['runs'] if r['block'] == block}
                    values.append(group['pool_n'] / group[denominator])
                cases.append(dict(case=case['id'], denominator=denominator, all_block_ratios=values,
                                  median=median(values), min=min(values), max=max(values)))
        return dict(original_commit=REVISION, original_report_sha256=hashlib.sha256(payload).hexdigest(),
                    source_sha256=report['source_sha256'], verified_trials=sum(len(c['runs']) for c in report['cases']),
                    verified_messages=sum(r['summary']['verified_messages'] for c in report['cases'] for r in c['runs']),
                    additionally_checked_fifo_messages=fifo_checked, independently_rebuilt_resource_trials=independently_checked,
                    largest_recorded_rss_gap_ms=max_gap_ms, synthetic_counterexample_old_accepted=True,
                    synthetic_counterexample_current_rejected_for_fifo=True, comparisons=cases,
                    assessment='Original 2.309x and 8.399x at 1 MiB are all-five-block descriptive medians of verified finite exchanges. The former changes capacity/copy/protocol; the latter matches capacity/protocol but still includes Pipe allocation/copy and transport differences. Original latency ends at producer ACK observation; consumer-ready time was not recorded and cannot be reconstructed. Original RSS is sampled worker RSS, not unique physical RAM. New timing instrumentation requires fresh measurements.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'reviews/pool-original-d0ba9c0.json')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = audit()
    if args.verify:
        if json.loads(args.output.read_text()) != result:
            raise ValueError('Pool review differs from immutable source/data')
        print('Original 200 trials, all-five-block ratios and FIFO ACK chronology verified.')
    else:
        if args.output.exists():
            raise ValueError('Use a new review output')
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
