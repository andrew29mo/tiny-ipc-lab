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
