
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from urllib.request import urlopen

import matplotlib
matplotlib.use("Agg")  # Save figures without requiring a graphical display.
import matplotlib.pyplot as plt
import neurokit2 as nk
import numpy as np
import pandas as pd
import wfdb

from .metrics import compare_r_peaks


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FIGURES_DIR = ROOT / "figures"
RESULTS_DIR = ROOT / "results"
PHYSIONET_BASE_URL = "https://physionet.org/files/mitdb/1.0.0"

# WFDB beat annotations; exclude rhythm changes (+), artifacts (~), etc.
# See https://www.physionet.org/physiobank/annotations.shtml
BEAT_SYMBOLS = {
    "N", "L", "R", "B", "A", "a", "J", "S", "V", "r", "F",
    "e", "j", "n", "E", "/", "f", "Q", "?",
}
DETECTORS = ("neurokit", "pantompkins1985")


def download_mit_bih_record(record_id: str) -> Path:
    """Download the three required files once; reuse them on later runs."""
    if not (record_id.isascii() and record_id.isdigit() and len(record_id) == 3):
        raise ValueError("MIT-BIH record ID must be a three-digit number, e.g. 100")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for extension in ("hea", "dat", "atr"):
        filename = f"{record_id}.{extension}"
        target = DATA_DIR / filename
        if target.exists() and target.stat().st_size > 0:
            continue
        print(f"Downloading {filename} from PhysioNet...")
        temporary = target.with_name(filename + ".partial")
        try:
            with urlopen(f"{PHYSIONET_BASE_URL}/{filename}", timeout=60) as source:
                with temporary.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
            temporary.replace(target)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(
                f"Could not download {filename}. Check your connection, or manually "
                f"download the .hea, .dat and .atr files from {PHYSIONET_BASE_URL}/ "
                f"and place them in {DATA_DIR}"
            ) from exc
    return DATA_DIR / record_id


def load_segment(record_path: Path, minutes: float):
    """Read channel MLII (or channel 0) and expert beat positions."""
    record = wfdb.rdrecord(str(record_path))
    annotations = wfdb.rdann(str(record_path), "atr")
    fs = float(record.fs)
    sample_count = min(len(record.p_signal), round(minutes * 60 * fs))
    if sample_count < round(10 * fs):
        raise ValueError("Choose at least 10 seconds of ECG")

    channel = record.sig_name.index("MLII") if "MLII" in record.sig_name else 0
    raw_ecg = np.asarray(record.p_signal[:sample_count, channel], dtype=float)
    reference = np.asarray(
        [int(sample) for sample, symbol in zip(annotations.sample, annotations.symbol)
         if symbol in BEAT_SYMBOLS and 0 <= sample < sample_count],
        dtype=int,
    )
    return raw_ecg, fs, reference, record.sig_name[channel]


def detect_peaks(raw_ecg: np.ndarray, fs: float):
    """Clean and detect using each method's recommended pipeline."""
    outputs = {}
    for method in DETECTORS:
        clean = nk.ecg_clean(raw_ecg, sampling_rate=fs, method=method)
        _, info = nk.ecg_peaks(
            clean,
            sampling_rate=fs,
            method=method,
            correct_artifacts=False,
        )
        outputs[method] = {
            "clean": np.asarray(clean),
            "peaks": np.asarray(info["ECG_R_Peaks"], dtype=int),
        }
    return outputs


def plot_overview(raw_ecg: np.ndarray, fs: float, record_id: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    times = np.arange(len(raw_ecg)) / fs
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.plot(times, raw_ecg, linewidth=0.7)
    ax.set(xlabel="Time (s)", ylabel="ECG (mV)", title=f"MIT-BIH {record_id}: raw ECG")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    output = FIGURES_DIR / f"{record_id}_raw_ecg.png"
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return output


def plot_comparison(
    raw_ecg: np.ndarray,
    fs: float,
    reference: np.ndarray,
    detector_outputs: dict,
    record_id: str,
    zoom_start: float,
    zoom_seconds: float,
) -> Path:
    n = len(raw_ecg)
    start = int(zoom_start * fs)
    stop = min(n, int((zoom_start + zoom_seconds) * fs))
    if start >= stop:
        raise ValueError("Zoom window starts after the end of the recording")

    times = np.arange(start, stop) / fs
    fig, axs = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axs[0].plot(times, raw_ecg[start:stop], linewidth=0.9)
    axs[0].set(ylabel="ECG (mV)", title="Original ECG + expert annotations")
    ref = reference[(reference >= start) & (reference < stop)]
    axs[0].scatter(ref / fs, raw_ecg[ref], s=48, marker="o", facecolors="none",
                   edgecolors="tab:green", label="Expert beats", zorder=3)
    axs[0].legend(loc="upper right")

    for ax, method in zip(axs[1:], DETECTORS):
        clean = detector_outputs[method]["clean"]
        peaks = detector_outputs[method]["peaks"]
        local_peaks = peaks[(peaks >= start) & (peaks < stop)]
        ax.plot(times, clean[start:stop], linewidth=0.9)
        ax.scatter(local_peaks / fs, clean[local_peaks], s=33, marker="x",
                   label=f"{method} peaks", zorder=3)
        for sample in ref:
            ax.axvline(sample / fs, linewidth=0.7, alpha=0.22, color="tab:green")
        ax.set(ylabel="ECG (mV)", title=method)
        ax.legend(loc="upper right")

    axs[-1].set_xlabel("Time (s)")
    for ax in axs:
        ax.grid(alpha=0.15)
    fig.suptitle(f"MIT-BIH {record_id}: QRS detection comparison", fontsize=13)
    fig.tight_layout()
    output = FIGURES_DIR / f"{record_id}_qrs_comparison.png"
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return output


def save_results(outputs: dict, reference: np.ndarray, fs: float, record_id: str):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_rows = []
    for method, output in outputs.items():
        row = {"record": record_id, "method": method,
               "reference_beats": len(reference), "detected_beats": len(output["peaks"])}
        row.update(compare_r_peaks(reference, output["peaks"], fs))
        metrics_rows.append(row)

    metrics = pd.DataFrame(metrics_rows)
    metrics_path = RESULTS_DIR / f"{record_id}_qrs_metrics.csv"
    metrics.to_csv(metrics_path, index=False)

    # HRV refers to R-R (NN) intervals and must be interpreted with care in
    # recordings containing ectopic beats or other arrhythmias.
    peaks = outputs["neurokit"]["peaks"]
    if len(peaks) >= 4:
        hrv = nk.hrv_time(peaks, sampling_rate=fs, show=False)
        hrv_path = RESULTS_DIR / f"{record_id}_hrv_time.csv"
        hrv.to_csv(hrv_path, index=False)
    else:
        hrv = None
        hrv_path = None
    return metrics, metrics_path, hrv, hrv_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", default="100", help="MIT-BIH record ID (default: 100)")
    parser.add_argument("--minutes", type=float, default=5.0,
                        help="Analyze the first N minutes (default: 5)")
    parser.add_argument("--zoom-start", type=float, default=10.0,
                        help="Start of zoom plot in seconds (default: 10)")
    parser.add_argument("--zoom-seconds", type=float, default=12.0,
                        help="Zoom window duration (default: 12)")
    args = parser.parse_args()
    if args.minutes <= 0 or args.zoom_start < 0 or args.zoom_seconds <= 0:
        parser.error("minutes and zoom-seconds must be > 0; zoom-start must be >= 0")

    record_path = download_mit_bih_record(args.record)
    ecg, fs, reference, channel = load_segment(record_path, args.minutes)
    print(f"Record {args.record} | lead {channel} | sampling rate {fs:g} Hz | "
          f"duration {len(ecg) / fs:.1f} s | reference beats {len(reference)}")

    detected = detect_peaks(ecg, fs)
    metrics, metrics_path, hrv, hrv_path = save_results(detected, reference, fs, args.record)
    raw_plot = plot_overview(ecg, fs, args.record)
    comparison_plot = plot_comparison(ecg, fs, reference, detected, args.record,
                                      args.zoom_start, args.zoom_seconds)

    print("\nQRS performance (one-to-one matching within ±150 ms):")
    print(metrics[["method", "TP", "FP", "FN", "Precision", "Recall", "F1"]]
          .to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    if hrv is not None:
        selected = [name for name in ("HRV_MeanNN", "HRV_SDNN", "HRV_RMSSD")
                    if name in hrv.columns]
        print("\nExploratory time-domain HRV (NeuroKit detections; milliseconds):")
        print(hrv[selected].to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nSaved: {metrics_path}")
    if hrv_path:
        print(f"Saved: {hrv_path}")
    print(f"Saved: {raw_plot}")
    print(f"Saved: {comparison_plot}")
    print("\nNote: this is a single-record educational demo, not clinical validation.")


if __name__ == "__main__":
    main()
