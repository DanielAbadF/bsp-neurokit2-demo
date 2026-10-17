
"""Compare NeuroKit2's QRS detection pipelines on several MIT-BIH records."""

from __future__ import annotations

import argparse
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .ecg_demo import (
    DETECTORS,
    FIGURES_DIR,
    RESULTS_DIR,
    detect_peaks,
    download_mit_bih_record,
    load_segment,
)
from .metrics import compare_r_peaks


DEFAULT_RECORDS = ("100", "101", "105", "108", "200", "203")


def evaluate_record(record_id: str, minutes: float) -> list[dict]:
    """Analyze one record and score both detection pipelines."""
    record_path = download_mit_bih_record(record_id)
    raw_ecg, fs, reference, lead = load_segment(record_path, minutes)
    outputs = detect_peaks(raw_ecg, fs)

    rows = []

    for method in DETECTORS:
        peaks = outputs[method]["peaks"]

        rows.append({
            "record": record_id,
            "lead": lead,
            "duration_s": round(len(raw_ecg) / fs, 2),
            "method": method,
            "reference_beats": len(reference),
            "detected_beats": len(peaks),
            **compare_r_peaks(reference, peaks, fs),
        })

    return rows


def summarize_micro(per_record: pd.DataFrame) -> pd.DataFrame:
    """Pool TP, FP and FN across records to compute overall metrics."""
    summaries = []

    for method in DETECTORS:
        subset = per_record.loc[per_record["method"] == method]

        if subset.empty:
            raise ValueError(f"No results for method: {method}")

        tp = int(subset["TP"].sum())
        fp = int(subset["FP"].sum())
        fn = int(subset["FN"].sum())

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * tp / (2 * tp + fp + fn)
            if 2 * tp + fp + fn else 0.0
        )

        mean_error_ms = (
            float(
                (
                    subset["Mean_absolute_error_ms"].fillna(0.0)
                    * subset["TP"]
                ).sum() / tp
            )
            if tp else float("nan")
        )

        summaries.append({
            "method": method,
            "records": subset["record"].nunique(),
            "reference_beats": int(subset["reference_beats"].sum()),
            "detected_beats": int(subset["detected_beats"].sum()),
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "Precision": precision,
            "Recall": recall,
            "F1": f1,
            "Mean_absolute_error_ms": mean_error_ms,
        })

    return pd.DataFrame(summaries)


def plot_record_f1(per_record: pd.DataFrame):
    """Plot F1-scores for each record and detection method."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    pivot = per_record.pivot(
        index="record",
        columns="method",
        values="F1",
    )

    pivot = pivot.reindex(columns=DETECTORS).mul(100.0)

    ax = pivot.plot(
        kind="bar",
        figsize=(10, 5),
        width=0.75,
        rot=0,
    )

    ax.set(
        title="MIT-BIH: QRS detection F1-score by record",
        xlabel="MIT-BIH record",
        ylabel="F1-score (%)",
        ylim=(0, 100),
    )

    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Detection pipeline")

    fig = ax.get_figure()
    fig.tight_layout()

    output = FIGURES_DIR / "batch_qrs_f1.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)

    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--records",
        nargs="+",
        default=list(DEFAULT_RECORDS),
        help="MIT-BIH record IDs (default: 100 101 105 108 200 203)",
    )

    parser.add_argument(
        "--minutes",
        type=float,
        default=5.0,
        help="Analyze the first N minutes of each record",
    )

    args = parser.parse_args()

    if not math.isfinite(args.minutes) or args.minutes < 1 / 6:
        parser.error("--minutes must be at least 10 seconds")

    if len(args.records) != len(set(args.records)):
        parser.error("--records must not contain duplicates")

    all_rows = []

    for record_id in args.records:
        print(
            f"Analyzing MIT-BIH record {record_id} ...",
            flush=True,
        )

        rows = evaluate_record(record_id, args.minutes)
        all_rows.extend(rows)

        for row in rows:
            print(
                f"  {row['method']:<15} "
                f"TP={row['TP']:<5} "
                f"FP={row['FP']:<4} "
                f"FN={row['FN']:<4} "
                f"F1={row['F1']:.4f}"
            )

    per_record = pd.DataFrame(all_rows)
    summary = summarize_micro(per_record)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    record_csv = RESULTS_DIR / "batch_qrs_per_record.csv"
    summary_csv = RESULTS_DIR / "batch_qrs_micro_summary.csv"

    per_record.to_csv(record_csv, index=False)
    summary.to_csv(summary_csv, index=False)

    figure = plot_record_f1(per_record)

    print("\nMicro-averaged scores (pooled TP, FP, FN):")

    print(
        summary[
            [
                "method",
                "records",
                "TP",
                "FP",
                "FN",
                "Precision",
                "Recall",
                "F1",
                "Mean_absolute_error_ms",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    print(f"\nSaved: {record_csv}")
    print(f"Saved: {summary_csv}")
    print(f"Saved: {figure}")

    print(
        "\nNote: an educational multi-record comparison, "
        "not clinical validation."
    )


if __name__ == "__main__":
    main()
