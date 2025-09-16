# scripts/eda_explore.py
"""
STEP TRACKING
- Step: Exploratory Data Analysis
- Objective: Correlations, scatterplots, boxplots by attendance tier; export tables + charts
- Inputs: data_clean/student-mat_clean_v2.csv, student-por_clean_v2.csv
- Outputs:
    visualizations/absences_vs_g3_math.png
    visualizations/absences_vs_g3_portuguese.png
    visualizations/box_g3_by_tier_math.png
    visualizations/box_g3_by_tier_portuguese.png
    data_clean/derived/math_g3_by_att_tier.csv
    data_clean/derived/port_g3_by_att_tier.csv
    logs/eda_summary.txt
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLEAN = os.path.join(ROOT, "data_clean")
DERIVED = os.path.join(CLEAN, "derived")
VIZ = os.path.join(ROOT, "visualizations")
LOGS = os.path.join(ROOT, "logs")
os.makedirs(DERIVED, exist_ok=True)
os.makedirs(VIZ, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

def attendance_tier(x):
    try:
        x = float(x)
    except Exception:
        return "Unknown"
    if x <= 5: return "High"
    if x <= 15: return "Moderate"
    return "Low"

def load_v2(name):
    path = os.path.join(CLEAN, "student-{}_clean_v2.csv".format(name))
    df = pd.read_csv(path)
    # numeric enforcement
    for c in ["absences", "G1", "G2", "G3", "age"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["att_tier"] = df["absences"].apply(attendance_tier)
    return df

def corr_block(df, label):
    cols = [c for c in ["absences","G1","G2","G3"] if c in df.columns]
    corr = df[cols].corr(method="pearson")
    return "== {} correlations ==\n{}\n".format(label, corr.to_string())

def scatter_with_trend(df, title, out_png):
    x = df["absences"].values
    y = df["G3"].values
    # trendline via polyfit if enough data
    if len(x) >= 2 and np.isfinite(x).sum() > 2 and np.isfinite(y).sum() > 2:
        m, b = np.polyfit(x, y, 1)
    else:
        m, b = 0.0, float(np.nan)

    plt.figure()
    plt.scatter(x, y, s=12)
    if np.isfinite(m) and np.isfinite(b):
        xline = np.linspace(np.nanmin(x), np.nanmax(x), 100)
        yline = m * xline + b
        plt.plot(xline, yline)
    plt.title(title)
    plt.xlabel("Absences")
    plt.ylabel("G3 (Final Grade)")
    plt.tight_layout()
    plt.savefig(out_png, bbox_inches="tight")
    plt.close()
    return m, b

def box_by_tier(df, title, out_png):
    order = ["High","Moderate","Low"]
    data = [df.loc[df["att_tier"]==t, "G3"].dropna().values for t in order]
    plt.figure()
    plt.boxplot(data, labels=order, showfliers=True)
    plt.title(title)
    plt.xlabel("Attendance Tier")
    plt.ylabel("G3 (Final Grade)")
    plt.tight_layout()
    plt.savefig(out_png, bbox_inches="tight")
    plt.close()

def tier_table(df):
    out = df.groupby("att_tier")["G3"].agg(["count","mean"]).reset_index()
    return out.sort_values("att_tier")

def main():
    log_lines = []

    # Load
    mat = load_v2("mat")
    por = load_v2("por")
    log_lines.append("Loaded MAT rows={}, POR rows={}".format(len(mat), len(por)))

    # Correlations
    log_lines.append(corr_block(mat, "Math"))
    log_lines.append(corr_block(por, "Portuguese"))

    # Scatterplots + trendlines
    m_mat, b_mat = scatter_with_trend(mat, "Math: Absences vs G3", os.path.join(VIZ, "absences_vs_g3_math.png"))
    m_por, b_por = scatter_with_trend(por, "Portuguese: Absences vs G3", os.path.join(VIZ, "absences_vs_g3_portuguese.png"))
    log_lines.append("Math trendline: y = {:.4f}x + {:.4f}".format(m_mat, b_mat))
    log_lines.append("Portuguese trendline: y = {:.4f}x + {:.4f}".format(m_por, b_por))

    # Boxplots by tier
    box_by_tier(mat, "Math: G3 by Attendance Tier", os.path.join(VIZ, "box_g3_by_tier_math.png"))
    box_by_tier(por, "Portuguese: G3 by Attendance Tier", os.path.join(VIZ, "box_g3_by_tier_portuguese.png"))

    # Tier tables
    tmat = tier_table(mat)
    tpor = tier_table(por)
    tmat.to_csv(os.path.join(DERIVED, "math_g3_by_att_tier.csv"), index=False)
    tpor.to_csv(os.path.join(DERIVED, "port_g3_by_att_tier.csv"), index=False)

    # Save log summary
    log_path = os.path.join(LOGS, "eda_summary.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print("\n".join(log_lines))
    print("Saved charts to {}".format(VIZ))
    print("Saved tier tables to {}".format(DERIVED))
    print("Wrote {}".format(log_path))

if __name__ == "__main__":
    main()
