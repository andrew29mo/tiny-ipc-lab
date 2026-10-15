"""Fail closed on missing, changed or inconsistent local cross-environment evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from validation_suite import sha, plan


def verify_environment(directory):
    report = json.loads((directory / 'validation.json').read_text())
    if report['status'] != 'passed' or report['benchmark_kind'] not in ('full', 'smoke'):
        raise ValueError('Incomplete validation')
    expected = [name for name, _ in plan(directory, report['benchmark_kind'])]
    if [step['name'] for step in report['steps']] != expected:
        raise ValueError('Missing or reordered validation steps')
    actual_names = {str(path.relative_to(directory)) for path in directory.rglob('*') if path.is_file() and path.name != 'validation.json'}
    if actual_names != set(report['artifacts']):
        raise ValueError('Artifact manifest is incomplete')
    for name, digest in report['artifacts'].items():
        path = directory / name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or sha(path) != digest:
            raise ValueError('Changed artifact: ' + name)
    if not report['artifacts']:
        raise ValueError('Missing artifact manifest')
    for step in report['steps']:
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
    return report


def check(directory):
    directory = Path(directory)
    combined = json.loads((directory / 'combined.json').read_text())
    snapshot = json.loads((directory / 'snapshot.json').read_text())
    tree = hashlib.sha256(json.dumps(snapshot['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if combined['status'] != 'passed' or combined['vm_stop_exit_code'] != 0 or combined['snapshot_tree_sha256'] != tree or snapshot['tree_sha256'] != tree:
        raise ValueError('Incomplete run, cleanup or snapshot')
    if sha(directory / 'linux-runtime.json') != combined['linux_runtime_sha256']:
        raise ValueError('Changed runtime metadata')
    reports = [verify_environment(directory / name) for name in ('native', 'linux')]
    for report, system, environment in zip(reports, ('Darwin', 'Linux'), ('native-macos', 'colima-linux')):
        if report['host']['os'] != system or report['environment'] != environment:
            raise ValueError('Wrong execution environment')
        if report['source_files'] != snapshot['files'] or report['source_sha256'] != combined['source_sha256'] or report['benchmark_kind'] != combined['benchmark_kind']:
            raise ValueError('Different source or benchmark configuration')
    if reports[0]['steps'][0]['tests_run'] != reports[1]['steps'][0]['tests_run']:
        raise ValueError('Different test coverage')
    print('Verified both environments, all steps/logs/raw hashes, shared source and separate measurements.')
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    check(parser.parse_args().directory)
