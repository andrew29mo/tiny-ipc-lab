import copy
import gzip
from functools import partial
import hashlib
import json
import multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
import psutil

from tiny_ipc_lab import experiment
from tiny_ipc_lab.experiment import run_trial, TrialFailure
from tiny_ipc_lab.pool import PoolSender, PoolReceiver, PUBLICATION, RELEASE, Loan
from tiny_ipc_lab.pool_bench import benchmark, verify, overview, render, block_order
from tiny_ipc_lab.protocol import ProtocolError, crc, fill, WARMUP
from tiny_ipc_lab.report import summarize


class PoolProtocolTests(unittest.TestCase):
    def setUp(self):
        self.left, self.right = mp.Pipe()
        self.block = SharedMemory(create=True, size=64 * 2)
        self.sender = PoolSender(self.left, 64, 2, self.block)
        self.receiver = PoolReceiver(self.right, 64, 2, self.block)

    def tearDown(self):
        self.sender.views = self.sender.loan_view = None
        self.receiver.views = None
        self.left.close()
        self.right.close()
        self.block.close()
        self.block.unlink()

    def publish(self, sequence):
        loan, view = self.sender.acquire(sequence)
        fill(np.arange(16, dtype=np.float32), view, sequence)
        self.sender.publish(loan, crc(view))
        return loan, view

    def test_direct_write_ownership_and_revoke_view_after_publish(self):
        loan, view = self.sender.acquire(0)
        self.assertTrue(np.shares_memory(view, self.sender.views))
        with self.assertRaises(ProtocolError):
            self.sender.acquire(0)
        fill(np.arange(16, dtype=np.float32), view, 0)
        with self.assertRaises(ProtocolError):
            self.sender.publish(Loan(0, 0, 99), crc(view))
        self.sender.publish(loan, crc(view))
        self.assertFalse(view.flags.writeable)
        with self.assertRaises(ValueError):
            view[0] = 100
        with self.assertRaises(ProtocolError):
            self.sender.publish(loan, 0)
        self.assertFalse(self.receiver.views.flags.writeable)
        self.assertEqual(self.receiver.receive(0), (crc(view), 0, 1))
        self.sender.drain()

    def test_full_pool_blocks_until_consumer_ack_and_then_reuses_generation(self):
        _, first = self.publish(0)
        self.publish(1)
        entered, returned = threading.Event(), threading.Event()
        result = []
        def acquire():
            entered.set()
            result.append(self.sender.acquire(2))
            returned.set()
        thread = threading.Thread(target=acquire)
        thread.start()
        self.assertTrue(entered.wait(1))
        try:
            self.assertFalse(returned.wait(.06))
            np.testing.assert_array_equal(self.receiver.views[0], np.arange(16, dtype=np.float32))
            self.assertEqual(len(self.sender.pending), 2)
            self.receiver.receive(0)
            self.assertTrue(returned.wait(1))
            loan, view = result.pop()
            self.assertEqual(loan, Loan(2, 0, 2))
            self.assertTrue(np.shares_memory(first, view))
            self.assertTrue(view.flags.writeable)
            fill(np.arange(16, dtype=np.float32), view, 2)
            self.sender.publish(loan, crc(view))
            self.receiver.receive(1)
            self.receiver.receive(2)
            records = self.sender.drain()
            self.assertEqual([r['sequence'] for r in records], [0, 1, 2])
            self.assertTrue(records[2]['waited_for_capacity'])
            self.assertGreaterEqual(records[2]['acquire_wait_s'], .05)
        finally:
            # Always release a waiting test thread if an assertion catches a source fault.
            if thread.is_alive():
                self.right.send_bytes(RELEASE.pack(0, 0, 1, crc(np.arange(16, dtype=np.float32))))
            thread.join(2)
            result.clear()

    def test_stale_release_cannot_free_current_generation(self):
        old, _ = self.publish(0)
        self.receiver.receive(0)
        self.sender.acknowledge()
        self.publish(1)
        self.receiver.receive(1)
        self.sender.acknowledge()
        loan, view = self.publish(2)
        # Correct current sequence/CRC, but stale generation of the same reused slot.
        self.right.send_bytes(RELEASE.pack(loan.sequence, loan.slot, old.generation, crc(view)))
        with self.assertRaises(ProtocolError):
            self.sender.acknowledge()
        self.assertEqual(len(self.sender.pending), 1)
        self.assertNotIn(loan.slot, self.sender.free)

    def test_invalid_release_fields_and_duplicate_do_not_return_ownership(self):
        loan, view = self.publish(0)
        checksum = crc(view)
        invalid = [RELEASE.pack(1, 0, 1, checksum), RELEASE.pack(0, 1, 1, checksum),
                   RELEASE.pack(0, 0, 2, checksum), RELEASE.pack(0, 0, 1, checksum ^ 1), b'short']
        for raw in invalid:
            self.right.send_bytes(raw)
            with self.assertRaises(ProtocolError):
                self.sender.acknowledge()
            self.assertEqual(list(self.sender.free), [1])
            self.assertEqual(self.sender.pending[0]['sequence'], 0)
        self.receiver.receive(0)
        self.sender.acknowledge()
        self.right.send_bytes(RELEASE.pack(0, 0, 1, checksum))
        self.publish(1)
        with self.assertRaises(ProtocolError):
            self.sender.acknowledge()
        self.assertEqual(self.sender.pending[0]['sequence'], 1)
        self.assertNotIn(1, self.sender.free)
        self.receiver.receive(1)
        self.sender.drain()

    def test_invalid_publication_fields_do_not_ack_or_advance(self):
        self.sender.views[0][:] = np.arange(16, dtype=np.float32)
        for raw in [PUBLICATION.pack(1, 0, 1, 64), PUBLICATION.pack(0, 1, 1, 64),
                    PUBLICATION.pack(0, 0, 2, 64), PUBLICATION.pack(0, 0, 1, 60), b'short']:
            self.left.send_bytes(raw)
            with self.assertRaises(ProtocolError):
                self.receiver.receive(0)
            self.assertEqual(self.receiver.next_sequence, 0)
            self.assertFalse(self.left.poll(.005))
        self.publish(0)
        self.receiver.receive(0)
        self.sender.drain()

    def test_receiver_rejects_stale_generation_and_middle_value_corruption(self):
        self.sender.views[0][:] = np.arange(16, dtype=np.float32)
        self.left.send_bytes(PUBLICATION.pack(0, 0, 0, 64))
        with self.assertRaises(ProtocolError):
            self.receiver.receive(0)
        loan, view = self.sender.acquire(0)
        fill(np.arange(16, dtype=np.float32), view, 0)
        view[8] = -99
        self.sender.publish(loan, crc(view))
        with self.assertRaises(ProtocolError):
            self.receiver.receive(0)
        self.assertFalse(self.left.poll(.03))  # Invalid contents must not release ownership.


real_producer = experiment.producer


def marked_producer(*args, marker):
    original_publish = experiment.PoolSender.publish
    def publish(sender, loan, checksum):
        original_publish(sender, loan, checksum)
        if loan.sequence == WARMUP + 3:
            Path(marker).write_text('four-measured-loans-published')
    experiment.PoolSender.publish = publish
    real_producer(*args)


def audited_inplace_producer(*args, marker):
    original_init, original_fill = experiment.PoolSender.__init__, experiment.fill
    observed, calls = [], []
    def initialize(sender, *values, **kwargs):
        original_init(sender, *values, **kwargs)
        observed.append(sender)
    def generate(base, target, sequence):
        sender = observed[0]
        if not sender.shared or not np.shares_memory(target, sender.views[sender.loan.slot]):
            raise RuntimeError('Production generation is not writing into the owned shared slot')
        original_fill(base, target, sequence)
        calls.append(sequence)
    experiment.PoolSender.__init__, experiment.fill = initialize, generate
    real_producer(*args)
    Path(marker).write_text(json.dumps(calls))


class PoolProcessTests(unittest.TestCase):
    def test_production_worker_generates_directly_into_owned_shared_slots(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / 'actual-generation-destinations'
            with patch.object(experiment, 'producer', partial(audited_inplace_producer, marker=str(marker))):
                try:
                    run = run_trial('pool', 65536, 17, capacity=3, pipe_receive='bytes')
                except TrialFailure as error:
                    self.fail('Production direct-write contract failed: ' + str(error))
            self.assertEqual(json.loads(marker.read_text()), list(range(25)))
            self.assertEqual(summarize(run)['verified_messages'], 17)

    def test_small_exact_and_partial_windows_in_actual_processes(self):
        for capacity, count in [(16, 1), (4, 4), (4, 5)]:
            for mode in ['pool', 'window_pipe']:
                with self.subTest(mode=mode, capacity=capacity, count=count):
                    run = run_trial(mode, 64, count, capacity=capacity, pipe_receive='bytes')
                    summary = summarize(run)
                    self.assertEqual(summary['verified_messages'], count)
                    self.assertEqual(summary['peak_owned_slots'], min(count, capacity))
                    self.assertEqual(len(run['producer']['records']), count)

    def test_pool_segment_is_unlinked_if_later_pipe_allocation_fails(self):
        names = []
        real = experiment.SharedMemory
        def tracked(*args, **kwargs):
            block = real(*args, **kwargs)
            if kwargs.get('create'):
                names.append(block.name)
            return block
        with patch.object(experiment, 'SharedMemory', side_effect=tracked), patch.object(mp.get_context('spawn'), 'Pipe', side_effect=OSError('injected allocation failure')):
            with self.assertRaises(TrialFailure) as caught:
                run_trial('pool', 64, 3, capacity=4)
        self.assertTrue(caught.exception.cleanup['segment_unlinked'])
        with self.assertRaises(FileNotFoundError):
            SharedMemory(name=names[0])

    def test_actual_tail_windows_and_slow_consumer_all_profiles(self):
        for mode, capacity in [('pipe', 1), ('shared', 1), ('pool', 1), ('pool', 3), ('window_pipe', 3)]:
            with self.subTest(mode=mode, capacity=capacity):
                run = run_trial(mode, 16384, 17, pipe_receive='bytes', capacity=capacity, consumer_delay_s=.001)
                summary = summarize(run)
                self.assertEqual(summary['verified_messages'], 17)
                self.assertEqual([r['sequence'] for r in run['producer']['records']], list(range(8, 25)))
                self.assertGreaterEqual(summary['duration_s'], .017)
                if mode in ('pool', 'window_pipe'):
                    self.assertEqual(summary['peak_owned_slots'], capacity)
                    self.assertEqual(summary['capacity_wait_count'], 17 - capacity)
                    for row in run['producer']['records']:
                        self.assertEqual(row['slot'], row['sequence'] % capacity)
                        self.assertEqual(row['generation'], row['sequence'] // capacity + 1)

    def test_workers_crashing_with_live_loans_reap_peers_and_unlink(self):
        for victim in (0, 1):
            with self.subTest(victim=victim), tempfile.TemporaryDirectory() as temp:
                marker = Path(temp) / 'published-full-window'
                names, threads = [], []
                real = experiment.SharedMemory
                def tracked(*args, **kwargs):
                    block = real(*args, **kwargs)
                    if kwargs.get('create'):
                        names.append(block.name)
                    return block
                def crash(*workers):
                    psutil.Process(workers[1].pid).suspend()
                    def wait_then_kill():
                        deadline = time.monotonic() + 1.
                        while not marker.exists() and time.monotonic() < deadline:
                            time.sleep(.002)
                        if marker.exists():
                            workers[victim].kill()
                    thread = threading.Thread(target=wait_then_kill)
                    threads.append(thread)
                    thread.start()
                with patch.object(experiment, 'SharedMemory', side_effect=tracked), patch.object(experiment, 'producer', partial(marked_producer, marker=str(marker))):
                    with self.assertRaises(TrialFailure) as caught:
                        run_trial('pool', 65536, 17, capacity=4, timeout=3., _on_warm=crash)
                    for thread in threads:
                        thread.join(2)
                self.assertEqual(marker.read_text(), 'four-measured-loans-published')
                self.assertTrue(caught.exception.cleanup['all_workers_exited'])
                self.assertTrue(caught.exception.cleanup['control_readers_exited'])
                self.assertTrue(caught.exception.cleanup['segment_unlinked'])
                with self.assertRaises(FileNotFoundError):
                    SharedMemory(name=names[0])

    def test_pool_timeout_and_descriptor_cleanup(self):
        run_trial('pool', 64, 1, capacity=4)
        before = psutil.Process().num_fds()
        for _ in range(3):
            run_trial('pool', 64, 5, capacity=4)
        self.assertLessEqual(psutil.Process().num_fds(), before + 1)
        def stall(*workers):
            psutil.Process(workers[1].pid).suspend()
        with self.assertRaises(TrialFailure) as caught:
            run_trial('pool', 4096, 17, capacity=4, timeout=1.5, _on_warm=stall)
        self.assertIn('TimeoutError', str(caught.exception))
        self.assertTrue(caught.exception.cleanup['segment_unlinked'])
        self.assertTrue(caught.exception.cleanup['all_workers_exited'])


class PoolMetricsTests(unittest.TestCase):
    def fixture(self):
        rows, received = [], []
        for sequence, start, acquired, published, end in [(8, 1., 1., 1.001, 1.006), (9, 1.002, 1.002, 1.003, 1.008), (10, 1.004, 1.007, 1.008, 1.011)]:
            checksum = crc(np.array([sequence], dtype=np.float32))
            rows.append(dict(sequence=sequence, slot=sequence % 2, generation=sequence // 2 + 1,
                             start_s=start, acquired_s=acquired, published_s=published, end_s=end,
                             input_crc32=checksum, ack_crc32=checksum, waited_for_capacity=sequence == 10,
                             acquire_wait_s=acquired - start if sequence == 10 else 0.))
            ready = {8: 1.005, 9: 1.007, 10: 1.010}[sequence]
            received.append(dict(sequence=sequence, slot=sequence % 2, generation=sequence // 2 + 1,
                                 crc32=checksum, verified_elements=1, ready_s=ready, delay_start_s=ready-.0005))
        run = dict(mode='pool', capacity=2, payload_bytes=4, count=3, warmup=8, pipe_receive='bytes', timing_version=2, consumer_delay_s=0.,
                   producer=dict(event='done', start_s=1., end_s=1.012, cpu_s=.001, high_water_rss_bytes=100, records=rows),
                   consumer=dict(event='done', end_s=1.013, cpu_s=.002, high_water_rss_bytes=200, records=received),
                   memory_window=dict(start_s=.99, end_s=1.02),
                   rss_samples=[dict(start_s=.991, end_s=.992, producer_rss_bytes=100, consumer_rss_bytes=10),
                                dict(start_s=1.014, end_s=1.015, producer_rss_bytes=10, consumer_rss_bytes=100)],
                   cleanup=dict(exitcodes=[0, 0], forced_termination=False, all_workers_exited=True,
                                control_readers_exited=True, segment_unlinked=True))
        return run

    def test_hand_calculated_overlap_capacity_wait_and_tail_duration(self):
        summary = summarize(self.fixture())
        self.assertAlmostEqual(summary['duration_s'], .013)
        self.assertAlmostEqual(summary['messages_per_s'], 3/.013)
        self.assertAlmostEqual(summary['round_trip_ms']['p50'], 6.)
        self.assertAlmostEqual(summary['round_trip_ms']['p95'], 6.9)
        self.assertEqual(summary['peak_owned_slots'], 2)
        self.assertEqual(summary['capacity_wait_count'], 1)
        self.assertAlmostEqual(summary['capacity_wait_s'], .003)
        self.assertAlmostEqual(summary['admitted_to_ready_ms']['p50'], 5.)
        self.assertAlmostEqual(summary['admitted_to_ready_ms']['p95'], 5.)
        self.assertAlmostEqual(summary['attempt_to_ready_ms']['p95'], 5.9)
        self.assertAlmostEqual(summary['ack_observation_lag_ms']['p95'], 1.)
        self.assertAlmostEqual(summary['admission_wait_ms']['p95'], 2.7)
        self.assertEqual(summary['slot_bytes'], 8)
        self.assertEqual(summary['peak_paired_rss_bytes'], 110)

    def test_rejects_fifo_ack_reordering_and_impossible_consumer_timing(self):
        for fault in [lambda r: r.update(timing_version=1),
                      lambda r: r['producer']['records'][1].update(end_s=1.005),
                      lambda r: r['consumer']['records'][0].update(ready_s=1.007),
                      lambda r: r['consumer']['records'][1].update(delay_start_s=1.001),
                      lambda r: r.update(consumer_delay_s=.001)]:
            run = self.fixture()
            fault(run)
            with self.assertRaises(ValueError):
                summarize(run)


class PoolEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name) / 'evidence'
        cls.report = benchmark(cls.directory, sizes=[64], blocks=2, capacity=3, smoke=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_production_reports_reconcile_and_all_profiles_same_work(self):
        verify(self.report, self.directory)
        self.assertEqual((self.directory / 'report.html').read_text(), render(self.report))
        self.assertEqual((self.directory / 'README.md').read_text(), overview(self.report))
        self.assertFalse((self.directory / 'partial.json').exists())
        self.assertEqual(sum(s['summary']['verified_messages'] for c in self.report['cases'] for s in c['runs']), 340)
        self.assertEqual([block_order(i)[0] for i in range(5)], ['pipe', 'shared', 'pool_1', 'pool_n', 'window_pipe'])

    def test_forged_metrics_policy_and_missing_trials_are_rejected(self):
        for fault in [lambda r:r['cases'][0]['runs'].pop(), lambda r:r['comparisons'][0].update(median=99.),
                      lambda r:r['cases'][0].update(consumer_delay_s=.002), lambda r:r.update(pool_capacity=4), lambda r:r.update(schema_version=3),
                      lambda r:r['cases'][0]['runs'][0].update(file='../report.json')]:
            report = copy.deepcopy(self.report)
            fault(report)
            with self.assertRaises(ValueError):
                verify(report, self.directory)

    def test_failed_trial_retains_partial_index_and_cleanup_without_final_report(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'failed'
            with patch('tiny_ipc_lab.pool_bench.run_trial', side_effect=TrialFailure('injected', {'segment_unlinked': True})):
                with self.assertRaises(TrialFailure):
                    benchmark(directory, sizes=[64], blocks=1, capacity=3, smoke=True)
            partial = json.loads((directory / 'partial.json').read_text())
            failure = json.loads((directory / 'failure.json').read_text())
            self.assertEqual(partial['cases'][0]['runs'], [])
            self.assertEqual(failure['profile'], 'pipe')
            self.assertTrue(failure['cleanup']['segment_unlinked'])
            self.assertFalse((directory / 'report.json').exists())

    def test_independent_oracle_rejects_forged_crc_and_illegal_reuse(self):
        stub = next(s for s in self.report['cases'][0]['runs'] if s['profile'] == 'pool_n')
        run = json.loads(gzip.decompress((self.directory / stub['file']).read_bytes()))
        for fault in [lambda r:r['producer']['records'][0].update(generation=0),
                      lambda r:r['producer']['records'][3].update(acquired_s=r['producer']['records'][0]['start_s']),
                      lambda r:r['producer']['records'][-1].update(end_s=r['producer']['records'][-1]['start_s'])]:
            bad = copy.deepcopy(run)
            fault(bad)
            with self.assertRaises(ValueError):
                summarize(bad)
        for row in run['producer']['records']:
            row['input_crc32'] = row['ack_crc32'] = 0
        for row in run['consumer']['records']:
            row['crc32'] = 0
        summarize(run, check_values=False)
        with self.assertRaises(ValueError):
            summarize(run)


if __name__ == '__main__':
    unittest.main()
