# scripts/outlier_check.py
"""
STEP TRACKING
- Step: Outlier scan on clean v1
- Objective: Identify suspicious values via IQR and z-score on numeric columns
- Expected: logs/outliers_report.txt + logs/proposed_caps.json; no data is modified
"""

import os
import json
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLEAN_DIR = os.path.join(ROOT, "data_clean")
LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

FILES = {
    "mat": os.path.join(CLEAN_DIR, "student-mat_clean_v1.csv"),
    "por": os.path.join(CLEAN_DIR, "student-por_clean_v1.csv"),
}

NUM_COLS = ["age", "absences", "G1", "G2", "G3"]

def iqr_bounds(s, k=1.5):
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    low = q1 - k * iqr
    high = q3 + k * iqr
    return low, high

def z_scores(s):
    m = s.mean()
    sd = s.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - m) / sd

def scan_df(df, name):
    lines = []
    lines.append("== {} basic stats ==".format(name))
    for c in NUM_COLS:
        if c in df.columns:
            desc = df[c].describe()
            lines.append("{}: count={}, min={}, q1={}, median={}, q3={}, max={}, mean={}, std={}".format(
                c, int(desc["count"]), desc["min"], desc["25%"], desc["50%"], desc["75%"], desc["max"], desc["mean"], desc["std"]
            ))
    lines.append("")

    lines.append("== {} outlier checks (IQR + |z|>=3) ==".format(name))
    summary = {"file": name, "columns": {}}
    for c in NUM_COLS:
        if c not in df.columns:
            continue
        s = pd.to_numeric(df[c], errors="coerce")

        lo, hi = iqr_bounds(s, k=1.5)
        mask_iqr = (s < lo) | (s > hi)
        n_iqr = int(mask_iqr.sum())

        zs = z_scores(s).abs()
        mask_z = zs >= 3.0
        n_z = int(mask_z.sum())

        summary["columns"][c] = {
            "min": float(s.min()),
            "max": float(s.max()),
            "iqr_low": float(lo),
            "iqr_high": float(hi),
            "n_iqr_outliers": n_iqr,
            "z_threshold": 3.0,
            "n_z_outliers": n_z
        }

        lines.append("{}: min={}, max={}, IQR_low={}, IQR_high={}, n_IQR_outliers={}, n_|z|>=3={}".format(
            c,
            summary["columns"][c]["min"],
            summary["columns"][c]["max"],
            summary["columns"][c]["iqr_low"],
            summary["columns"][c]["iqr_high"],
            n_iqr,
            n_z
        ))
    lines.append("")
    return "\n".join(lines), summary

def main():
    report_lines = []
    caps_suggestion = {}

    for key, path in FILES.items():
        if not os.path.exists(path):
            report_lines.append("MISSING: {}".format(path))
            continue

        df = pd.read_csv(path)
        text, summary = scan_df(df, key)
        report_lines.append(text)

        proposed = {}
        for c, info in summary["columns"].items():
            if info.get("n_iqr_outliers", 0) > 0:
                proposed[c] = {
                    "low_cap": info["iqr_low"],
                    "high_cap": info["iqr_high"]
                }
        caps_suggestion[key] = proposed

    report = "# Outlier Report (clean v1)\n\n" + "\n".join(report_lines)
    out_path = os.path.join(LOG_DIR, "outliers_report.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    caps_path = os.path.join(LOG_DIR, "proposed_caps.json")
    with open(caps_path, "w", encoding="utf-8") as f:
        json.dump(caps_suggestion, f, indent=2)

    print(report)
    print("Wrote {}".format(out_path))
    print("Wrote {}".format(caps_path))

if __name__ == "__main__":
    main()
