
"""Tests for pooling per-record QRS detection results."""

import math
import unittest

import pandas as pd

from src.batch_demo import summarize_micro


class TestBatchSummary(unittest.TestCase):

    def setUp(self):
        self.data = pd.DataFrame([
            {
                "record": "100",
                "method": "neurokit",
                "reference_beats": 10,
                "detected_beats": 10,
                "TP": 9,
                "FP": 1,
                "FN": 1,
                "Mean_absolute_error_ms": 20.0,
            },
            {
                "record": "101",
                "method": "neurokit",
                "reference_beats": 1,
                "detected_beats": 1,
                "TP": 1,
                "FP": 0,
                "FN": 0,
                "Mean_absolute_error_ms": 10.0,
            },
            {
                "record": "100",
                "method": "pantompkins1985",
                "reference_beats": 10,
                "detected_beats": 10,
                "TP": 10,
                "FP": 0,
                "FN": 0,
                "Mean_absolute_error_ms": 5.0,
            },
            {
                "record": "101",
                "method": "pantompkins1985",
                "reference_beats": 1,
                "detected_beats": 1,
                "TP": 1,
                "FP": 0,
                "FN": 0,
                "Mean_absolute_error_ms": 5.0,
            },
        ])

    def test_pooled_metrics(self):
        summary = summarize_micro(self.data).set_index("method")
        nk = summary.loc["neurokit"]

        self.assertEqual((nk.TP, nk.FP, nk.FN), (10, 1, 1))
        self.assertEqual(nk.records, 2)
        self.assertAlmostEqual(nk.Precision, 10 / 11)
        self.assertAlmostEqual(nk.Recall, 10 / 11)
        self.assertAlmostEqual(nk.F1, 10 / 11)
        self.assertAlmostEqual(nk.Mean_absolute_error_ms, 19.0)

        self.assertEqual(summary.loc["pantompkins1985", "F1"], 1.0)

    def test_missing_detector_raises(self):
        subset = self.data[self.data["method"] == "neurokit"]

        with self.assertRaises(ValueError):
            summarize_micro(subset)

    def test_no_matched_beats(self):
        empty = self.data.copy()

        empty["TP"] = 0
        empty["FP"] = empty["detected_beats"]
        empty["FN"] = empty["reference_beats"]
        empty["Mean_absolute_error_ms"] = float("nan")

        summary = summarize_micro(empty)

        self.assertTrue((summary["F1"] == 0).all())
        self.assertTrue(
            all(math.isnan(x) for x in summary["Mean_absolute_error_ms"])
        )


if __name__ == "__main__":
    unittest.main()
