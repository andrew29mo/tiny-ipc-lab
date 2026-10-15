"""Spawn two measured workers; an external controller samples and owns cleanup."""

import hashlib
import json
import multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path
import platform
import resource
import sys
import time

import numpy as np
import psutil

from .protocol import Sender, Receiver, WARMUP, arrays, check_config, fill, crc


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def source_hash():
    return fingerprint({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(Path(__file__).parent.glob("*.py"))})


def highwater():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def producer(data, control, mode, payload_bytes, count, name):
    block = sender = None
    try:
        block = SharedMemory(name=name) if name else None
        base, frame = arrays(payload_bytes)
        sender = Sender(data, mode, payload_bytes, block)
        control.send({"event": "ready"})
        if control.recv() != "warmup":
            raise RuntimeError("Expected warmup command")
        for seq in range(WARMUP):
            fill(base, frame, seq)
            sender.exchange(seq, frame, crc(frame))
        control.send({"event": "warm"})
        if control.recv() != "start":
            raise RuntimeError("Expected start command")
        records = []
        cpu_start = time.process_time()
        start = time.perf_counter()
        for seq in range(WARMUP, WARMUP + count):
            before = time.perf_counter()
            fill(base, frame, seq)
            expected_crc = crc(frame)
            actual_crc = sender.exchange(seq, frame, expected_crc)
            after = time.perf_counter()
            records.append({"sequence": seq, "start_s": before, "end_s": after,
                            "input_crc32": expected_crc, "ack_crc32": actual_crc})
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
            sender.view = None
        if block is not None:
            block.close()
        data.close()
        control.close()


def consumer(data, control, mode, payload_bytes, count, name):
    block = receiver = None
    try:
        block = SharedMemory(name=name) if name else None
        receiver = Receiver(data, mode, payload_bytes, block)
        control.send({"event": "ready"})
        for seq in range(WARMUP):
            receiver.receive(seq)
        control.send({"event": "warm"})
        records = []
        cpu_start = time.process_time()
        for seq in range(WARMUP, WARMUP + count):
            observed_crc = receiver.receive(seq)
            records.append({"sequence": seq, "crc32": observed_crc,
                            "verified_elements": payload_bytes // 4})
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
        if block is not None:
            block.close()
        data.close()
        control.close()


class TrialFailure(RuntimeError):
    def __init__(self, message, cleanup):
        super().__init__(message)
        self.cleanup = cleanup


def run_trial(mode, payload_bytes, count, *, timeout=30., _on_warm=None):
    check_config(mode, payload_bytes, count)
    if type(timeout) not in (int, float) or not 0 < timeout <= 300:
        raise ValueError("Invalid trial timeout")
    context = mp.get_context("spawn")
    block = SharedMemory(create=True, size=payload_bytes) if mode == "shared" else None
    name = block.name if block else None
    left, right = context.Pipe()
    controls, child_controls = zip(*(context.Pipe() for _ in range(2)))
    workers = [context.Process(target=target, args=(data, ctl, mode, payload_bytes, count, name))
               for target, data, ctl in zip((producer, consumer), (left, right), child_controls)]
    processes, samples, result = [], [], None
    failure, forced = None, False
    cleanup = {}
    try:
        for worker in workers:
            worker.start()
            processes.append(psutil.Process(worker.pid))
        left.close()
        right.close()
        for ctl in child_controls:
            ctl.close()
        deadline = time.monotonic() + timeout

        def collect(event, memory=False):
            found = {}
            while len(found) < 2:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Trial deadline exceeded")
                for index, ctl in enumerate(controls):
                    if index in found:
                        continue
                    if ctl.poll():
                        value = ctl.recv()
                        if value.get("event") != event:
                            raise RuntimeError("Worker failed or unexpected lifecycle event")
                        found[index] = value
                    elif workers[index].exitcode is not None:
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
        result = {"mode": mode, "payload_bytes": payload_bytes, "count": count, "warmup": WARMUP,
                  "producer": p_result, "consumer": c_result, "rss_samples": samples,
                  "memory_window": {"start_s": window_start, "end_s": window_end},
                  "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                  "psutil": psutil.__version__, "optimization": sys.flags.optimize}}
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
        for ctl in (*controls, *child_controls, left, right):
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
                   "segment_unlinked": unlinked}
        for worker in workers:
            if worker.pid is not None and not worker.is_alive():
                worker.close()  # Release each exited Process object's sentinel/OS handles as well.
    if failure is not None:
        raise TrialFailure(type(failure).__name__ + ": " + str(failure), cleanup) from failure
    if cleanup != {"exitcodes": [0, 0], "forced_termination": False, "all_workers_exited": True,
                   "segment_unlinked": True if mode == "shared" else None}:
        raise TrialFailure("Unclean worker or shared-memory exit", cleanup)
    result["cleanup"] = cleanup
    return result
