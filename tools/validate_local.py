"""Native macOS + isolated Colima Linux, sequentially, from one credential-free snapshot."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from install_colima import install, digest
from validation_suite import save, execute

ROOT = Path(__file__).resolve().parents[1]


def capture(command, *, cwd=ROOT, env=None):
    return subprocess.check_output(command, cwd=cwd, env=env, text=True).strip()


def inventory(root):
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    result = {}
    for name in filter(None, names):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Snapshot requires ordinary tracked files: ' + name)
        result[name] = digest(path)
    return result


def snapshot(output):
    files = inventory(ROOT)
    workspace = output / 'context/workspace'
    workspace.mkdir(parents=True)
    for name in files:
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    bundle = output / 'history.bundle'
    subprocess.run(['git', 'bundle', 'create', str(bundle), 'HEAD'], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(['git', 'init', '--template=', '-q', '-b', 'snapshot-unborn'], cwd=workspace, check=True)
    subprocess.run(['git', 'fetch', '-q', str(bundle), 'HEAD:refs/heads/validation'], cwd=workspace, check=True)
    subprocess.run(['git', 'symbolic-ref', 'HEAD', 'refs/heads/validation'], cwd=workspace, check=True)
    subprocess.run(['git', 'add', '--all'], cwd=workspace, check=True)
    identity = dict(base_commit=capture(['git', 'rev-parse', 'HEAD']), files=files,
                    tree_sha256=hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                    modified=bool(capture(['git', 'status', '--porcelain'])))
    save(output / 'snapshot.json', identity)
    # Docker build context has no user Git config/remotes or untracked local files.
    return workspace, identity


def check_snapshot(workspace, identity):
    if inventory(workspace) != identity['files']:
        raise ValueError('Validation snapshot changed; cannot declare success')


def run(output, benchmark):
    if platform.system() != 'Darwin' or sys.version_info[:2] != (3, 12):
        raise RuntimeError('Run with a macOS Python 3.12 interpreter')
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Use a new validation output directory')
    output.mkdir(parents=True)
    summary = dict(schema_version=1, generated_utc=datetime.now(timezone.utc).isoformat(), status='running',
                   benchmark_kind=benchmark, scope='Native macOS and same-architecture Linux VM; separate performance/RSS, no cross-environment speedup.',
                   environments={})
    save(output / 'combined.json', summary)
    binaries, env = install()
    colima, docker = str(binaries / 'colima'), str(binaries / 'docker')
    profile = 'ipc'
    vm_command = [colima, 'start', profile, '--cpu', '4', '--memory', '6', '--disk', '40', '--vm-type', 'vz',
                  '--runtime', 'docker', '--mount', 'none', '--activate=false', '--ssh-config=false', '--ssh-agent=false',
                  '--vz-rosetta=false', '--binfmt=false']
    container = None
    copied = False
    try:
        # Only this dedicated profile is stopped; no benchmark overlaps VM startup/build.
        subprocess.run([colima, 'stop', profile], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        workspace, identity = snapshot(output)
        summary['snapshot_tree_sha256'] = identity['tree_sha256']
        native_env = output / 'native-env'
        setup = execute([sys.executable, '-m', 'venv', str(native_env)], output / 'native-venv.log')
        if setup['status'] != 'passed':
            raise RuntimeError('Native environment setup failed')
        python = str(native_env / 'bin/python')
        setup = execute([python, '-m', 'pip', 'install', '-r', 'requirements-dev.txt'], output / 'native-install.log', cwd=workspace)
        if setup['status'] != 'passed':
            raise RuntimeError('Native dependency setup failed')
        print('Running native macOS suite and measurements (VM stopped).', flush=True)
        result = execute([python, 'tools/validation_suite.py', '--output', str(output / 'native'), '--environment', 'native-macos', '--benchmark', benchmark],
                         output / 'native-driver.log', cwd=workspace, timeout=3600)
        summary['environments']['native'] = result
        save(output / 'combined.json', summary)
        if result['status'] != 'passed':
            raise RuntimeError('Native validation failed; inspect native/validation.json')
        check_snapshot(workspace, identity)
        print('Starting isolated Colima profile and building the Linux image.', flush=True)
        with (output / 'vm-start.log').open('w') as log:
            subprocess.run(vm_command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
        # Do not infer architecture from the host or from an emulation-capable image tag.
        info = json.loads(capture([docker, 'info', '--format', '{{json .}}'], env=env))
        vm = {key: info[key] for key in ('ServerVersion', 'KernelVersion', 'Architecture', 'OperatingSystem', 'NCPU', 'MemTotal')}
        vm.update(colima_version=capture([colima, 'version'], env=env).splitlines()[0],
                  lima_version=capture([str(binaries / 'limactl'), '--version'], env=env),
                  cpu_limit=4, memory_limit_bytes=4*1024**3, shm_bytes=256*1024**2,
                  network='none', privileged=False, vm_memory_gib=6, vm_disk_gib=40)
        expected_arch = ('aarch64', 'arm64') if platform.machine() == 'arm64' else ('x86_64', 'amd64')
        if vm['Architecture'] not in expected_arch:
            raise RuntimeError('VM architecture differs from requested native architecture')
        shutil.copyfile(workspace / 'containers/validation.Dockerfile', output / 'context/Dockerfile')
        image = 'tiny-ipc-validation:' + output.name.lower()
        with (output / 'image-build.log').open('w') as log:
            subprocess.run([docker, 'build', '--load', '-t', image, str(output / 'context')], env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
        inspect = json.loads(capture([docker, 'image', 'inspect', image], env=env))[0]
        vm['image'] = {key: inspect[key] for key in ('Id', 'Architecture', 'Os')}
        vm['dockerfile_sha256'] = digest(output / 'context/Dockerfile')
        container = 'tiny-ipc-validation-' + output.name.lower()
        subprocess.run([docker, 'create', '--name', container, '--network', 'none', '--cap-drop', 'ALL',
                        '--security-opt', 'no-new-privileges', '--cpus', '4', '--memory', '4g', '--shm-size', '256m',
                        image, '--output', '/evidence', '--environment', 'colima-linux', '--benchmark', benchmark],
                       env=env, check=True, stdout=subprocess.DEVNULL)
        container_info = json.loads(capture([docker, 'inspect', container], env=env))[0]
        actual = container_info['HostConfig']
        vm['container'] = {key: actual[key] for key in ('NetworkMode', 'Privileged', 'NanoCpus', 'Memory', 'ShmSize', 'CapDrop', 'SecurityOpt')}
        vm['container']['user'] = container_info['Config']['User']
        vm['container']['mounts'] = container_info['Mounts']
        if (actual['NetworkMode'] != 'none' or actual['Privileged'] or actual['NanoCpus'] != 4*10**9
                or actual['Memory'] != 4*1024**3 or actual['ShmSize'] != 256*1024**2
                or actual['CapDrop'] != ['ALL'] or 'no-new-privileges' not in actual['SecurityOpt']
                or container_info['Config']['User'] != 'validator' or container_info['Mounts']):
            raise RuntimeError('Actual container isolation differs from requested constraints')
        save(output / 'linux-runtime.json', vm)
        summary['linux_runtime_sha256'] = digest(output / 'linux-runtime.json')
        print('Running Linux suite and measurements; logs remain inside the container until copied.', flush=True)
        with (output / 'linux-driver.log').open('w') as log:
            completed = subprocess.run([docker, 'start', '--attach', container], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
        subprocess.run([docker, 'cp', container + ':/evidence', str(output / 'linux')], env=env, check=True)
        copied = True
        linux = json.loads((output / 'linux/validation.json').read_text())
        summary['environments']['linux'] = dict(status=linux['status'], exit_code=completed.returncode)
        if completed.returncode != 0 or linux['status'] != 'passed':
            raise RuntimeError('Linux validation failed; inspect linux/validation.json')
        native = json.loads((output / 'native/validation.json').read_text())
        if native['source_sha256'] != linux['source_sha256']:
            raise RuntimeError('Native and Linux production source differs')
        summary['source_sha256'] = native['source_sha256']
        check_snapshot(workspace, identity)
        summary['status'] = 'passed'
    except BaseException as error:
        summary['status'] = 'failed'
        summary['error_type'] = type(error).__name__
        raise
    finally:
        if container and not copied:
            subprocess.run([docker, 'kill', container], env=env, capture_output=True)
            export = subprocess.run([docker, 'cp', container + ':/evidence', str(output / 'linux-failed')], env=env, capture_output=True)
            copied = export.returncode == 0
        if container and copied:
            subprocess.run([docker, 'rm', '-f', container], env=env, capture_output=True)
        cleanup = subprocess.run([colima, 'stop', profile], env=env, capture_output=True)
        summary['vm_stop_exit_code'] = cleanup.returncode
        if cleanup.returncode != 0:
            summary['status'] = 'cleanup-failed'
        save(output / 'combined.json', summary)
    if summary['status'] != 'passed':
        raise RuntimeError('Validation cleanup did not pass')
    from check_validation import check
    check(output)
    print('Both environments passed; full local evidence: ' + str(output), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results/local/validation' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--benchmark', choices=('full', 'smoke'), default='full')
    args = parser.parse_args()
    run(args.output, args.benchmark)
