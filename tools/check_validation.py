"""Fail closed on missing, changed or inconsistent local cross-environment evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from validation_suite import sha, plan, normalize_command, behavioral_faults


def verify_runtime(runtime, expected_arch):
    actual = runtime['container']
    if (runtime['Architecture'] not in expected_arch or runtime['image']['Architecture'] not in expected_arch
            or runtime['image']['Os'] != 'linux' or runtime['NCPU'] != 4
            or actual['NetworkMode'] != 'none' or actual['Privileged'] or actual['NanoCpus'] != 4*10**9
            or actual['Memory'] != 4*1024**3 or actual['ShmSize'] != 256*1024**2
            or actual['CapDrop'] != ['ALL'] or 'no-new-privileges' not in actual['SecurityOpt']
            or actual['user'] != 'validator' or actual['mounts']):
        raise ValueError('Actual runtime differs from isolation/architecture contract')


def verify_environment(directory):
    report = json.loads((directory / 'validation.json').read_text())
    if report['status'] != 'passed' or report['benchmark_kind'] not in ('full', 'smoke'):
        raise ValueError('Incomplete validation')
    commands = plan(directory, report['benchmark_kind'])
    expected = [name for name, _ in commands]
    if [step['name'] for step in report['steps']] != expected:
        raise ValueError('Missing or reordered validation steps')
    actual_names = {str(path.relative_to(directory)) for path in directory.rglob('*') if path.is_file() and path != directory / 'validation.json'}
    if actual_names != set(report['artifacts']):
        raise ValueError('Artifact manifest is incomplete')
    for name, digest in report['artifacts'].items():
        path = directory / name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or sha(path) != digest:
            raise ValueError('Changed artifact: ' + name)
    if not report['artifacts']:
        raise ValueError('Missing artifact manifest')
    for step, (_, command) in zip(report['steps'], commands, strict=True):
        if report['schema_version'] >= 2 and step['command'] != normalize_command(command, directory):
            raise ValueError('Different executed command')
        if step['status'] != 'passed' or step['exit_code'] != 0:
            raise ValueError('Unsuccessful validation step')
        if report['artifacts'].get(step['log']) != step['log_sha256']:
            raise ValueError('Unbound test log')
    normal, optimized, mutation = report['steps'][:3]
    if normal['tests_run'] <= 0 or normal['tests_run'] != optimized['tests_run'] or mutation['faults_detected'] != 10:
        raise ValueError('Insufficient tests or source faults')
    for step in (normal, optimized):
        text = (directory / step['log']).read_text()
        found = re.search(r'Ran (\d+) tests? in ', text)
        if found is None or int(found.group(1)) != step['tests_run'] or not re.search(r'^OK\s*$', text, re.M):
            raise ValueError('Actual unittest result differs')
    if len(re.findall(r'^Detected:', (directory / mutation['log']).read_text(), re.M)) != 10:
        raise ValueError('Actual behavioral faults differ')
    if report['schema_version'] >= 2:
        if behavioral_faults((directory / mutation['log']).read_text()) != mutation['fault_ids']:
            raise ValueError('Actual source faults differ')
        actual_ids = re.findall(r'^test\S+ \(([^)]+)\) \.\.\.', (directory / normal['log']).read_text(), re.M)
        if actual_ids != normal['test_ids'] or len(set(actual_ids)) != normal['tests_run']:
            raise ValueError('Different executed test identities')
        from tiny_ipc_lab.experiment import fingerprint
        bound = {key: value for key, value in report['source_files'].items() if key.startswith('src/tiny_ipc_lab/') and key.endswith('.py')}
        if not bound or bound != report['implementation_files'] or fingerprint({Path(key).name: value for key, value in bound.items()}) != report['source_sha256']:
            raise ValueError('Imported implementation is not bound to snapshot')
    measured_path = directory / report['measurement']['file']
    if sha(measured_path) != report['measurement']['sha256']:
        raise ValueError('Changed benchmark report')
    measured = json.loads(measured_path.read_text())
    if measured['source_sha256'] != report['source_sha256']:
        raise ValueError('Different measured source')
    trials = sum(len(case['runs']) for case in measured['cases'])
    messages = sum(run['summary']['verified_messages'] for case in measured['cases'] for run in case['runs'])
    if (trials, messages) != (report['measurement']['trials'], report['measurement']['messages']):
        raise ValueError('Measurement counts differ')
    from check_project import check as check_measurement
    check_measurement(directory / 'benchmark', smoke=report['benchmark_kind'] == 'smoke')
    for api in ('into', 'bytes'):
        check_measurement(directory / ('legacy-' + api), smoke=True)
    if report['schema_version'] >= 2:
        expected_counts = (200, 654450) if report['benchmark_kind'] == 'full' else (40, 680)
        if (trials, messages) != expected_counts:
            raise ValueError('Wrong full/smoke workload')
    return report


def check(directory, *, finalizing=False):
    directory = Path(directory)
    combined = json.loads((directory / 'combined.json').read_text())
    snapshot = json.loads((directory / 'snapshot.json').read_text())
    tree = hashlib.sha256(json.dumps(snapshot['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if combined['status'] != ('checking' if finalizing else 'passed') or combined['vm_stop_exit_code'] != 0 or combined['snapshot_tree_sha256'] != tree or snapshot['tree_sha256'] != tree:
        raise ValueError('Incomplete run, cleanup or snapshot')
    if sha(directory / 'linux-runtime.json') != combined['linux_runtime_sha256']:
        raise ValueError('Changed runtime metadata')
    if combined['schema_version'] >= 2:
        cleanup = combined['cleanup']
        if cleanup['errors'] or cleanup['container'] != 'removed' or cleanup['vm'] != 'stopped' or not cleanup['evidence_copied']:
            raise ValueError('Unsuccessful resource cleanup')
        state = combined['container_exit']
        if state['Running'] or state['OOMKilled'] or state['ExitCode'] != 0 or state['Error']:
            raise ValueError('Container did not exit successfully')
        for name, operation in combined['operations'].items():
            if operation['status'] != 'passed' or operation['exit_code'] != 0 or sha(directory / operation['log']) != operation['log_sha256']:
                raise ValueError('Failed or changed orchestration operation: ' + name)
    elif finalizing:
        raise ValueError('New runs require reviewed schema 2')
    reports = [verify_environment(directory / name) for name in ('native', 'linux')]
    for report, system, environment in zip(reports, ('Darwin', 'Linux'), ('native-macos', 'colima-linux')):
        if combined['schema_version'] >= 2 and report['schema_version'] != 2:
            raise ValueError('New run has legacy environment record')
        if report['host']['os'] != system or report['environment'] != environment:
            raise ValueError('Wrong execution environment')
        if report['source_files'] != snapshot['files'] or report['source_sha256'] != combined['source_sha256'] or report['benchmark_kind'] != combined['benchmark_kind']:
            raise ValueError('Different source or benchmark configuration')
    if reports[0]['steps'][0]['tests_run'] != reports[1]['steps'][0]['tests_run']:
        raise ValueError('Different test coverage')
    if combined['schema_version'] >= 2:
        native, linux = reports
        if native['versions'] != linux['versions'] or native['host']['python'] != linux['host']['python'] or native['steps'][0]['test_ids'] != linux['steps'][0]['test_ids']:
            raise ValueError('Different dependency versions or executed tests')
        arch = native['host']['machine']
        aliases = ('arm64', 'aarch64') if arch in ('arm64', 'aarch64') else ('x86_64', 'amd64')
        if linux['host']['machine'] not in aliases:
            raise ValueError('Cross-architecture execution')
        runtime = json.loads((directory / 'linux-runtime.json').read_text())
        verify_runtime(runtime, aliases)
        if runtime['dockerfile_sha256'] != snapshot['files']['containers/validation.Dockerfile']:
            raise ValueError('Different container recipe')
    if combined['schema_version'] >= 2 and not finalizing:
        from validation_report import render
        measured = [json.loads((directory / name / 'benchmark/report.json').read_text()) for name in ('native', 'linux')]
        if sha(directory / 'validation.html') != combined['html_sha256'] or (directory / 'validation.html').read_text() != render(combined, measured):
            raise ValueError('Different labelled HTML report')
    print('Verified both environments, all steps/logs/raw hashes, shared source and separate measurements.')
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    check(parser.parse_args().directory)
