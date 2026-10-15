"""One environment's real tests, archived-evidence checks and separate IPC measurements."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def execute(command, logfile, *, timeout=900, cwd=ROOT):
    start = time.monotonic()
    status = 'passed'
    with Path(logfile).open('wb') as log:
        child = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            status = 'timeout'
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            # Descendants may outlive a parent which exits promptly on TERM.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            code = child.returncode
        if code != 0 and status == 'passed':
            status = 'failed'
    return dict(status=status, exit_code=code, elapsed_s=time.monotonic()-start,
                log=Path(logfile).name, log_sha256=sha(logfile))


def plan(output, benchmark):
    python = sys.executable
    steps = [('tests', [python, '-m', 'unittest', 'discover', '-s', 'tests', '-v']),
             ('optimized', [python, '-O', '-m', 'unittest', 'discover', '-s', 'tests']),
             ('mutations', [python, 'tools/run_mutations.py'])]
    for i, directory in enumerate(('macos-arm64-pool-reviewed', 'macos-arm64-pool', 'macos-arm64-pool-development', 'macos-arm64', 'macos-arm64-pipe-bytes')):
        steps.append((f'evidence-{i}', [python, 'tools/check_project.py', '--directory', 'results/' + directory]))
    steps += [('rss-diagnosis', [python, 'tools/diagnose_rss.py', '--verify']),
              ('original-audit', [python, 'tools/audit_original.py', '--verify']),
              ('pool-audit', [python, 'tools/audit_pool_original.py', '--verify'])]
    for api in ('into', 'bytes'):
        directory = output / ('legacy-' + api)
        steps += [('legacy-' + api, [python, '-m', 'tiny_ipc_lab.cli', '--output', str(directory), '--sizes', '64', '4096', '--count', '17', '--pairs', '2', '--pipe-receive', api]),
                  ('check-legacy-' + api, [python, 'tools/check_project.py', '--directory', str(directory), '--smoke'])]
    command = [python, '-m', 'tiny_ipc_lab.pool_bench', '--output', str(output / 'benchmark')]
    if benchmark == 'smoke':
        command += ['--sizes', '64', '1048576', '--blocks', '2', '--capacity', '3', '--smoke']
    steps += [('benchmark', command), ('check-benchmark', [python, 'tools/check_project.py', '--directory', str(output / 'benchmark')] + (['--smoke'] if benchmark == 'smoke' else []))]
    return steps


def tracked_files():
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    return {name: sha(ROOT / name) for name in names if name}


def run(output, environment, benchmark):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new evidence directory')
    output.mkdir(parents=True, exist_ok=True)
    from tiny_ipc_lab.experiment import source_hash
    import numpy
    import psutil
    if sys.version_info[:2] != (3, 12) or numpy.__version__ != '1.26.4' or psutil.__version__ != '7.0.0':
        raise RuntimeError('Production tests require Python 3.12, NumPy 1.26.4 and psutil 7.0.0')
    report = dict(schema_version=1, environment=environment, benchmark_kind=benchmark,
                  generated_utc=datetime.now(timezone.utc).isoformat(), source_sha256=source_hash(),
                  host=dict(os=platform.system(), release=platform.release(), machine=platform.machine(), python=platform.python_version()),
                  versions=dict(numpy=numpy.__version__, psutil=psutil.__version__), status='running', steps=[], source_files=tracked_files())
    save(output / 'validation.json', report)
    expected_steps = plan(output, benchmark)
    for name, command in expected_steps:
        print(f'[{environment}] {name}', flush=True)
        step = dict(name=name, **execute(command, output / (name + '.log')))
        if step['status'] == 'passed' and name in ('tests', 'optimized'):
            text = (output / step['log']).read_text()
            found = re.search(r'Ran (\d+) tests? in ', text)
            if found is None or int(found.group(1)) <= 0 or not re.search(r'^OK\s*$', text, re.M):
                step['status'] = 'invalid-test-result'
            else:
                step['tests_run'] = int(found.group(1))
        if step['status'] == 'passed' and name == 'mutations':
            step['faults_detected'] = len(re.findall(r'^Detected:', (output / step['log']).read_text(), re.M))
            if step['faults_detected'] != 10:
                step['status'] = 'invalid-mutation-result'
        report['steps'].append(step)
        save(output / 'validation.json', report)
        if step['status'] != 'passed':
            report['status'] = 'failed'
            break
    else:
        if source_hash() != report['source_sha256'] or tracked_files() != report['source_files']:
            report['status'] = 'source-changed'
        else:
            report['status'] = 'passed'
    if (output / 'benchmark/report.json').exists():
        measured = json.loads((output / 'benchmark/report.json').read_text())
        report['measurement'] = dict(file='benchmark/report.json', sha256=sha(output / 'benchmark/report.json'),
                                     trials=sum(len(c['runs']) for c in measured['cases']),
                                     messages=sum(r['summary']['verified_messages'] for c in measured['cases'] for r in c['runs']))
    report['artifacts'] = {str(path.relative_to(output)): sha(path) for path in sorted(output.rglob('*'))
                           if path.is_file() and path.name != 'validation.json'}
    save(output / 'validation.json', report)
    if report['status'] != 'passed':
        raise RuntimeError('Validation did not pass; retained step log identifies the failure')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--environment', choices=('native-macos', 'colima-linux', 'github-hosted'), required=True)
    parser.add_argument('--benchmark', choices=('full', 'smoke'), default='full')
    args = parser.parse_args()
    run(args.output, args.environment, args.benchmark)
