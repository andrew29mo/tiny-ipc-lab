"""Spawn two measured workers; an external controller samples and owns cleanup."""

import hashlib
import json
import multiprocessing as mp
import multiprocessing.connection as mp_connection
from multiprocessing.shared_memory import SharedMemory
import os
from pathlib import Path
import platform
from queue import Empty, Queue
import resource
import sys
from threading import Thread
import time

import numpy as np
import psutil

from .protocol import Sender, Receiver, WARMUP, arrays, check_config, fill, crc
from .pool import PoolSender, PoolReceiver, check_capacity


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def source_hash():
    return fingerprint({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(Path(__file__).parent.glob("*.py"))})


def highwater():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def producer(data, control, mode, payload_bytes, count, name, pipe_receive, capacity=1, consumer_delay_s=0.):
    block = sender = None
    try:
        block = SharedMemory(name=name) if name else None
        streaming = mode in ("pool", "window_pipe")
        base, frame = arrays(payload_bytes) if not streaming else (np.arange(payload_bytes // 4, dtype=np.float32), None)
        sender = PoolSender(data, payload_bytes, capacity, block) if streaming else Sender(data, mode, payload_bytes, block)
        control.send({"event": "ready"})
        if control.recv() != "warmup":
            raise RuntimeError("Expected warmup command")
        for seq in range(WARMUP):
            if streaming:
                loan, target = sender.acquire(seq)
                fill(base, target, seq)
                sender.publish(loan, crc(target))
                del target
            else:
                fill(base, frame, seq)
                sender.exchange(seq, frame, crc(frame))
        if streaming:
            sender.drain()
        control.send({"event": "warm"})
        if control.recv() != "start":
            raise RuntimeError("Expected start command")
        records = []
        cpu_start = time.process_time()
        start = time.perf_counter()
        for seq in range(WARMUP, WARMUP + count):
            if streaming:
                loan, target = sender.acquire(seq)
                fill(base, target, seq)  # Direct write into the owned slot; no staging frame/copy.
                sender.publish(loan, crc(target))
                del target
                continue
            before = time.perf_counter()
            fill(base, frame, seq)
            expected_crc = crc(frame)
            actual_crc = sender.exchange(seq, frame, expected_crc)
            after = time.perf_counter()
            records.append({"sequence": seq, "start_s": before, "end_s": after,
                            "input_crc32": expected_crc, "ack_crc32": actual_crc})
        if streaming:
            records = sender.drain()
        end = time.perf_counter()
        control.send({"event": "done", "start_s": start, "end_s": end,
                      "cpu_s": time.process_time() - cpu_start, "high_water_rss_bytes": highwater(),
                      "records": records})
        if control.recv() != "close":
            raise RuntimeError("Expected close command")
    except BaseException as error:
        try:
            control.send({"event": "error", "type": type(error).__name__})
        except (OSError, EOFError):
            pass
        raise
    finally:
        if sender is not None:
            target = None
            sender.loan_view = None
            sender.view = None
            if hasattr(sender, "views"):
                sender.views = None
        if block is not None:
            block.close()
        data.close()
        control.close()


def consumer(data, control, mode, payload_bytes, count, name, pipe_receive, capacity=1, consumer_delay_s=0.):
    block = receiver = None
    try:
        block = SharedMemory(name=name) if name else None
        streaming = mode in ("pool", "window_pipe")
        receiver = PoolReceiver(data, payload_bytes, capacity, block, pipe_receive, consumer_delay_s) if streaming else Receiver(data, mode, payload_bytes, block, pipe_receive, consumer_delay_s)
        control.send({"event": "ready"})
        for seq in range(WARMUP):
            receiver.receive(seq)
        control.send({"event": "warm"})
        records = []
        cpu_start = time.process_time()
        for seq in range(WARMUP, WARMUP + count):
            value = receiver.receive(seq)
            observed_crc = value[0] if streaming else value
            row = {"sequence": seq, "crc32": observed_crc, "verified_elements": payload_bytes // 4,
                   "delay_start_s": receiver.last_delay_start_s, "ready_s": receiver.last_ready_s}
            if streaming:
                row.update(slot=value[1], generation=value[2])
            records.append(row)
        end = time.perf_counter()
        control.send({"event": "done", "end_s": end, "cpu_s": time.process_time() - cpu_start,
                      "high_water_rss_bytes": highwater(), "records": records})
        if control.recv() != "close":
            raise RuntimeError("Expected close command")
    except BaseException as error:
        try:
            control.send({"event": "error", "type": type(error).__name__})
        except (OSError, EOFError):
            pass
        raise
    finally:
        if receiver is not None:
            receiver.view = None
            if hasattr(receiver, "views"):
                receiver.views = None
        if block is not None:
            block.close()
        data.close()
        control.close()


class TrialFailure(RuntimeError):
    def __init__(self, message, cleanup):
        super().__init__(message)
        self.cleanup = cleanup


def run_trial(mode, payload_bytes, count, *, pipe_receive="into", timeout=30., _on_warm=None, capacity=1, consumer_delay_s=0.):
    check_config(mode, payload_bytes, count)
    check_capacity(capacity)
    if mode not in ("pool", "window_pipe") and capacity != 1:
        raise ValueError("Legacy stop-and-wait requires capacity=1")
    if type(consumer_delay_s) not in (int, float) or not 0 <= consumer_delay_s <= .05:
        raise ValueError("Consumer delay must be 0..0.05 seconds")
    if pipe_receive not in ("into", "bytes") or type(timeout) not in (int, float) or not 0 < timeout <= 300:
        raise ValueError("Invalid trial timeout")
    context = mp.get_context("spawn")
    block = None
    name = None
    connections, controls, child_controls, workers, readers = [], [], [], [], []
    processes, samples, result = [], [], None
    failure, forced = None, False
    cleanup = {}
    deadline = time.monotonic() + timeout
    try:
        block = SharedMemory(create=True, size=payload_bytes * capacity) if mode in ("shared", "pool") else None
        name = block.name if block else None
        left, right = context.Pipe()
        connections.extend((left, right))
        for _ in range(2):
            parent, child = context.Pipe()
            connections.extend((parent, child))
            controls.append(parent)
            child_controls.append(child)
        workers = [context.Process(target=target, args=(data, ctl, mode, payload_bytes, count, name, pipe_receive, capacity, consumer_delay_s))
                   for target, data, ctl in zip((producer, consumer), (left, right), child_controls)]
        for worker in workers:
            worker.start()
            processes.append(psutil.Process(worker.pid))
        left.close()
        right.close()
        for ctl in child_controls:
            ctl.close()
        events = Queue()
        def read_control(index, ctl):
            try:
                while True:
                    events.put((index, ctl.recv()))
            except (EOFError, OSError):
                events.put((index, {"event": "eof"}))
        for index, ctl in enumerate(controls):
            reader = Thread(target=read_control, args=(index, ctl), daemon=True)
            reader.start()
            readers.append(reader)

        def collect(event, memory=False):
            found = {}
            while len(found) < 2:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Trial deadline exceeded")
                try:
                    while True:
                        index, value = events.get_nowait()
                        if index in found or not isinstance(value, dict) or value.get("event") != event:
                            raise RuntimeError("Worker failed or unexpected lifecycle event")
                        found[index] = value
                except Empty:
                    pass
                for index, worker in enumerate(workers):
                    if index not in found and worker.exitcode is not None:
                        raise RuntimeError("Worker exited before completing the protocol")
                if memory:
                    sample()
                if len(found) < 2:
                    time.sleep(.005 if memory else .001)
            return [found[i] for i in range(2)]

        def sample():
            before = time.perf_counter()
            p, c = [process.memory_info().rss for process in processes]
            samples.append({"start_s": before, "end_s": time.perf_counter(),
                            "producer_rss_bytes": p, "consumer_rss_bytes": c})

        collect("ready")
        controls[0].send("warmup")
        collect("warm")
        if _on_warm is not None:
            _on_warm(*workers)
        window_start = time.perf_counter()
        sample()
        controls[0].send("start")
        p_result, c_result = collect("done", memory=True)
        sample()  # Both workers wait for release; this brackets the last ACK and result collection.
        window_end = time.perf_counter()
        for ctl in controls:
            ctl.send("close")
        result = {"mode": mode, "pipe_receive": pipe_receive, "payload_bytes": payload_bytes, "count": count, "warmup": WARMUP,
                  "capacity": capacity, "consumer_delay_s": consumer_delay_s, "timing_version": 2,
                  "producer": p_result, "consumer": c_result, "rss_samples": samples,
                  "memory_window": {"start_s": window_start, "end_s": window_end},
                  "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                  "psutil": psutil.__version__, "optimization": sys.flags.optimize,
                                  "connection_source_sha256": hashlib.sha256(Path(mp_connection.__file__).read_bytes()).hexdigest(),
                                  "runtime_options": {k: os.environ.get(k) for k in
                                      ("MallocLargeCache", "MallocAggressiveMadvise", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}}
    except BaseException as error:
        failure = error
    finally:
        # Only the controller owns unlink. It also cleans up after real worker crashes.
        for worker in workers:
            if worker.pid is None:
                continue
            worker.join(2 if failure is None else .05)
            if worker.is_alive():
                forced = True
                worker.terminate()
                worker.join(1)
            if worker.is_alive():
                worker.kill()
                worker.join(2)
        for reader in readers:
            reader.join(2)  # Worker death closes the peer, including a half-written control frame.
        for ctl in connections:
            ctl.close()
        unlinked = None
        if block is not None:
            block.close()
            block.unlink()
            try:
                leftover = SharedMemory(name=name)
            except FileNotFoundError:
                unlinked = True
            else:
                leftover.close()
                unlinked = False
        cleanup = {"exitcodes": [w.exitcode for w in workers], "forced_termination": forced,
                   "all_workers_exited": all(w.pid is None or not w.is_alive() for w in workers),
                   "control_readers_exited": all(not r.is_alive() for r in readers),
                   "segment_unlinked": unlinked}
        for worker in workers:
            if worker.pid is not None and not worker.is_alive():
                worker.close()  # Release each exited Process object's sentinel/OS handles as well.
    if failure is not None:
        raise TrialFailure(type(failure).__name__ + ": " + str(failure), cleanup) from failure
    if cleanup != {"exitcodes": [0, 0], "forced_termination": False, "all_workers_exited": True,
                   "control_readers_exited": True,
                   "segment_unlinked": True if mode in ("shared", "pool") else None}:
        raise TrialFailure("Unclean worker or shared-memory exit", cleanup)
    result["cleanup"] = cleanup
    return result
