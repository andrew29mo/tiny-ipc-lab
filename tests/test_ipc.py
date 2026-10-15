import copy
from contextlib import contextmanager
import multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
import psutil

from tiny_ipc_lab import experiment
from tiny_ipc_lab.experiment import run_trial, TrialFailure
from tiny_ipc_lab.protocol import Sender, Receiver, HEADER, ACK, ProtocolError, arrays, fill, crc
from tiny_ipc_lab.report import summarize


@contextmanager
def transport(mode, size=64):
    left, right = mp.get_context("spawn").Pipe()
    block = SharedMemory(create=True, size=size) if mode == "shared" else None
    sender, receiver = Sender(left, mode, size, block), Receiver(right, mode, size, block)
    try:
        yield left, right, block, sender, receiver
    finally:
        sender.view = receiver.view = None
        left.close()
        right.close()
        if block is not None:
            block.close()
            block.unlink()


class ProtocolTests(unittest.TestCase):
    def test_ack_is_required_before_buffer_reuse_and_every_generation_changes(self):
        for mode in ("pipe", "shared"):
            with self.subTest(mode=mode), transport(mode) as (_, right, _, sender, receiver):
                base, frame = arrays(64)
                errors = []
                for sequence in range(3):
                    fill(base, frame, sequence)
                    expected = frame.copy()
                    def send():
                        try:
                            sender.exchange(sequence, frame, crc(frame))
                        except Exception as error:
                            errors.append(error)
                    thread = threading.Thread(target=send)
                    thread.start()
                    self.assertTrue(right.poll(2))
                    self.assertEqual(HEADER.unpack(right.recv_bytes()), (sequence, 64))
                    if mode == "pipe":
                        self.assertEqual(right.recv_bytes_into(receiver.view), 64)
                    np.testing.assert_array_equal(receiver.view, expected)
                    thread.join(.02)
                    self.assertTrue(thread.is_alive(), "Sender returned ownership before ACK")
                    right.send_bytes(ACK.pack(sequence, crc(expected)))
                    thread.join(2)
                    self.assertFalse(thread.is_alive())
                    self.assertEqual(errors, [])

    def test_receiver_rejects_skipped_repeated_or_wrong_length_headers(self):
        for mode in ("pipe", "shared"):
            for header in ((1, 64), (0, 60)):
                with self.subTest(mode=mode, header=header), transport(mode) as (left, _, _, _, receiver):
                    left.send_bytes(HEADER.pack(*header))
                    with self.assertRaises(ProtocolError):
                        receiver.receive(0)
            with transport(mode) as (left, _, _, _, receiver):
                left.send_bytes(HEADER.pack(0, 64))
                with self.assertRaises(ProtocolError):
                    receiver.receive(1)  # A repeated sequence after the first generation.

    def test_receiver_checks_middle_values_and_stale_shared_generation(self):
        for mode in ("pipe", "shared"):
            with self.subTest(mode=mode), transport(mode) as (left, _, block, _, receiver):
                frame = np.arange(16, dtype=np.float32)
                frame[8] = -999  # First/last elements still match; CRC is not the oracle.
                if mode == "shared":
                    np.copyto(receiver.view, frame)
                left.send_bytes(HEADER.pack(0, 64))
                if mode == "pipe":
                    left.send_bytes(frame)
                with self.assertRaises(ProtocolError):
                    receiver.receive(0)
        with transport("shared") as (left, _, _, _, receiver):
            receiver.view[:] = np.arange(16, dtype=np.float32)
            left.send_bytes(HEADER.pack(1, 64))  # Header advanced, payload did not.
            with self.assertRaises(ProtocolError):
                receiver.receive(1)

    def test_sender_rejects_wrong_ack_sequence_or_crc(self):
        for mode in ("pipe", "shared"):
            for sequence, checksum in ((1, 0), (0, 0)):
                with self.subTest(mode=mode, sequence=sequence), transport(mode) as (_, right, _, sender, _):
                    frame = np.arange(16, dtype=np.float32)
                    right.send_bytes(ACK.pack(sequence, checksum))
                    with self.assertRaises(ProtocolError):
                        sender.exchange(0, frame, crc(frame))

    def test_short_pipe_payload_is_not_completed_using_stale_buffer_bytes(self):
        with transport("pipe") as (left, _, _, _, receiver):
            left.send_bytes(HEADER.pack(0, 64))
            left.send_bytes(np.arange(2, dtype=np.float32))
            with self.assertRaises(ProtocolError):
                receiver.receive(0)


class ProcessTests(unittest.TestCase):
    def test_actual_spawn_workers_check_all_rows_and_cleanup_after_reuse(self):
        names = []
        def tracked(*args, **kwargs):
            block = SharedMemory(*args, **kwargs)
            if kwargs.get("create"):
                names.append(block.name)
            return block
        with patch.object(experiment, "SharedMemory", side_effect=tracked):
            for mode in ("pipe", "shared"):
                for size in (64, 65536):
                    run = run_trial(mode, size, 17)
                    result = summarize(run)
                    self.assertEqual(result["verified_messages"], 17)
                    self.assertEqual(result["verified_payload_bytes"], 17 * size)
                    self.assertEqual([r["sequence"] for r in run["consumer"]["records"]], list(range(8, 25)))
                    self.assertTrue(run["cleanup"]["all_workers_exited"])
                    self.assertEqual(run["cleanup"]["exitcodes"], [0, 0])
        self.assertEqual(len(names), 2)
        for name in names:
            with self.assertRaises(FileNotFoundError):
                SharedMemory(name=name)

    def test_real_worker_crashes_do_not_leave_peers_or_shared_segments(self):
        for victim in (0, 1):
            names = []
            def tracked(*args, **kwargs):
                block = SharedMemory(*args, **kwargs)
                if kwargs.get("create"):
                    names.append(block.name)
                return block
            def kill(*workers):
                workers[victim].kill()
                workers[victim].join(2)
            with self.subTest(victim=victim), patch.object(experiment, "SharedMemory", side_effect=tracked):
                with self.assertRaises(TrialFailure) as caught:
                    run_trial("shared", 4096, 17, _on_warm=kill)
                self.assertTrue(caught.exception.cleanup["all_workers_exited"])
                self.assertTrue(caught.exception.cleanup["segment_unlinked"])
            self.assertEqual(len(names), 1)
            with self.assertRaises(FileNotFoundError):
                SharedMemory(name=names[0])

    def test_invalid_configuration_does_not_start_children(self):
        for args in (("bad", 64, 1), ("shared", 3, 1), ("pipe", 64, 0), ("pipe", True, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                run_trial(*args)

    def test_stalled_real_consumer_hits_trial_deadline_and_is_reaped(self):
        names = []
        stopped = []
        def tracked(*args, **kwargs):
            block = SharedMemory(*args, **kwargs)
            if kwargs.get("create"):
                names.append(block.name)
            return block
        def stop(producer, consumer):
            psutil.Process(consumer.pid).suspend()
            stopped.append(consumer.pid)
        before = time.monotonic()
        with patch.object(experiment, "SharedMemory", side_effect=tracked):
            with self.assertRaises(TrialFailure) as caught:
                run_trial("shared", 4096, 17, timeout=5, _on_warm=stop)
        self.assertIn("TimeoutError", str(caught.exception))
        self.assertEqual(len(stopped), 1)
        self.assertLess(time.monotonic() - before, 12)
        self.assertTrue(caught.exception.cleanup["all_workers_exited"])
        self.assertTrue(caught.exception.cleanup["segment_unlinked"])
        self.assertTrue(caught.exception.cleanup["forced_termination"])
        self.assertEqual(len(names), 1)
        with self.assertRaises(FileNotFoundError):
            SharedMemory(name=names[0])


if __name__ == "__main__":
    unittest.main()
