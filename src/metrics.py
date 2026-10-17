"""Small, testable helpers for evaluating QRS peak detectors."""

from __future__ import annotations

from typing import Iterable


def compare_r_peaks(
    reference: Iterable[int],
    detected: Iterable[int],
    sampling_rate: float,
    tolerance_seconds: float = 0.15,
) -> dict[str, float | int]:
    """Match detected R-peaks to expert beat annotations one-to-one.

    Both sequences contain sample indices from the same segment and must be
    sortable. An event is a true positive if it falls within the tolerance of
    an unmatched reference beat. Returns event-detection metrics, not beat-type
    classification metrics.

    This two-pointer matcher assumes beats are farther apart than the matching
    tolerance, as is typical for MIT-BIH ECG. For dense event sequences an
    optimal assignment algorithm would be more appropriate.
    """
    if sampling_rate <= 0 or tolerance_seconds < 0:
        raise ValueError("sampling_rate must be > 0 and tolerance_seconds >= 0")

    refs = sorted(int(sample) for sample in reference)
    preds = sorted(int(sample) for sample in detected)
    tolerance_samples = round(tolerance_seconds * sampling_rate)

    i = j = 0
    matched_errors = []
    while i < len(refs) and j < len(preds):
        error = preds[j] - refs[i]
        if abs(error) <= tolerance_samples:
            matched_errors.append(abs(error) * 1000.0 / sampling_rate)
            i += 1
            j += 1
        elif preds[j] < refs[i]:
            j += 1
        else:
            i += 1

    tp = len(matched_errors)
    fp = len(preds) - tp
    fn = len(refs) - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "Mean_absolute_error_ms": sum(matched_errors) / tp if tp else float("nan"),
    }
