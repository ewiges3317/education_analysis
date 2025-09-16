# scripts/clean_v1_enforce_types.py
"""
STEP TRACKING
- Step: Enforce dtypes + export v1 clean
- Objective: Ensure numeric columns are numeric, categorical are strings; save clean CSVs
- Expected: data_clean/student-mat_clean_v1.csv and student-por_clean_v1.csv written
"""

import os
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(ROOT, "data_raw", "student")
OUT_DIR = os.path.join(ROOT, "data_clean")
LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

files = {
    "mat": os.path.join(RAW_DIR, "student-mat.csv"),
    "por": os.path.join(RAW_DIR, "student-por.csv"),
}

num_cols = ["age", "absences", "G1", "G2", "G3"]
# columns that are basically yes/no flags we keep as string "no"/"yes" for interpretability
flag_cols = ["schoolsup","famsup","paid","activities","nursery","higher","internet","romantic"]

def load_df(path):
    return pd.read_csv(path, sep=";", engine="python")

def coerce_types(df):
    # numeric
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # strip whitespace on object columns
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = df[c].astype(str).str.strip()
    return df

def write_preview(df, name):
    prev = df[num_cols].describe().to_string()
    with open(os.path.join(LOG_DIR, f"preview_{name}.txt"), "w", encoding="utf-8") as f:
        f.write(prev)

def process(name, path):
    df = load_df(path)
    df = coerce_types(df)

    # sanity: drop rows with all three grades missing (should be none in this dataset)
    if all(c in df.columns for c in ["G1","G2","G3"]):
        df = df[~(df["G1"].isna() & df["G2"].isna() & df["G3"].isna())].copy()

    # export
    out_path = os.path.join(OUT_DIR, f"student-{name}_clean_v1.csv")
    df.to_csv(out_path, index=False)
    write_preview(df, name)
    print(f"Wrote {out_path} (rows={len(df)})")

if __name__ == "__main__":
    for name, path in files.items():
        process(name, path)
    print("Clean v1 export complete.")
