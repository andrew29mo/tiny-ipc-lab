"""Sequential native macOS / Colima Linux validation from one bounded, owned run."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid

from install_colima import install, digest
from validation_suite import save, execute
from validation_process import cancellation_signals, cleanup_signals

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def exclusive_run(root=ROOT):
    path = root / 'results/local/runtime/validation.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another validation owns this project VM') from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def inventory(root):
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root, timeout=30).decode().split('\0')
    result = {}
    for name in filter(None, names):
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Snapshot requires ordinary tracked files: ' + name)
        result[name] = digest(path)
    return result


class Commands:
    def __init__(self, output, summary, env=None):
        self.output, self.summary, self.env = output, summary, env

    def call(self, name, command, *, timeout=120, cwd=ROOT, check=True):
        log = self.output / (name + '.log')
        try:
            result = execute(command, log, timeout=timeout, cwd=cwd, env=self.env)
        except BaseException as error:
            result = dict(status='interrupted', error_type=type(error).__name__, log=log.name)
            self.summary['operations'][name] = result
            save(self.output / 'combined.json', self.summary)
            raise
        self.summary['operations'][name] = result
        save(self.output / 'combined.json', self.summary)
        if check and result['status'] != 'passed':
            raise RuntimeError('Command failed or timed out: ' + name)
        return result

    def capture(self, name, command, **kwargs):
        self.call(name, command, **kwargs)
        return (self.output / (name + '.log')).read_text().strip()


def snapshot(output, commands):
    files = inventory(ROOT)
    workspace = output / 'context/workspace'
    workspace.mkdir(parents=True)
    for name in files:
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    bundle = output / 'history.bundle'
    commands.call('snapshot-bundle', ['git', 'bundle', 'create', str(bundle), 'HEAD'])
    commands.call('snapshot-init', ['git', 'init', '--template=', '-q', '-b', 'snapshot-unborn'], cwd=workspace)
    commands.call('snapshot-fetch', ['git', 'fetch', '-q', str(bundle), 'HEAD:refs/heads/validation'], cwd=workspace)
    commands.call('snapshot-head', ['git', 'symbolic-ref', 'HEAD', 'refs/heads/validation'], cwd=workspace)
    commands.call('snapshot-index', ['git', 'add', '--all'], cwd=workspace)
    identity = dict(base_commit=commands.capture('base-commit', ['git', 'rev-parse', 'HEAD']), files=files,
                    tree_sha256=hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                    modified=bool(commands.capture('working-status', ['git', 'status', '--porcelain'])))
    save(output / 'snapshot.json', identity)
    check_snapshot(workspace, identity)
    return workspace, identity


def check_snapshot(workspace, identity):
    if inventory(workspace) != identity['files']:
        raise ValueError('Validation snapshot changed')


def profile_status(commands, colima, label):
    lines = commands.capture(label, [colima, 'list', '--json']).splitlines()
    profiles = [json.loads(line) for line in lines if line.strip()]
    matches = [item for item in profiles if item['name'] == 'ipc']
    if len(matches) > 1:
        raise ValueError('Ambiguous VM profile')
    return matches[0]['status'] if matches else 'Absent'


def stop_vm(commands, colima, prefix):
    state = profile_status(commands, colima, prefix + '-before')
    if state not in ('Stopped', 'Absent'):
        commands.call(prefix, [colima, 'stop', 'ipc'], timeout=180)
    after = profile_status(commands, colima, prefix + '-after')
    if after not in ('Stopped', 'Absent'):
        raise RuntimeError('VM did not stop')
    return after


def cleanup(commands, colima, docker, token, copied, vm_attempted):
    result = dict(container='not-created', vm='not-started', errors=[], evidence_copied=copied)
    if docker and vm_attempted:
        try:
            # Unique per-run ownership label, not a user-supplied container name.
            ids = commands.capture('cleanup-owned', [docker, 'ps', '-aq', '--filter', 'label=tiny-ipc.validation.run=' + token]).split()
            if len(ids) > 1:
                raise RuntimeError('Ambiguous owned container')
            if ids:
                identifier = ids[0]
                result['container'] = 'present'
                result['container_id'] = identifier
                state = json.loads(commands.capture('cleanup-state', [docker, 'inspect', identifier]))[0]['State']
                if state['Running']:
                    commands.call('cleanup-kill', [docker, 'kill', identifier])
                if not copied:
                    exported = commands.call('cleanup-export', [docker, 'cp', identifier + ':/evidence', str(commands.output / 'linux-failed')], check=False)
                    copied = exported['status'] == 'passed'
                    result['evidence_copied'] = copied
                if copied:
                    commands.call('cleanup-remove', [docker, 'rm', identifier])
                    remaining = commands.capture('cleanup-remaining', [docker, 'ps', '-aq', '--filter', 'label=tiny-ipc.validation.run=' + token])
                    if remaining:
                        raise RuntimeError('Container survived removal')
                    result['container'] = 'removed'
                else:
                    result['container'] = 'retained'
                    result['errors'].append('Evidence export failed; owned container retained for recovery')
        except BaseException as error:
            result['errors'].append('container: ' + type(error).__name__)
    if colima and vm_attempted:
        try:
            stop_vm(commands, colima, 'cleanup-vm-stop')
            result['vm'] = 'stopped'
        except BaseException as error:
            result['errors'].append('vm: ' + type(error).__name__)
    return result


def finalize(output, summary):
    from check_validation import check
    summary['status'] = 'checking'
    save(output / 'combined.json', summary)
    try:
        check(output, finalizing=True)
        from validation_report import render
        measured = [json.loads((output / name / 'benchmark/report.json').read_text()) for name in ('native', 'linux')]
        (output / 'validation.html').write_text(render(summary, measured))
        summary['html_sha256'] = digest(output / 'validation.html')
    except BaseException as error:
        summary.update(status='integrity-failed', error_type=type(error).__name__)
        save(output / 'combined.json', summary)
        raise
    summary['status'] = 'passed'
    save(output / 'combined.json', summary)


def run(output, benchmark):
    if platform.system() != 'Darwin' or sys.version_info[:2] != (3, 12):
        raise RuntimeError('Run with a macOS Python 3.12 interpreter and project dependencies')
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Use a new validation output directory')
    output.mkdir(parents=True)
    summary = dict(schema_version=2, generated_utc=datetime.now(timezone.utc).isoformat(), status='running',
                   benchmark_kind=benchmark, scope='Native macOS and native-architecture Linux VM. Separate performance/RSS; no cross-environment speedup or whole-VM memory claim.',
                   operations={}, environments={})
    save(output / 'combined.json', summary)
    commands = Commands(output, summary)
    colima = docker = None
    vm_attempted = copied = False
    token = uuid.uuid4().hex
    try:
        with exclusive_run(ROOT):
            try:
                binaries, commands.env = install()
                colima, docker = str(binaries / 'colima'), str(binaries / 'docker')
                stop_vm(commands, colima, 'initial-stop')
                workspace, identity = snapshot(output, commands)
                summary['snapshot_tree_sha256'] = identity['tree_sha256']
                native_env = output / 'native-env'
                commands.call('native-venv', [sys.executable, '-m', 'venv', str(native_env)])
                python = str(native_env / 'bin/python')
                commands.call('native-install', [python, '-m', 'pip', 'install', '-r', 'requirements-dev.txt'], cwd=workspace, timeout=900)
                print('Running native macOS suite and measurements; VM verified stopped.', flush=True)
                result = commands.call('native-driver', [python, 'tools/validation_suite.py', '--output', str(output / 'native'), '--environment', 'native-macos', '--benchmark', benchmark], cwd=workspace, timeout=3600)
                summary['environments']['native'] = result
                check_snapshot(workspace, identity)
                vm_attempted = True
                print('Starting isolated Linux VM and building image.', flush=True)
                commands.call('vm-start', [colima, 'start', 'ipc', '--cpu', '4', '--memory', '6', '--disk', '40', '--vm-type', 'vz',
                              '--runtime', 'docker', '--mount', 'none', '--activate=false', '--ssh-config=false', '--ssh-agent=false',
                              '--vz-rosetta=false', '--binfmt=false'], timeout=900)
                info = json.loads(commands.capture('docker-info', [docker, 'info', '--format', '{{json .}}']))
                vm = {key: info[key] for key in ('ServerVersion', 'KernelVersion', 'Architecture', 'OperatingSystem', 'NCPU', 'MemTotal')}
                expected_arch = ('aarch64', 'arm64') if platform.machine() == 'arm64' else ('x86_64', 'amd64')
                if vm['Architecture'] not in expected_arch:
                    raise RuntimeError('VM architecture differs from host architecture')
                vm.update(colima_version=commands.capture('colima-version', [colima, 'version']).splitlines()[0],
                          lima_version=commands.capture('lima-version', [str(binaries / 'limactl'), '--version']))
                shutil.copyfile(workspace / 'containers/validation.Dockerfile', output / 'context/Dockerfile')
                image = 'tiny-ipc-validation:' + token
                commands.call('image-build', [docker, 'build', '--load', '-t', image, str(output / 'context')], timeout=1200)
                image_info = json.loads(commands.capture('image-info', [docker, 'image', 'inspect', image]))[0]
                vm['image'] = {key: image_info[key] for key in ('Id', 'Architecture', 'Os')}
                vm['dockerfile_sha256'] = digest(output / 'context/Dockerfile')
                name = 'tiny-ipc-validation-' + token
                commands.call('container-create', [docker, 'create', '--name', name, '--label', 'tiny-ipc.validation.run=' + token,
                              '--network', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--cpus', '4', '--memory', '4g', '--shm-size', '256m',
                              image, '--output', '/evidence', '--environment', 'colima-linux', '--benchmark', benchmark])
                container_info = json.loads(commands.capture('container-info', [docker, 'inspect', name]))[0]
                actual = container_info['HostConfig']
                vm['container'] = {key: actual[key] for key in ('NetworkMode', 'Privileged', 'NanoCpus', 'Memory', 'ShmSize', 'CapDrop', 'SecurityOpt')}
                vm['container'].update(user=container_info['Config']['User'], mounts=container_info['Mounts'])
                from check_validation import verify_runtime
                verify_runtime(vm, expected_arch)
                save(output / 'linux-runtime.json', vm)
                summary['linux_runtime_sha256'] = digest(output / 'linux-runtime.json')
                print('Running Linux formal suite and separate measurements.', flush=True)
                result = commands.call('linux-driver', [docker, 'start', '--attach', name], timeout=3600, check=False)
                state = json.loads(commands.capture('container-exit', [docker, 'inspect', name]))[0]['State']
                summary['container_exit'] = {key: state[key] for key in ('Running', 'ExitCode', 'OOMKilled', 'Error')}
                commands.call('linux-export', [docker, 'cp', name + ':/evidence', str(output / 'linux')])
                copied = True
                linux = json.loads((output / 'linux/validation.json').read_text())
                summary['environments']['linux'] = dict(status=linux['status'], exit_code=result['exit_code'])
                if result['status'] != 'passed' or state['Running'] or state['ExitCode'] != 0 or state['OOMKilled'] or state['Error'] or linux['status'] != 'passed':
                    raise RuntimeError('Linux process/attach/evidence did not all pass')
                native = json.loads((output / 'native/validation.json').read_text())
                summary['source_sha256'] = native['source_sha256']
                check_snapshot(workspace, identity)
            finally:
                with cleanup_signals():
                    summary['cleanup'] = cleanup(commands, colima, docker, token, copied, vm_attempted)
                    summary['vm_stop_exit_code'] = 0 if not summary['cleanup']['errors'] else 1
                    save(output / 'combined.json', summary)
            if summary['cleanup']['errors']:
                raise RuntimeError('Cleanup did not complete')
            finalize(output, summary)
    except BaseException as error:
        if summary['status'] != 'integrity-failed':
            summary.update(status='failed', error_type=type(error).__name__)
        save(output / 'combined.json', summary)
        raise
    print('Both environments passed; verified local evidence: ' + str(output), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results/local/validation' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--benchmark', choices=('full', 'smoke'), default='full')
    args = parser.parse_args()
    with cancellation_signals():
        run(args.output, args.benchmark)
