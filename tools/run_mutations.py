"""Require meaningful behavioral failures, rather than import/hash failures."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ACK_BLOCK = '''        if not self.connection.poll(10):
            raise ProtocolError("Acknowledgement timed out")
        acknowledgement = self.connection.recv_bytes(ACK.size)
        if len(acknowledgement) != ACK.size:
            raise ProtocolError("Malformed acknowledgement")
        actual_sequence, actual_crc = ACK.unpack(acknowledgement)
        if actual_sequence != sequence or actual_crc != expected_crc:
            raise ProtocolError("Acknowledgement sequence/content differs")
        return actual_crc'''
MUTATIONS = [
    ("skip_shared_copy", "np.copyto(self.view, frame)", "pass", "test_ack_is_required_before_buffer_reuse_and_every_generation_changes"),
    ("stale_sequence", "HEADER.pack(sequence, frame.nbytes)", "HEADER.pack(0, frame.nbytes)", "test_ack_is_required_before_buffer_reuse_and_every_generation_changes"),
    ("reuse_before_ack", ACK_BLOCK, "        return expected_crc", "test_ack_is_required_before_buffer_reuse_and_every_generation_changes"),
    ("skip_full_tensor_validation", "if not np.array_equal(self.view, self.expected):", "if False:", "test_receiver_checks_middle_values_and_stale_shared_generation"),
    ("trust_wrong_ack", "if actual_sequence != sequence or actual_crc != expected_crc:", "if False:", "test_sender_rejects_wrong_ack_sequence_or_crc"),
]

POOL_MUTATIONS = [
    ("pool_reuse_before_ack", 'self.acknowledge()  # Backpressure: no overwrite, allocation, drop or unbounded queue.', 'self.free.append(self.pending[0]["slot"])', "test_full_pool_blocks_until_consumer_ack_and_then_reuses_generation"),
    ("pool_ignore_release_generation", 'RELEASE.unpack(raw) != expected', '(RELEASE.unpack(raw)[:2] + RELEASE.unpack(raw)[3:]) != (expected[:2] + expected[3:])', "test_stale_release_cannot_free_current_generation"),
    ("pool_ignore_publication_generation", 'PUBLICATION.unpack(raw) != (sequence, slot, generation, self.payload_bytes)', '(PUBLICATION.unpack(raw)[:2] + PUBLICATION.unpack(raw)[3:]) != (sequence, slot, self.payload_bytes)', "test_receiver_rejects_stale_generation_and_middle_value_corruption"),
    ("pool_skip_full_validation", 'if not np.array_equal(view, self.expected):', 'if False:', "test_receiver_rejects_stale_generation_and_middle_value_corruption"),
]

WORKER_MUTATIONS = [
    ("worker_staging_copy_instead_of_inplace", 'fill(base, target, seq)  # Direct write into the owned slot; no staging frame/copy.',
     'staging = np.empty_like(target)\n                fill(base, staging, seq)\n                np.copyto(target, staging)',
     "test_production_worker_generates_directly_into_owned_shared_slots"),
]


def run(mutation=None):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)
        for folder in ("src", "tests"):
            shutil.copytree(ROOT / folder, path / folder, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        if mutation:
            name, before, after, test = mutation
            worker = mutation[0].startswith("worker_")
            pool = mutation[0].startswith("pool_")
            source = path / ("src/tiny_ipc_lab/experiment.py" if worker else "src/tiny_ipc_lab/pool.py" if pool else "src/tiny_ipc_lab/protocol.py")
            text = source.read_text()
            if text.count(before) != 1:
                raise ValueError("Non-unique mutation target: " + name)
            source.write_text(text.replace(before, after))
            tests = [("test_pool.PoolProcessTests." if worker else "test_pool.PoolProtocolTests." if pool else "test_ipc.ProtocolTests.") + test]
        else:
            tests = ["test_ipc.ProtocolTests", "test_pool.PoolProtocolTests", "test_pool.PoolProcessTests.test_production_worker_generates_directly_into_owned_shared_slots"]
        result = subprocess.run([sys.executable, "-m", "unittest", *tests], cwd=path / "tests",
                                env=dict(os.environ, PYTHONPATH=str(path / "src")), capture_output=True, text=True, timeout=25)
        return result.returncode, result.stdout + result.stderr


if __name__ == "__main__":
    code, output = run()
    if code:
        raise SystemExit("Unchanged baseline failed: " + output)
    for mutation in MUTATIONS + POOL_MUTATIONS + WORKER_MUTATIONS:
        code, output = run(mutation)
        if code != 1 or "FAIL:" not in output or "ERROR:" in output:
            raise SystemExit("Fault not detected by behavioral assertion: " + mutation[0] + "\n" + output)
        print("Detected:", mutation[0])
    print("All ten source faults detected by behavioral assertions.")
