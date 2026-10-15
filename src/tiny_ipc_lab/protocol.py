"""One acknowledged payload in flight; acknowledgement returns buffer ownership."""

import struct
import zlib

import numpy as np

HEADER = struct.Struct("!QQ")  # Sequence, payload byte count. One fixed slot.
ACK = struct.Struct("!QI")  # Sequence, CRC32 of the fully checked received values.
MODES = ("pipe", "shared")
WARMUP = 8
RECIPE = "float32 arange(elements) + sequence; exact equality; seq starts at zero"


class ProtocolError(RuntimeError):
    pass


def check_config(mode, payload_bytes, count):
    if (mode not in MODES or type(payload_bytes) is not int or payload_bytes % 4
            or not 4 <= payload_bytes <= 16 * 1024 * 1024
            or type(count) is not int or not 1 <= count <= 16384):
        raise ValueError("Require pipe/shared, 4..16 MiB divisible by four, count 1..16384")


def arrays(payload_bytes):
    base = np.arange(payload_bytes // 4, dtype=np.float32)
    return base, np.empty_like(base)


def fill(base, target, sequence):
    np.add(base, sequence, out=target)


def crc(array):
    return zlib.crc32(array) & 0xffffffff


class Sender:
    def __init__(self, connection, mode, payload_bytes, block=None):
        check_config(mode, payload_bytes, 1)
        self.connection, self.mode = connection, mode
        self.view = (np.ndarray((payload_bytes // 4,), dtype=np.float32, buffer=block.buf)
                     if mode == "shared" else None)

    def exchange(self, sequence, frame, expected_crc):
        # Do not publish a header until the complete payload is written.
        if self.mode == "shared":
            np.copyto(self.view, frame)
        self.connection.send_bytes(HEADER.pack(sequence, frame.nbytes))
        if self.mode == "pipe":
            self.connection.send_bytes(frame)
        if not self.connection.poll(10):
            raise ProtocolError("Acknowledgement timed out")
        acknowledgement = self.connection.recv_bytes(ACK.size)
        if len(acknowledgement) != ACK.size:
            raise ProtocolError("Malformed acknowledgement")
        actual_sequence, actual_crc = ACK.unpack(acknowledgement)
        if actual_sequence != sequence or actual_crc != expected_crc:
            raise ProtocolError("Acknowledgement sequence/content differs")
        return actual_crc  # The single slot may only be reused after this point.


class Receiver:
    def __init__(self, connection, mode, payload_bytes, block=None, pipe_receive="into"):
        check_config(mode, payload_bytes, 1)
        if pipe_receive not in ("into", "bytes"):
            raise ValueError("Unknown Pipe receive API")
        self.pipe_receive = pipe_receive
        self.connection, self.mode, self.payload_bytes = connection, mode, payload_bytes
        self.base, self.expected = arrays(payload_bytes)
        self.view = (np.ndarray(self.base.shape, dtype=np.float32, buffer=block.buf)
                     if mode == "shared" else np.empty_like(self.base))
        if mode == "shared":
            self.view.setflags(write=False)  # Consumer API guard; not OS permission/tenant isolation.

    def receive(self, expected_sequence):
        if not self.connection.poll(10):
            raise ProtocolError("Frame timed out")
        header = self.connection.recv_bytes(HEADER.size)
        if len(header) != HEADER.size or HEADER.unpack(header) != (expected_sequence, self.payload_bytes):
            raise ProtocolError("Unexpected sequence or payload length")
        if self.mode == "pipe":
            if self.pipe_receive == "into":
                if self.connection.recv_bytes_into(self.view) != self.payload_bytes:
                    raise ProtocolError("Short payload")
            else:
                raw = self.connection.recv_bytes(self.payload_bytes)
                if len(raw) != self.payload_bytes:
                    raise ProtocolError("Short payload")
                np.copyto(self.view, np.frombuffer(raw, dtype=np.float32))
                del raw  # Public API sensitivity control; no private Connection calls.
        fill(self.base, self.expected, expected_sequence)
        # CRC alone is not the correctness oracle: check every tensor value first.
        if not np.array_equal(self.view, self.expected):
            raise ProtocolError("Tensor differs from independently generated expected values")
        observed_crc = crc(self.view)
        self.connection.send_bytes(ACK.pack(expected_sequence, observed_crc))
        return observed_crc
