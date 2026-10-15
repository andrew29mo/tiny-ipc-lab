"""Bounded SPSC loans. Only a matching sequence/slot/generation/CRC ACK frees a slot."""

from collections import deque
from dataclasses import dataclass
import struct
import time

import numpy as np

from .protocol import ProtocolError, WARMUP, arrays, crc, fill

PUBLICATION = struct.Struct("!QQQQ")  # sequence, slot, generation, payload bytes
RELEASE = struct.Struct("!QQQI")


@dataclass(frozen=True)
class Loan:
    sequence: int
    slot: int
    generation: int


def check_capacity(capacity):
    if type(capacity) is not int or not 1 <= capacity <= 16:
        raise ValueError("Pool capacity must be 1..16")


class PoolSender:
    def __init__(self, connection, payload_bytes, capacity, block=None):
        check_capacity(capacity)
        self.connection, self.payload_bytes, self.capacity = connection, payload_bytes, capacity
        self.shared = block is not None
        self.views = (np.ndarray((capacity, payload_bytes // 4), dtype=np.float32, buffer=block.buf)
                      if self.shared else np.empty((capacity, payload_bytes // 4), dtype=np.float32))
        self.free = deque(range(capacity))
        self.generations = [0] * capacity
        self.loan = None
        self.pending = deque()
        self.next_sequence = 0
        self.completed = []

    def acknowledge(self):
        if not self.pending:
            raise ProtocolError("No published loan to release")
        if not self.connection.poll(10):
            raise ProtocolError("Release timed out")
        raw = self.connection.recv_bytes(RELEASE.size)
        record = self.pending[0]
        expected = (record["sequence"], record["slot"], record["generation"], record["input_crc32"])
        if len(raw) != RELEASE.size or RELEASE.unpack(raw) != expected:
            raise ProtocolError("Stale, out-of-order or corrupt release")
        record["end_s"] = time.perf_counter()
        record["ack_crc32"] = expected[3]
        self.pending.popleft()
        self.free.append(record["slot"])
        self.completed.append(record)

    def acquire(self, sequence):
        if sequence != self.next_sequence or self.loan is not None:
            raise ProtocolError("Unexpected sequence or unpublished loan")
        start = time.perf_counter()
        blocked = not self.free
        if blocked:
            self.acknowledge()  # Backpressure: no overwrite, allocation, drop or unbounded queue.
        acquired = time.perf_counter()
        slot = self.free.popleft()
        self.generations[slot] += 1
        self.loan = Loan(sequence, slot, self.generations[slot])
        self.loan_record = {"sequence": sequence, "slot": slot, "generation": self.generations[slot],
                            "start_s": start, "acquired_s": acquired,
                            "waited_for_capacity": blocked,
                            "acquire_wait_s": acquired - start if blocked else 0.}
        self.loan_view = self.views[slot]
        return self.loan, self.loan_view

    def publish(self, loan, checksum):
        if loan != self.loan or loan is None:
            raise ProtocolError("Publish does not own the current loan")
        self.loan_view.setflags(write=False)  # Revoke this borrowed view at publication; not OS isolation.
        self.connection.send_bytes(PUBLICATION.pack(loan.sequence, loan.slot, loan.generation, self.payload_bytes))
        if not self.shared:
            self.connection.send_bytes(self.views[loan.slot])
        self.loan_record.update(published_s=time.perf_counter(), input_crc32=checksum)
        self.pending.append(self.loan_record)
        self.loan = None
        self.loan_view = None
        self.next_sequence += 1

    def drain(self):
        if self.loan is not None:
            raise ProtocolError("Cannot drain an unpublished loan")
        while self.pending:
            self.acknowledge()
        result, self.completed = self.completed, []
        return result


class PoolReceiver:
    def __init__(self, connection, payload_bytes, capacity, block=None, pipe_receive="bytes", consumer_delay_s=0.):
        check_capacity(capacity)
        if pipe_receive not in ("bytes", "into"):
            raise ValueError("Unknown Pipe receive API")
        self.connection, self.payload_bytes, self.capacity = connection, payload_bytes, capacity
        self.pipe_receive = pipe_receive
        self.consumer_delay_s = consumer_delay_s
        self.base, self.expected = arrays(payload_bytes)
        self.views = (np.ndarray((capacity, payload_bytes // 4), dtype=np.float32, buffer=block.buf)
                      if block is not None else None)
        if self.views is not None:
            self.views.setflags(write=False)
        self.target = np.empty_like(self.base) if block is None else None
        self.generations = [0] * capacity
        self.next_sequence = 0

    def receive(self, sequence):
        if sequence != self.next_sequence:
            raise ProtocolError("Unexpected consumer sequence")
        if not self.connection.poll(10):
            raise ProtocolError("Publication timed out")
        raw = self.connection.recv_bytes(PUBLICATION.size)
        slot = sequence % self.capacity
        generation = self.generations[slot] + 1
        if len(raw) != PUBLICATION.size or PUBLICATION.unpack(raw) != (sequence, slot, generation, self.payload_bytes):
            raise ProtocolError("Stale, reordered or invalid publication")
        if self.views is None:
            if self.pipe_receive == "into":
                if self.connection.recv_bytes_into(self.target) != self.payload_bytes:
                    raise ProtocolError("Short windowed Pipe payload")
            else:
                payload = self.connection.recv_bytes(self.payload_bytes)
                if len(payload) != self.payload_bytes:
                    raise ProtocolError("Short windowed Pipe payload")
                np.copyto(self.target, np.frombuffer(payload, dtype=np.float32))
                del payload
            view = self.target
        else:
            view = self.views[slot]
        fill(self.base, self.expected, sequence)
        if not np.array_equal(view, self.expected):
            raise ProtocolError("Loaned tensor content differs")
        checksum = crc(view)
        if sequence >= WARMUP and self.consumer_delay_s:
            time.sleep(self.consumer_delay_s)
        self.connection.send_bytes(RELEASE.pack(sequence, slot, generation, checksum))
        self.generations[slot] = generation
        self.next_sequence += 1
        return checksum, slot, generation
