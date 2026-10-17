# Source code

- `ecg_demo.py`: loads MIT-BIH ECG, cleans it with NeuroKit2, detects R-peaks,
  compares detectors and exports plots and metrics.
- `metrics.py`: independent event-level R-peak matching and evaluation functions.

Run from the repository root: `python -m src.ecg_demo`.
