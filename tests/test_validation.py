"""Challenge the actual validation runner and its fail-closed evidence checker."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from validation_suite import execute, plan, sha, save
from check_validation import verify_environment


class ValidationTests(unittest.TestCase):
    def test_actual_nonzero_process_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / 'failure.log'
            result = execute([sys.executable, '-c', 'print("failure evidence"); raise SystemExit(7)'], log)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['exit_code'], 7)
            self.assertEqual(result['log_sha256'], sha(log))
            self.assertIn('failure evidence', log.read_text())

    def test_actual_timeout_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = execute([sys.executable, '-c', 'import time; time.sleep(20)'], Path(temporary) / 'timeout.log', timeout=0.1)
            self.assertEqual(result['status'], 'timeout')
            self.assertNotEqual(result['exit_code'], 0)
            self.assertLess(result['elapsed_s'], 10)

    def test_production_commands_same_for_full_and_smoke(self):
        full = plan(Path('/evidence'), 'full')
        smoke = plan(Path('/evidence'), 'smoke')
        self.assertEqual(full[:-2], smoke[:-2])
        self.assertEqual(len(full), 17)
        self.assertEqual(full[0][1][1:], ['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
        self.assertIn('tiny_ipc_lab.pool_bench', full[-2][1])

    def test_claimed_pass_with_missing_steps_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            save(directory / 'validation.json', dict(status='passed', benchmark_kind='full', steps=[]))
            with self.assertRaises(ValueError):
                verify_environment(directory)

    def test_tampered_log_rejected_before_claimed_test_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            log = directory / 'tests.log'
            log.write_text('original')
            report = dict(status='passed', benchmark_kind='smoke', steps=[dict(name=name) for name, _ in plan(directory, 'smoke')], artifacts={'tests.log': sha(log)})
            save(directory / 'validation.json', report)
            log.write_text('forged OK')
            with self.assertRaisesRegex(ValueError, 'Changed artifact'):
                verify_environment(directory)


class ReviewRegressionTests(unittest.TestCase):
    def test_timeout_reaps_descendant_in_new_session(self):
        import os
        import psutil
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            marker = directory / 'descendant'
            child_code = 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)'
            code = ('import subprocess,sys,time; from pathlib import Path; '
                    f'child=subprocess.Popen([sys.executable,"-c",{child_code!r}],start_new_session=True); '
                    f'Path({str(marker)!r}).write_text(str(child.pid)); time.sleep(30)')
            result = execute([sys.executable, '-c', code], directory / 'timeout.log', timeout=0.4)
            self.assertEqual(result['status'], 'timeout')
            pid = int(marker.read_text())
            try:
                self.assertEqual(psutil.Process(pid).status(), psutil.STATUS_ZOMBIE)
            except psutil.NoSuchProcess:
                pass

    def test_sigterm_reaps_actual_owned_processes(self):
        import os
        import psutil
        import signal
        import subprocess
        import time
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            marker = directory / 'owned'
            child_code = f'import os,time; from pathlib import Path; Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(30)'
            code = ('import sys; sys.path.insert(0,' + repr(str(Path(__file__).resolve().parents[1] / 'tools')) + '); '
                    'from validation_process import cancellation_signals,execute\n'
                    'with cancellation_signals():\n'
                    f' execute([sys.executable,"-c",{child_code!r}],{str(directory / "child.log")!r})\n')
            with (directory / 'driver.log').open('wb') as log:
                driver = subprocess.Popen([sys.executable, '-c', code], stdout=log, stderr=log)
                try:
                    deadline = time.monotonic() + 8
                    while not marker.exists() and driver.poll() is None and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertTrue(marker.exists(), (directory / 'driver.log').read_text())
                    driver.send_signal(signal.SIGTERM)
                    self.assertNotEqual(driver.wait(timeout=10), 0)
                    try:
                        self.assertEqual(psutil.Process(int(marker.read_text())).status(), psutil.STATUS_ZOMBIE)
                    except psutil.NoSuchProcess:
                        pass
                finally:
                    if driver.poll() is None:
                        driver.kill()
                        driver.wait()

    def test_final_integrity_failure_rewrites_pass_claim(self):
        from validate_local import finalize
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            state = dict(status='passed')
            with self.assertRaises(FileNotFoundError):
                finalize(directory, state)
            self.assertEqual(json.loads((directory / 'combined.json').read_text())['status'], 'integrity-failed')

    def test_install_failure_recorded_not_left_running(self):
        from unittest.mock import patch
        import validate_local
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(validate_local, 'ROOT', root), patch.object(validate_local.platform, 'system', return_value='Darwin'), patch.object(validate_local, 'install', side_effect=RuntimeError('installer failed')):
                with self.assertRaises(RuntimeError):
                    validate_local.run(root / 'run', 'smoke')
            state = json.loads((root / 'run/combined.json').read_text())
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(state['error_type'], 'RuntimeError')

    def test_same_project_lock_rejects_concurrent_run(self):
        from validate_local import exclusive_run
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with exclusive_run(root):
                with self.assertRaisesRegex(RuntimeError, 'Another validation'):
                    with exclusive_run(root):
                        self.fail('second owner acquired lock')
            with exclusive_run(root):
                pass

    def test_import_from_outside_snapshot_rejected(self):
        from unittest.mock import patch
        import validation_suite
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(validation_suite, 'ROOT', Path(temporary)):
                with self.assertRaisesRegex(ValueError, 'outside the snapshot'):
                    validation_suite.implementation({})

    def test_cleanup_command_timeout_is_failure_and_retained(self):
        from validate_local import Commands
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            summary = dict(operations={})
            runner = Commands(directory, summary)
            with self.assertRaises(RuntimeError):
                runner.call('cleanup', [sys.executable, '-c', 'import time;time.sleep(30)'], timeout=.1)
            self.assertEqual(json.loads((directory / 'combined.json').read_text())['operations']['cleanup']['status'], 'timeout')

    def test_failed_initial_vm_stop_cannot_start_measurement(self):
        from validate_local import stop_vm
        class Fake:
            def capture(self, name, command):
                return '{"name":"ipc","status":"Running"}'
            def call(self, *args, **kwargs):
                raise RuntimeError('stop failed')
        with self.assertRaisesRegex(RuntimeError, 'stop failed'):
            stop_vm(Fake(), 'colima', 'initial')

    def test_failed_remove_and_export_keep_failure_and_still_stop_vm(self):
        from validate_local import cleanup
        class Fake:
            output = Path('/evidence')
            def __init__(self, copied):
                self.copied, self.names = copied, []
            def capture(self, name, command):
                self.names.append(name)
                if name == 'cleanup-owned':
                    self.command = command
                    return 'owned-id'
                if name == 'cleanup-state':
                    return '[{"State":{"Running":false}}]'
                if name.startswith('cleanup-vm-stop'):
                    return '{"name":"ipc","status":"Stopped"}'
                raise AssertionError(name)
            def call(self, name, command, **kwargs):
                self.names.append(name)
                if name == 'cleanup-remove':
                    raise RuntimeError('remove failed')
                if name == 'cleanup-export':
                    return dict(status='failed')
                raise AssertionError(name)
        for copied in (True, False):
            runner = Fake(copied)
            state = cleanup(runner, 'colima', 'docker', 'unique-token', copied, True)
            self.assertTrue(state['errors'])
            self.assertEqual(state['vm'], 'stopped')
            self.assertIn('label=tiny-ipc.validation.run=unique-token', runner.command)
            if not copied:
                self.assertEqual(state['container'], 'retained')
                self.assertNotIn('cleanup-remove', runner.names)

    def test_hashed_but_semantically_invalid_benchmark_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            benchmark = directory / 'benchmark'
            benchmark.mkdir()
            save(benchmark / 'report.json', dict(schema_version=4, source_sha256='source', cases=[]))
            steps = []
            for name, _ in plan(directory, 'smoke'):
                text = 'Ran 1 test in 0.1s\n\nOK\n' if name in ('tests', 'optimized') else ('Detected: fault\n'*10 if name == 'mutations' else '')
                log = directory / (name + '.log')
                log.write_text(text)
                step = dict(name=name, status='passed', exit_code=0, log=log.name, log_sha256=sha(log))
                if name in ('tests', 'optimized'):
                    step['tests_run'] = 1
                if name == 'mutations':
                    step['faults_detected'] = 10
                steps.append(step)
            report = dict(schema_version=1, status='passed', benchmark_kind='smoke', source_sha256='source', steps=steps,
                          measurement=dict(file='benchmark/report.json',sha256=sha(benchmark/'report.json'),trials=0,messages=0),
                          artifacts={str(path.relative_to(directory)):sha(path) for path in directory.rglob('*') if path.is_file()})
            save(directory / 'validation.json', report)
            with self.assertRaises((ValueError, KeyError)):
                verify_environment(directory)


    def test_duplicate_fault_lines_cannot_replace_complete_matrix(self):
        from validation_suite import behavioral_faults
        with self.assertRaises(ValueError):
            behavioral_faults('Detected: duplicated\n' * 10)


    def test_installed_lima_bytes_checked_not_just_version(self):
        import io
        import tarfile
        from install_colima import verified_lima_files
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            archive = directory / 'lima.tar.gz'
            content = b'official pinned binary'
            with tarfile.open(archive, 'w:gz') as stream:
                item = tarfile.TarInfo('bin/limactl')
                item.size = len(content)
                stream.addfile(item, io.BytesIO(content))
            root = directory / 'installed'
            (root / 'bin').mkdir(parents=True)
            (root / 'bin/limactl').write_bytes(content)
            self.assertTrue(verified_lima_files(archive, root))
            (root / 'bin/limactl').write_bytes(b'same-version altered binary')
            self.assertFalse(verified_lima_files(archive, root))


    def test_html_distinguishes_vm_rss_and_escapes_metadata(self):
        from validation_report import render
        report = dict(cases=[], profiles=[], host=dict(os='Linux', machine='<script>', python='3.12'))
        text = render(dict(benchmark_kind='full', source_sha256='source'), [report, report])
        self.assertIn('Native macOS', text)
        self.assertIn('Linux inside Colima VM', text)
        self.assertIn('Whole-VM host memory was not measured', text)
        self.assertIn('can double-count shared pages', text)
        self.assertIn('&lt;script&gt;', text)
        self.assertNotIn('<script>', text)
