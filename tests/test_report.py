import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tiny_ipc_lab.cli import benchmark
from tiny_ipc_lab.experiment import TrialFailure
from tiny_ipc_lab.report import summarize, verify, render, overview, resolve, comparisons


class MetricsTests(unittest.TestCase):
    def test_paired_ratio_is_not_a_ratio_of_independent_medians(self):
        report = {"pairs": 2, "cases": [{"payload_bytes": 64, "runs": [
            {"trial": 0, "mode": "pipe", "summary": {"payload_mib_per_s": 1.}},
            {"trial": 0, "mode": "shared", "summary": {"payload_mib_per_s": 10.}},
            {"trial": 1, "mode": "pipe", "summary": {"payload_mib_per_s": 100.}},
            {"trial": 1, "mode": "shared", "summary": {"payload_mib_per_s": 200.}}]}]}
        result = comparisons(report)[0]
        self.assertEqual(result["ratios"], [10., 2.])
        self.assertEqual(result["median"], 6.)
        self.assertNotAlmostEqual(result["median"], 105 / 50.5)
        report["cases"][0]["runs"].pop()
        with self.assertRaises(ValueError):
            comparisons(report)
    def fixture(self):
        return {"mode": "shared", "pipe_receive": "into", "payload_bytes": 4, "count": 2, "warmup": 8, "timing_version": 2, "consumer_delay_s": 0.,
                "producer": {"event": "done", "start_s": 1., "end_s": 1.006, "cpu_s": .001,
                             "high_water_rss_bytes": 100,
                             "records": [{"sequence": 8, "start_s": 1., "end_s": 1.002, "input_crc32": 1, "ack_crc32": 1},
                                         {"sequence": 9, "start_s": 1.003, "end_s": 1.006, "input_crc32": 2, "ack_crc32": 2}]},
                "consumer": {"event": "done", "end_s": 1.007, "cpu_s": .002, "high_water_rss_bytes": 200,
                             "records": [{"sequence": 8, "crc32": 1, "verified_elements": 1, "delay_start_s": 1.0014, "ready_s": 1.0015},
                                         {"sequence": 9, "crc32": 2, "verified_elements": 1, "delay_start_s": 1.0049, "ready_s": 1.005}]},
                "memory_window": {"start_s": .99, "end_s": 1.02},
                "rss_samples": [{"start_s": .991, "end_s": .992, "producer_rss_bytes": 100, "consumer_rss_bytes": 10},
                                {"start_s": 1.008, "end_s": 1.009, "producer_rss_bytes": 10, "consumer_rss_bytes": 100}],
                "cleanup": {"exitcodes": [0, 0], "forced_termination": False,
                            "all_workers_exited": True, "control_readers_exited": True, "segment_unlinked": True}}

    def test_hand_calculated_duration_latency_and_simultaneous_rss(self):
        result = summarize(self.fixture(), check_values=False)
        self.assertAlmostEqual(result["duration_s"], .007)
        self.assertAlmostEqual(result["messages_per_s"], 2 / .007)
        self.assertAlmostEqual(result["payload_mib_per_s"], 8 / .007 / 1048576)
        self.assertAlmostEqual(result["round_trip_ms"]["p50"], 2.5)
        self.assertAlmostEqual(result["round_trip_ms"]["p95"], 2.95)
        self.assertEqual(result["peak_paired_rss_bytes"], 110)  # Independent peaks would incorrectly give 200.
        self.assertAlmostEqual(result["max_rss_gap_ms"], 17.)
        self.assertAlmostEqual(result["max_paired_read_ms"], 1.)

    def test_rejects_missing_repeated_reordered_or_contradictory_records(self):
        faults = [lambda r: r["consumer"]["records"].pop(),
                  lambda r: r["producer"]["records"].reverse(),
                  lambda r: r["consumer"]["records"][1].update(sequence=8),
                  lambda r: r["consumer"]["records"][1].update(crc32=3),
                  lambda r: r["producer"]["records"][1].update(start_s=1.001),
                  lambda r: r["producer"]["records"][0].update(end_s=float("nan")),
                  lambda r: r["rss_samples"].pop(),
                  lambda r: r["rss_samples"][1].update(start_s=1.001, end_s=1.002),
                  lambda r: r["rss_samples"][0].update(producer_rss_bytes=-1),
                  lambda r: r["cleanup"].update(segment_unlinked=False)]
        for fault in faults:
            run = self.fixture()
            fault(run)
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                summarize(run, check_values=False)


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name) / "smoke"
        cls.report = benchmark(cls.directory, sizes=[64], pairs=2, count=9)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_production_benchmark_and_report_reconcile_every_message(self):
        verify(self.report, self.directory)
        self.assertEqual((self.directory / "report.html").read_text(), render(self.report))
        self.assertEqual((self.directory / "README.md").read_text(), overview(self.report))
        self.assertFalse((self.directory / "partial.json").exists())
        self.assertEqual(sum(r["summary"]["verified_messages"] for r in self.report["cases"][0]["runs"]), 36)

    def test_report_rejects_forged_metrics_missing_pairs_or_unequal_work(self):
        faults = [lambda r: r["cases"][0]["runs"].pop(),
                  lambda r: r["cases"][0]["runs"][0]["summary"].update(payload_mib_per_s=1e9),
                  lambda r: r["cases"][0]["runs"][0].update(count=8),
                  lambda r: r.update(source_sha256="0"*64),
                  lambda r: r["cases"][0]["runs"][0].update(file="../../README.md"),
                  lambda r: r.update(pipe_receive="bytes"),
                  lambda r: r["comparisons"][0].update(median=4.10)]
        for fault in faults:
            changed = copy.deepcopy(self.report)
            fault(changed)
            with self.assertRaises(ValueError):
                verify(changed, self.directory)

    def test_corruption_and_self_consistent_wrong_payload_crc_are_rejected(self):
        stub = copy.deepcopy(self.report["cases"][0]["runs"][0])
        run = resolve(stub, self.directory)
        for row in run["producer"]["records"]:
            row["input_crc32"] = row["ack_crc32"] = 0
        for row in run["consumer"]["records"]:
            row["crc32"] = 0
        # Also recompute the summary and digest: independent data regeneration must still reject it.
        stub["summary"] = summarize(run, check_values=False)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / stub["file"]
            path.parent.mkdir()
            payload = gzip.compress(json.dumps(run).encode(), mtime=0)
            path.write_bytes(payload)
            stub["sha256"] = hashlib.sha256(payload).hexdigest()
            with self.assertRaises(ValueError):
                resolve(stub, temp)
            path.write_bytes(payload[:-4] + b"bad!")
            with self.assertRaises(ValueError):
                resolve(stub, temp)

    def test_first_trial_failure_leaves_explicit_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "failed"
            with patch("tiny_ipc_lab.cli.run_trial", side_effect=TrialFailure("injected", {"all_workers_exited": True})):
                with self.assertRaises(TrialFailure):
                    benchmark(directory, sizes=[64], pairs=1, count=1)
            partial = json.loads((directory / "partial.json").read_text())
            self.assertEqual(partial["cases"][0]["runs"], [])
            self.assertTrue((directory / "failure.json").exists())
            self.assertFalse((directory / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
