# scripts/qc_check.py
"""
STEP TRACKING (for hiring managers)
- Step: Terminal QC of raw data
- Objective: Verify schema, missing values, duplicates, ranges, placeholders before analysis
- Expected: A qc_report.txt in /logs with issues listed or 'No blocking issues detected.'
"""

import os, sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(ROOT, "data_raw", "student")
LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

FILES = [
    os.path.join(RAW_DIR, "student-mat.csv"),
    os.path.join(RAW_DIR, "student-por.csv"),
]

issues = []
report_lines = []

def add(section, content):
    report_lines.append("\n## {}\n{}".format(section, content))

def check_file(path):
    name = os.path.basename(path)
    try:
        # Use semicolon delimiter
        df = pd.read_csv(path, sep=";", engine="python")
    except Exception as e:
        issues.append("{}: failed to read -> {}".format(name, e))
        add("{} — READ ERROR".format(name), str(e))
        return

    # 1) Shape & dtypes
    schema_info = "Rows x Cols: {} x {}\nDtypes:\n{}".format(
        df.shape[0],
        df.shape[1],
        "\n".join(["  - {}: {}".format(c, t) for c, t in df.dtypes.items()])
    )
    add("{} — Schema".format(name), schema_info)

    # 2) Missing values
    na = df.isna().sum().sort_values(ascending=False)
    add("{} — Missing values".format(name), na.to_string())

    # 3) Placeholder tokens
    placeholders = {"?", "NA", "N/A", "None", "Unknown", "unknown", ""}
    hits = []
    for col in df.columns:
        if df[col].dtype == "object":
            s = df[col].astype(str).str.strip()
            found = {tok: int((s == tok).sum()) for tok in placeholders}
            found = {k: v for k, v in found.items() if v > 0}
            if found:
                hits.append("{}: {}".format(col, ", ".join(["'{}'={}".format(k, v) for k, v in found.items()])))
    if hits:
        add("{} — Placeholder tokens".format(name), "\n".join(hits))
        issues.append("{}: placeholder-like tokens present".format(name))
    else:
        add("{} — Placeholder tokens".format(name), "None detected")

    # 4) Duplicate rows
    dups = int(df.duplicated().sum())
    add("{} — Duplicate rows".format(name), str(dups))
    if dups > 0:
        issues.append("{}: {} duplicate rows".format(name, dups))

    # 5) Value ranges
    expected_ranges = {
        "G1": (0, 20),
        "G2": (0, 20),
        "G3": (0, 20),
        "absences": (0, None),
        "age": (10, 30),
    }
    lines = []
    for col, (lo, hi) in expected_ranges.items():
        if col in df.columns:
            lo_bad = (df[col] < lo) if lo is not None else pd.Series(False, index=df.index)
            hi_bad = (df[col] > hi) if hi is not None else pd.Series(False, index=df.index)
            n_bad = int((lo_bad | hi_bad).sum())
            lines.append("{}: min={}, max={}, out_of_range={}".format(col, df[col].min(), df[col].max(), n_bad))
            if n_bad > 0:
                issues.append("{}: {} has {} out-of-range values".format(name, col, n_bad))
    if lines:
        add("{} — Value ranges".format(name), "\n".join(lines))

    # 6) Categorical uniques
    cat_cols = [c for c in df.columns if df[c].dtype == "object"]
    cat_lines = []
    for c in cat_cols:
        vals = df[c].dropna().astype(str).str.strip().unique()
        vals_sorted = sorted(vals)[:15]
        cat_lines.append("{}: {} unique (showing up to 15) -> {}".format(c, min(len(vals),15), vals_sorted))
    if cat_lines:
        add("{} — Categorical uniques (sample)".format(name), "\n".join(cat_lines))

    # 7) Stats on target fields
    for col in ["G1", "G2", "G3", "absences"]:
        if col in df.columns:
            add("{} — Describe({})".format(name, col), df[col].describe().to_string())

# Run checks
for path in FILES:
    if not os.path.exists(path):
        issues.append("Missing file: {}".format(path))
        add("Missing file", path)
    else:
        check_file(path)

report = "# QC Report — Student Dataset\n" + "\n".join(report_lines)
out_path = os.path.join(LOG_DIR, "qc_report.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report)

print(report)
if issues:
    print("\n=== ISSUES FOUND ===")
    for i in issues:
        print("- {}".format(i))
    sys.exit(1)
else:
    print("\nNo blocking issues detected.")


