# NeuroKit2: ECG Processing and QRS Detection Comparison

Seminar demonstration for the **Biomedical Signal Processing** course.

This project presents the open-source [NeuroKit2](https://github.com/neuropsychology/NeuroKit) toolbox through a practical analysis of real ECG signals. It compares two available R-peak detection methods against annotated beats in a public [PhysioNet](https://physionet.org/content/mitdb/1.0.0/) dataset.

## What the demonstration covers

1. Load a real ECG signal from the MIT-BIH Arrhythmia Database (record `100`, lead `MLII`).
2. Clean the ECG with NeuroKit2 using the preprocessing method appropriate to each detector.
3. Detect R-peaks using `neurokit` and `pantompkins1985`.
4. Compare both methods against expert-reviewed beat annotations using a one-to-one, ±150 ms matching rule.
5. Compute precision, recall, F1 and timing error for detected beats.
6. Calculate exploratory time-domain heart-rate variability (HRV) indices.
7. Save visualizations and numeric results for the seminar.

## Requirements

- Python **3.11 or 3.12** recommended.
- Internet access for the first run (downloads a public record; subsequent runs use cached files).

### Windows PowerShell

```powershell
# From the repository root
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m src.ecg_demo
```

If you use a different installed Python version, adapt the `py -3.12` command accordingly.

Run a different segment or another MIT-BIH record:

```powershell
python -m src.ecg_demo --record 101 --minutes 5 --zoom-start 20 --zoom-seconds 10
```

Run the unit tests without downloading ECG data:

```powershell
python -m unittest discover -s tests -v
```

## Generated files

```text
bsp-neurokit2-demo/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── ecg_demo.py            # Real-record ECG demo
│   └── metrics.py             # Event-level validation metrics
├── tests/
│   └── test_metrics.py       # Unit tests for matching
├── data/                      # Local MIT-BIH .dat, .hea, .atr (ignored)
├── figures/                   # Generated .png plots (ignored)
└── results/                   # Generated .csv tables (ignored)
```

The downloaded ECG recordings and generated outputs are not committed. The script creates:

- `figures/100_raw_ecg.png`
- `figures/100_qrs_comparison.png`
- `results/100_qrs_metrics.csv`
- `results/100_hrv_time.csv`

## Evaluation method and limitations

- The `atr` file mixes beat annotations with other event annotations. We **select only beat symbols** for QRS-detection evaluation; rhythm-change markers and noise markers are excluded.
- One predicted R-peak may match **at most one reference beat** within ±150 ms. Unmatched detections are false positives (FP); unmatched reference beats are false negatives (FN).
- Precision = TP / (TP + FP); recall = TP / (TP + FN); F1 is their harmonic mean.
- This is a **five-minute, single-record demonstration**, not a published benchmark or proof of clinical performance. Broader validation should use many records, difficult noise conditions, prespecified criteria, and confidence intervals.
- The comparison follows each method's built-in cleaning workflow. Changes in sampling rate, filtering, ECG morphology, noise, and matching tolerance can change the scores.
- Pan–Tompkins peak locations may have different temporal alignment than NeuroKit's default peak locations. The timing-error column and zoom plot help reveal those differences.
- HRV indices are exploratory: raw R-R intervals in arrhythmia recordings may include ectopic beats; proper analysis of **NN** intervals may require artifact detection and beat correction. Do not use these values for diagnosis.
- The `neurokit` ECG cleaning default includes a 50 Hz power-line suppression step; original US recordings may have different interference. This is a parameter worth studying in a follow-up experiment.

## About NeuroKit2 (presentation pointers)

- Core functionality: ECG, PPG, RSP, EDA, EMG, EEG; event detection, cleaning, signal-quality assessment, HRV and statistical analysis.
- Useful APIs: `nk.ecg_clean()`, `nk.ecg_peaks()`, `nk.ecg_process()`, `nk.hrv_time()`.
- Published research and examples are linked below; **our single-record demo is independent of the toolbox's published validation**.
- Potential improvements to discuss: robust noise-aware selection of detector, automated parameter calibration, cross-dataset testing, explicit confidence intervals and more comprehensive peak-alignment reporting.


## Multi-record QRS detection comparison

The batch experiment evaluates both detection pipelines across six
MIT-BIH Arrhythmia Database records.

Default records: 100, 101, 105, 108, 200, 203.

Each recording is analyzed over its first five minutes.

Run:

```powershell
python -m src.batch_demo --records 100 101 105 108 200 203 --minutes 5
```

Alternatively, in VS Code, select the "Batch QRS Comparison"
configuration in Run and Debug and press Ctrl+F5.

### Batch evaluation

For each record, the program:

1. Downloads the ECG and expert beat annotations.
2. Applies each detector's associated ECG cleaning method.
3. Detects R-peaks using NeuroKit2.
4. Matches detections to expert annotations within ±150 ms.
5. Computes TP, FP, FN, precision, recall, F1 and timing error.

Overall performance is calculated using micro-averaging:
TP, FP and FN are pooled across all records before computing
precision, recall and F1.

### Batch outputs

- `results/batch_qrs_per_record.csv`
- `results/batch_qrs_micro_summary.csv`
- `figures/batch_qrs_f1.png`

This experiment evaluates detection performance on selected ECG
segments and should not be interpreted as clinical validation
or as a comprehensive benchmark of NeuroKit2.


## Experimental Results

We evaluated two QRS detection pipelines available in NeuroKit2
using the first five minutes of six MIT-BIH Arrhythmia Database
records: 100, 101, 105, 108, 200, and 203.

R-peaks were matched to expert annotations using a tolerance
of ±150 ms and one-to-one matching.

### Overall performance (micro-averaged)

| Metric | NeuroKit | Pan-Tompkins |
|---|---:|---:|
| Precision | 96.44% | 93.57% |
| Recall | 94.80% | 95.52% |
| F1-score | 95.61% | 94.53% |
| Mean absolute timing error | 5.96 ms | 50.71 ms |

### Observations

- Both methods achieved near-perfect performance on several records.
- Record 108 was particularly challenging for both methods.
- Pan-Tompkins outperformed the default NeuroKit detector on record 203.
- NeuroKit achieved a higher overall F1-score and lower timing error.
- Performance depends on the recording and detection pipeline.

### Limitations

This experiment uses only six recordings and five minutes per
record. Different cleaning procedures are associated with the
two detection algorithms.

These findings do not establish clinical validity or prove
that one algorithm is universally superior.



## References

1. NeuroKit2 source code: https://github.com/neuropsychology/NeuroKit
2. NeuroKit2 documentation: https://neuropsychology.github.io/NeuroKit/
3. Makowski et al. (2021). NeuroKit2: A Python toolbox for neurophysiological signal processing. *Behavior Research Methods*. https://doi.org/10.3758/s13428-020-01516-y
4. Moody & Mark. MIT-BIH Arrhythmia Database (version 1.0.0). PhysioNet. https://doi.org/10.13026/C2F305
5. Pan & Tompkins (1985). A real-time QRS detection algorithm. *IEEE Transactions on Biomedical Engineering*. https://doi.org/10.1109/TBME.1985.325532

The underlying MIT-BIH data are available from PhysioNet under the license identified on its dataset page. Provide attribution when using plots or redistributed samples.
