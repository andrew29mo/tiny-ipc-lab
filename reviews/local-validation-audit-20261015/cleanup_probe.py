"""Review fixture: time out a live owned Docker container, export evidence and clean up.

Run from the repository root with: .venv/bin/python <this-file> <full-validation-dir>
This is a cleanup fault probe, not a benchmark or a substitute for formal tests.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import uuid

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'tools'))
from install_colima import install, digest
from validate_local import Commands, cleanup, exclusive_run, stop_vm
from validation_process import cancellation_signals, cleanup_signals
from validation_suite import save


def probe(source):
    if platform.system() != 'Darwin':
        raise RuntimeError('This fixture starts the dedicated macOS Colima profile')
    original = json.loads((source / 'combined.json').read_text())
    if original['status'] != 'passed':
        raise RuntimeError('Complete the full validation first')
    runtime = json.loads((source / 'linux-runtime.json').read_text())
    output = ROOT / 'results/local/cleanup-probe' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output.mkdir(parents=True)
    summary = dict(schema_version=1, purpose='Actual Docker timeout / owned-container cleanup fault probe; not a measurement run', status='running', operations={},
                   tested_helpers={name:digest(ROOT / name) for name in ('tools/validate_local.py','tools/validation_process.py')})
    runner = Commands(output, summary)
    token = uuid.uuid4().hex
    done = False
    colima = docker = None
    with exclusive_run(ROOT):
        try:
            binaries, runner.env = install()
            colima, docker = str(binaries / 'colima'), str(binaries / 'docker')
            stop_vm(runner, colima, 'initial-stop')
            runner.call('vm-start', [colima, 'start', 'ipc', '--cpu', '4', '--memory', '6', '--disk', '40', '--vm-type', 'vz', '--runtime', 'docker',
                                    '--mount', 'none', '--activate=false', '--ssh-config=false', '--ssh-agent=false', '--vz-rosetta=false', '--binfmt=false'], timeout=900)
            code = ('import signal,time; from pathlib import Path; '
                    'signal.signal(signal.SIGINT,signal.SIG_IGN); signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                    'Path("/evidence/probe.json").write_text("{\\"probe\\":\\"owned-cleanup\\",\\"sequence\\":1}"); time.sleep(60)')
            name = 'tiny-ipc-cleanup-probe-' + token
            runner.call('create', [docker, 'create', '--name', name, '--label', 'tiny-ipc.validation.run=' + token, '--network', 'none', '--cap-drop', 'ALL',
                                  '--security-opt', 'no-new-privileges', '--cpus', '4', '--memory', '4g', '--shm-size', '256m', '--entrypoint', 'python', runtime['image']['Id'], '-c', code])
            result = runner.call('attach-timeout', [docker, 'start', '--attach', name], timeout=1, check=False)
            if result['status'] != 'timeout':
                raise RuntimeError('Did not exercise the actual timeout path')
            state = json.loads(runner.capture('still-running', [docker, 'inspect', name]))[0]['State']
            if not state['Running']:
                raise RuntimeError('Expected live daemon-owned container after client timeout')
            summary['expected_attach_timeout'] = True
            summary['container_running_after_client_timeout'] = True
            with cleanup_signals():
                summary['cleanup'] = cleanup(runner, colima, docker, token, False, True)
            done = True
            receipt = summary['cleanup']
            if receipt['errors'] or receipt['container'] != 'removed' or receipt['vm'] != 'stopped' or not receipt['evidence_copied']:
                raise RuntimeError('Actual cleanup probe failed')
            marker = json.loads((output / 'linux-failed/probe.json').read_text())
            if marker != dict(probe='owned-cleanup', sequence=1):
                raise RuntimeError('Retained evidence differs')
            summary.update(status='passed', retained_marker=marker)
        except BaseException as error:
            summary.update(status='failed', error_type=type(error).__name__)
            raise
        finally:
            if not done:
                with cleanup_signals():
                    summary['cleanup'] = cleanup(runner, colima, docker, token, False, bool(colima))
            save(output / 'combined.json', summary)
    print(output)
    return output


if __name__ == '__main__':
    with cancellation_signals():
        probe(Path(sys.argv[1]).resolve())
