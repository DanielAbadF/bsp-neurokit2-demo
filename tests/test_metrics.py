"""Unit tests for QRS event-level scoring (no dataset required)."""

import math
import unittest

from src.metrics import compare_r_peaks


class TestPeakMetrics(unittest.TestCase):
    def test_perfect_match(self):
        result = compare_r_peaks([100, 200, 300], [100, 200, 300], 100, 0.1)
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (3, 0, 0))
        self.assertEqual(result["F1"], 1.0)

    def test_false_positive_and_false_negative(self):
        result = compare_r_peaks([100, 200, 300], [100, 200, 400], 100, 0.1)
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (2, 1, 1))
        self.assertAlmostEqual(result["F1"], 2/3)

    def test_matching_tolerance_and_one_to_one(self):
        result = compare_r_peaks([100, 200], [108, 109, 200], 100, 0.1)
        self.assertEqual((result["TP"], result["FP"], result["FN"]), (2, 1, 0))
        self.assertAlmostEqual(result["Mean_absolute_error_ms"], 40.0)

    def test_empty_sequences(self):
        result = compare_r_peaks([], [], 100)
        self.assertEqual(result["F1"], 0.0)
        self.assertTrue(math.isnan(result["Mean_absolute_error_ms"]))

    def test_validation(self):
        with self.assertRaises(ValueError):
            compare_r_peaks([1], [1], 0)


if __name__ == "__main__":
    unittest.main()
