# scripts/apply_caps_make_v2.py
"""
STEP TRACKING
- Step: Apply outlier caps and export v2
- Objective: Cap extreme 'absences' to reduce skew while retaining all students
- Policy: Keep grades (G1,G2,G3) and age unchanged; absences capped at IQR-high
- Expected: data_clean/student-mat_clean_v2.csv, student-por_clean_v2.csv + logs/caps_summary.txt
"""

import os, json
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLEAN_DIR = os.path.join(ROOT, "data_clean")
LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Input (v1) and output (v2) files
FILES = {
    "mat": {
        "in":  os.path.join(CLEAN_DIR, "student-mat_clean_v1.csv"),
        "out": os.path.join(CLEAN_DIR, "student-mat_clean_v2.csv"),
    },
    "por": {
        "in":  os.path.join(CLEAN_DIR, "student-por_clean_v1.csv"),
        "out": os.path.join(CLEAN_DIR, "student-por_clean_v2.csv"),
    },
}

# Default caps from IQR highs seen in outlier_check:
DEFAULT_CAPS = {
    "mat": {"absences": {"low_cap": None, "high_cap": 20.0}},
    "por": {"absences": {"low_cap": None, "high_cap": 15.0}},
}

# If you ran scripts/outlier_check.py, we can load its suggested caps
CAPS_JSON = os.path.join(LOG_DIR, "proposed_caps.json")

def load_caps():
    caps = DEFAULT_CAPS
    if os.path.exists(CAPS_JSON):
        try:
            with open(CAPS_JSON, "r", encoding="utf-8") as f:
                suggested = json.load(f)
            # Merge suggested into defaults (prefer suggested if present)
            for k in caps.keys():
                if k in suggested and "absences" in suggested[k]:
                    caps[k]["absences"]["low_cap"]  = suggested[k]["absences"].get("low_cap", caps[k]["absences"]["low_cap"])
                    caps[k]["absences"]["high_cap"] = suggested[k]["absences"].get("high_cap", caps[k]["absences"]["high_cap"])
        except Exception:
            # If JSON fails for any reason, just use defaults
            pass
    return caps

def cap_series(s, low, high):
    orig = s.copy()
    if low is not None:
        s = np.where(s < low, low, s)
    if high is not None:
        s = np.where(s > high, high, s)
    s = pd.to_numeric(s, errors="coerce")
    n_changed = int((pd.Series(orig) != pd.Series(s)).sum())
    return pd.Series(s), n_changed

def process_one(key, paths, caps):
    df = pd.read_csv(paths["in"])
    summary_lines = []

    # Ensure numeric for target columns
    for c in ["age", "absences", "G1", "G2", "G3"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Apply absences cap if present
    changed_total = 0
    cdef = caps.get(key, {}).get("absences", {})
    low_cap = cdef.get("low_cap", None)
    high_cap = cdef.get("high_cap", None)

    if "absences" in df.columns:
        capped, n_changed = cap_series(df["absences"], low_cap, high_cap)
        df["absences"] = capped
        changed_total += n_changed
        summary_lines.append("{}: absences cap -> low={}, high={}, changed={} rows".format(
            key, low_cap, high_cap, n_changed
        ))
    else:
        summary_lines.append("{}: absences column not found".format(key))

    # Export v2
    df.to_csv(paths["out"], index=False)
    summary_lines.append("{}: wrote {}".format(key, paths["out"]))
    return "\n".join(summary_lines)

def main():
    caps = load_caps()
    lines = ["# Caps summary (v2 export)"]
    for key, paths in FILES.items():
        if not os.path.exists(paths["in"]):
            lines.append("{}: MISSING input {}".format(key, paths["in"]))
            continue
        lines.append(process_one(key, paths, caps))

    out_log = os.path.join(LOG_DIR, "caps_summary.txt")
    with open(out_log, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print("Wrote {}".format(out_log))

if __name__ == "__main__":
    main()
