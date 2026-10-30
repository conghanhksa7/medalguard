"""
Publication-Quality Visualization Script for MedalGuard Phase 2 Experiments
===========================================================================
Generates 6 IEEE/ACM-standard charts at 300 DPI:
  - fig1_detection_and_fpr_comparison.png (Panel A: Core 19, Panel B: Expanded 36 with 95% Wilson CI)
  - fig2_blast_radius_heatmap.png (24 Harmful Scenarios × 5 Configs with outcome labels)
  - fig3_detection_depth_and_boundary_ablation.png (Panel A: Stage/Depth distribution, Panel B: Boundary ablation B1, B2, C3_DUAL)
  - fig4_validator_ablation_study.png (Detection rates of A1..A6 vs C3 across mutation categories)
  - fig5_overhead_and_scale_stress_test.png (Panel A: Latency breakdown @ SF=0.1 & SF=1.0, Panel B: Scaling model curves)
  - fig6_ct3_pilot_mttd_mttr_recovery.png (Panel A: MTTD vs MTTR across 3 use cases, Panel B: Blast radius before/after replay)

Outputs saved to results/charts/
"""

import json
import math
import statistics
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUMMARY_DIR = PROJECT_ROOT / "results" / "summary"
CHARTS_DIR = PROJECT_ROOT / "results" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Global Plot Styling (IEEE/ACM Academic Standard)
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans", "Helvetica"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.labelweight": "bold",
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 14,
    "figure.titleweight": "bold",
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

CONFIG_COLORS = {
    "C0": "#7f8c8d",          # Baseline (Gray)
    "C1": "#e67e22",          # dbt Contracts (Orange)
    "C2": "#f39c12",          # Great Expectations (Amber)
    "C3_standalone": "#16a085",# Standalone Gate (Teal)
    "C3": "#2c3e50",          # MedalGuard In-line (Navy Dark)
    "C3_DUAL_GATE": "#2c3e50",
    "B1_GATE1_ONLY": "#3498db",# Gate 1 Only (Sky Blue)
    "B2_GATE2_ONLY": "#e74c3c",# Gate 2 Only (Coral Red)
}


# ===========================================================================
# Figure 1: Detection Rate, Ingest Correctness, SLA & FPR Comparison
# ===========================================================================
def plot_fig1():
    stat_path = SUMMARY_DIR / "e1_paired_statistical_ci.json"
    with open(stat_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), sharey=True)

    configs = ["C0", "C1", "C2", "C3_standalone", "C3"]
    cfg_labels = ["C0\n(Baseline)", "C1\n(dbt Contracts)", "C2\n(Great Exp.)", "C3_standalone\n(MedalGuard)", "C3\n(In-line Gate)"]

    metrics = [
        ("detection_rate_pct", "detection_rate_ci_95", "Detection Rate (DR %)", "#2980b9"),
        ("ingest_correctness_rate_pct", None, "Ingest Correctness (%)", "#27ae60"),
        ("sla_attainment_rate_pct", None, "SLA Attainment (%)", "#8e44ad"),
        ("false_positive_rate_pct", "false_positive_rate_ci_95", "False Positive Rate (%)", "#c0392b"),
    ]

    for ax_idx, (suite_key, title) in enumerate([("core19", "Panel A: Core 19 Benchmark (14 Harmful + 5 Benign)"),
                                                 ("expanded36", "Panel B: Expanded 36 Benchmark (24 Harmful + 12 Benign)")]):
        ax = axes[ax_idx]
        suite_cfgs = data[suite_key]["configs"]

        x = np.arange(len(configs))
        width = 0.21

        for m_idx, (m_key, ci_key, m_label, color) in enumerate(metrics):
            vals = [suite_cfgs[c][m_key] for c in configs]
            pos = x + (m_idx - 1.5) * width

            # Compute error bars if CI available
            yerr = None
            if ci_key:
                err_low = []
                err_high = []
                for c in configs:
                    ci = suite_cfgs[c][ci_key]
                    val = suite_cfgs[c][m_key]
                    err_low.append(max(0.0, val - ci[0]))
                    err_high.append(max(0.0, ci[1] - val))
                yerr = [err_low, err_high]

            bars = ax.bar(pos, vals, width, yerr=yerr, capsize=3, label=m_label if ax_idx == 0 else "",
                          color=color, alpha=0.88, edgecolor="black", linewidth=0.7)

            # Direct data labels with alternating vertical offsets to prevent label collision
            for bar, val in zip(bars, vals):
                if val > 0:
                    y_off = 3 + (m_idx % 2) * 6
                    ax.annotate(f"{val:.0f}%",
                                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                                xytext=(0, y_off), textcoords="offset points",
                                ha="center", va="bottom", fontsize=7.0, weight="bold", rotation=0)

        ax.set_title(title, pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels(cfg_labels)
        ax.set_ylim(0, 115)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(100))
        ax.grid(axis="y", linestyle="--", alpha=0.6)

    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.05), ncol=4, frameon=True, fontsize=10)
    out_path = CHARTS_DIR / "fig1_detection_and_fpr_comparison.png"
    plt.savefig(out_path)
    plt.close()
    print(f"  [Chart] Saved {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# ===========================================================================
# Figure 2: Blast Radius Heatmap (24 Harmful Scenarios × 5 Configs)
# ===========================================================================
def plot_fig2():
    json_path = SUMMARY_DIR / "e1_main_matrix_expanded36.json"
    with open(json_path, "r", encoding="utf-8") as f:
        runs = json.load(f)

    harmful_runs = [r for r in runs if r["category"] != "BENIGN"]
    mut_names = sorted(list(set(r["mutation_name"] for r in harmful_runs)))
    configs = ["C0", "C1", "C2", "C3_standalone", "C3"]

    matrix_br = np.zeros((len(mut_names), len(configs)))
    annot_text = []

    for i, mname in enumerate(mut_names):
        row_annot = []
        for j, cname in enumerate(configs):
            matched = [r for r in harmful_runs if r["mutation_name"] == mname and r["config_name"] == cname]
            if matched:
                r = matched[0]
                br = r["blast_radius"] * 100.0
                matrix_br[i, j] = br
                status = r["pipeline_status"]
                det = r["detected"]
                stage = r["detection_stage"]
                q = r.get("quarantined_rows", 0)

                if status == "CRASH":
                    lbl = "CRASH\n(0.0%)"
                elif q > 0 and r.get("quarantine_effective", False):
                    lbl = f"QUAR\n({q} rows)"
                elif det and stage == "PRE_TRANSFORM":
                    lbl = "G1 BLK\n(0.0%)"
                elif det and stage == "SILVER_CONTRACT":
                    lbl = "S-CON\n(0.0%)"
                elif det and stage == "POST_TRANSFORM":
                    lbl = f"POST BLK\n({br:.1f}%)"
                else:
                    lbl = f"SILENT\n({br:.1f}%)"
                row_annot.append(lbl)
            else:
                row_annot.append("—")
        annot_text.append(row_annot)

    fig, ax = plt.subplots(figsize=(10, 13))
    cmap = sns.color_palette("YlOrRd", as_cmap=True)

    sns.heatmap(matrix_br, annot=annot_text, fmt="", cmap=cmap, cbar_kws={'label': 'Blast Radius at Gold Table (%)'},
                xticklabels=["C0 (Baseline)", "C1 (dbt Contracts)", "C2 (GX Post)", "C3_standalone (MedalGuard)", "C3 (In-line Dual-Gate)"],
                yticklabels=mut_names, linewidths=0.6, linecolor="#bdc3c7", ax=ax,
                annot_kws={"size": 7.5, "weight": "bold"})

    ax.set_title("Blast Radius & Failure Outcome Heatmap (24 Harmful Scenarios × 5 Configs)", pad=16, fontsize=12)
    ax.tick_params(axis='x', rotation=15)
    ax.tick_params(axis='y', rotation=0)

    out_path = CHARTS_DIR / "fig2_blast_radius_heatmap.png"
    plt.savefig(out_path)
    plt.close()
    print(f"  [Chart] Saved {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# ===========================================================================
# Figure 3: Detection Depth & Boundary Placement Ablation
# ===========================================================================
def plot_fig3():
    e1_path = SUMMARY_DIR / "e1_main_matrix_expanded36.json"
    e2b_path = SUMMARY_DIR / "e2_ablation_boundaries.json"

    with open(e1_path, "r", encoding="utf-8") as f:
        e1_runs = json.load(f)
    with open(e2b_path, "r", encoding="utf-8") as f:
        e2b_runs = json.load(f)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Panel A: Detection Depth Breakdown in E1
    configs = ["C0", "C1", "C2", "C3_standalone", "C3"]
    harmful_e1 = [r for r in e1_runs if r["category"] != "BENIGN"]

    stages = ["Gate 1 (Pre-transform)", "Silver Contract", "Gate 2 / GX (Post-transform)", "Pipeline Crash", "Undetected (Silent)"]
    stage_colors = ["#27ae60", "#2980b9", "#f39c12", "#e74c3c", "#7f8c8d"]

    stage_counts = {s: [] for s in stages}

    for c in configs:
        c_runs = [r for r in harmful_e1 if r["config_name"] == c]
        tot = len(c_runs)
        g1 = sum(1 for r in c_runs if r["detected"] and r["detection_stage"] == "PRE_TRANSFORM")
        s_con = sum(1 for r in c_runs if r["detected"] and r["detection_stage"] == "SILVER_CONTRACT")
        post = sum(1 for r in c_runs if r["detected"] and r["detection_stage"] == "POST_TRANSFORM")
        crash = sum(1 for r in c_runs if not r["detected"] and r["pipeline_status"] == "CRASH")
        undet = sum(1 for r in c_runs if not r["detected"] and r["pipeline_status"] != "CRASH")

        stage_counts["Gate 1 (Pre-transform)"].append(g1 / tot * 100.0)
        stage_counts["Silver Contract"].append(s_con / tot * 100.0)
        stage_counts["Gate 2 / GX (Post-transform)"].append(post / tot * 100.0)
        stage_counts["Pipeline Crash"].append(crash / tot * 100.0)
        stage_counts["Undetected (Silent)"].append(undet / tot * 100.0)

    bottom = np.zeros(len(configs))
    for s, col in zip(stages, stage_colors):
        vals = stage_counts[s]
        ax1.bar(configs, vals, bottom=bottom, label=s, color=col, width=0.55, edgecolor="black", linewidth=0.6)
        bottom += np.array(vals)

    ax1.set_title("Panel A: Failure Interception Depth Distribution (E1)", pad=12)
    ax1.set_ylabel("Share of 24 Harmful Scenarios (%)")
    ax1.set_ylim(0, 105)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter(100))
    ax1.legend(loc="upper left", frameon=True, fontsize=8.5)
    ax1.grid(axis="y", linestyle="--", alpha=0.6)

    # Panel B: Boundary Placement Ablation (B1 vs B2 vs C3_DUAL)
    b_cfgs = ["B1_GATE1_ONLY", "B2_GATE2_ONLY", "C3_DUAL_GATE"]
    b_labels = ["Gate 1 Only\n(Bronze->Silver)", "Gate 2 Only\n(Silver->Gold)", "Dual-Boundary Gate\n(Gate 1 + Gate 2)"]

    dr_vals = []
    br_vals = []
    crash_vals = []

    for b in b_cfgs:
        b_runs = [r for r in e2b_runs if r["config_name"] == b]
        tot = len(b_runs)
        dr_vals.append(sum(1 for r in b_runs if r["detected"]) / tot * 100.0)
        br_vals.append(statistics.mean([r["blast_radius"] * 100.0 for r in b_runs]))
        crash_vals.append(sum(1 for r in b_runs if r["pipeline_status"] == "CRASH") / tot * 100.0)

    x2 = np.arange(len(b_cfgs))
    w2 = 0.25

    b1 = ax2.bar(x2 - w2, dr_vals, w2, label="Detection Rate (%)", color="#2980b9", edgecolor="black", linewidth=0.6)
    b2 = ax2.bar(x2, br_vals, w2, label="Mean Blast Radius (%)", color="#e74c3c", edgecolor="black", linewidth=0.6)
    b3 = ax2.bar(x2 + w2, crash_vals, w2, label="Pipeline Crash Rate (%)", color="#e67e22", edgecolor="black", linewidth=0.6)

    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            if h >= 0:
                ax2.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h),
                             xytext=(0, 3), textcoords="offset points",
                             ha="center", va="bottom", fontsize=8, weight="bold")

    ax2.set_title("Panel B: Architectural Boundary Ablation (E2b)", pad=12)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(b_labels)
    ax2.set_ylim(0, 128)
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(100))
    ax2.legend(loc="upper center", ncol=1, frameon=True, fontsize=8.5)
    ax2.grid(axis="y", linestyle="--", alpha=0.6)

    out_path = CHARTS_DIR / "fig3_detection_depth_and_boundary_ablation.png"
    plt.savefig(out_path)
    plt.close()
    print(f"  [Chart] Saved {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# ===========================================================================
# Figure 4: Validator Ablation Study (A1..A6 vs C3_standalone)
# ===========================================================================
def plot_fig4():
    e2a_path = SUMMARY_DIR / "e2_ablation_validators.json"
    with open(e2a_path, "r", encoding="utf-8") as f:
        runs = json.load(f)

    cfg_names = ["C3_standalone", "A1_NO_SCHEMA", "A2_NO_CONSTRAINT", "A3_NO_SEMANTIC", "A4_SCHEMA_ONLY", "A5_CONSTRAINT_ONLY", "A6_SEMANTIC_ONLY"]
    cfg_labels = ["C3 (Full)", "A1 (No Schema)", "A2 (No Constraint)", "A3 (No Semantic)", "A4 (Schema Only)", "A5 (Constraint Only)", "A6 (Semantic Only)"]

    groups = [
        ("M1", "M1: Additive (4)"),
        ("M2", "M2: Destructive (5)"),
        ("M3", "M3: Type Change (5)"),
        ("M4", "M4: Constraint (5)"),
        ("M5", "M5: Semantic (5)"),
    ]

    fig, ax = plt.subplots(figsize=(14, 6.2))

    x = np.arange(len(cfg_names))
    width = 0.16
    colors = ["#3498db", "#e74c3c", "#9b59b6", "#2ecc71", "#f39c12"]

    for g_idx, (prefix, g_label) in enumerate(groups):
        rates = []
        for cname in cfg_names:
            matched = [r for r in runs if r["config_name"] == cname and r["mutation_name"].startswith(prefix)]
            tot = len(matched)
            det = sum(1 for r in matched if r["detected"])
            rates.append((det / tot * 100.0) if tot else 0.0)

        pos = x + (g_idx - 2) * width
        bars = ax.bar(pos, rates, width, label=g_label, color=colors[g_idx], edgecolor="black", linewidth=0.6, alpha=0.9)

        for bar, r in zip(bars, rates):
            if r > 0:
                y_off = 3 + (g_idx % 2) * 5
                ax.annotate(f"{r:.0f}%", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                            xytext=(0, y_off), textcoords="offset points", ha="center", va="bottom", fontsize=7.5, weight="bold")

    ax.set_title("Validator Module Ablation Across Failure Taxonomies (E2a - 24 Harmful Scenarios)", pad=16)
    ax.set_xticks(x)
    ax.set_xticklabels(cfg_labels, rotation=10, ha="right")
    ax.set_ylabel("Detection Rate (DR %)")
    ax.set_ylim(0, 115)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(100))
    ax.legend(loc="upper right", ncol=5, frameon=True, fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    out_path = CHARTS_DIR / "fig4_validator_ablation_study.png"
    plt.savefig(out_path)
    plt.close()
    print(f"  [Chart] Saved {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# ===========================================================================
# Figure 5: Overhead Decomposition & Scaling Benchmark
# ===========================================================================
def plot_fig5():
    e3_path = SUMMARY_DIR / "e3_overhead_and_scaling.json"
    with open(e3_path, "r", encoding="utf-8") as f:
        e3_data = json.load(f)

    s01 = e3_data["sf01_summary"]
    s10 = e3_data["sf10_summary"]
    models = e3_data["scaling_models"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Panel A: Latency Decomposition (dbt vs Validation)
    cfgs = ["C0", "C1", "C2", "C3"]
    cfg_labels = ["C0 (Baseline)", "C1 (dbt Contracts)", "C2 (GX Post)", "C3 (MedalGuard)"]

    x = np.arange(len(cfgs))
    w = 0.35

    # SF=0.1
    dbt_01 = [s01[c]["median_dbt_ms"] for c in cfgs]
    val_01 = [s01[c]["median_val_ms"] for c in cfgs]
    p1 = ax1.bar(x - w/2, dbt_01, w, label="dbt DAG Exec (SF=0.1)", color="#34495e", edgecolor="black", linewidth=0.6)
    p2 = ax1.bar(x - w/2, val_01, w, bottom=dbt_01, label="Validation Gate (SF=0.1)", color="#1abc9c", edgecolor="black", linewidth=0.6)

    # SF=1.0
    dbt_10 = [s10[c]["median_dbt_ms"] for c in cfgs]
    val_10 = [s10[c]["median_val_ms"] for c in cfgs]
    p3 = ax1.bar(x + w/2, dbt_10, w, label="dbt DAG Exec (SF=1.0)", color="#2c3e50", alpha=0.6, edgecolor="black", linewidth=0.6)
    p4 = ax1.bar(x + w/2, val_10, w, bottom=dbt_10, label="Validation Gate (SF=1.0)", color="#16a085", alpha=0.6, edgecolor="black", linewidth=0.6)

    # Labels on top
    for i in range(len(cfgs)):
        tot01 = dbt_01[i] + val_01[i]
        tot10 = dbt_10[i] + val_10[i]
        ax1.annotate(f"{tot01:.0f}ms", xy=(x[i] - w/2, tot01), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7.5, weight="bold")
        ax1.annotate(f"{tot10:.0f}ms", xy=(x[i] + w/2, tot10), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7.5, weight="bold")

    ax1.set_title("Panel A: Execution Time Decomposition (E3a & E3b)", pad=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(cfg_labels, rotation=10, ha="right")
    ax1.set_ylabel("Execution Time (ms)")
    ax1.legend(loc="upper left", frameon=True, fontsize=8)
    ax1.grid(axis="y", linestyle="--", alpha=0.6)

    # Panel B: Scaling Curve Projections
    sf_points = np.array([0.1, 1.0, 3.0, 5.0, 10.0])
    line_styles = {"C0": ("--", "#7f8c8d"), "C1": (":", "#e67e22"), "C2": ("-.", "#f39c12"), "C3": ("-", "#2c3e50")}

    for c in cfgs:
        m = models[c]
        intercept = m["intercept_ms"]
        slope = m["slope_ms_per_sf"]
        projected = (intercept + slope * sf_points) / 1000.0  # seconds

        ls, col = line_styles[c]
        ax2.plot(sf_points, projected, linestyle=ls, color=col, linewidth=2.0, marker="o" if c == "C3" else "s", label=f"{c}: T = {intercept:.0f} + {slope:.0f}×SF")

    ax2.set_title("Panel B: Empirical Pipeline Scaling Curve T(SF)", pad=12)
    ax2.set_xlabel("Scale Factor (SF)")
    ax2.set_ylabel("Pipeline Wall-Clock Time (seconds)")
    ax2.legend(loc="upper left", frameon=True, fontsize=8.5)
    ax2.grid(True, linestyle="--", alpha=0.6)

    out_path = CHARTS_DIR / "fig5_overhead_and_scale_stress_test.png"
    plt.savefig(out_path)
    plt.close()
    print(f"  [Chart] Saved {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


# ===========================================================================
# Figure 6: CT3 Pilot MTTD, MTTR & Blast Radius Recovery
# ===========================================================================
def plot_fig6():
    pilot_path = SUMMARY_DIR / "ct3_pilot_use_cases.json"
    with open(pilot_path, "r", encoding="utf-8") as f:
        pilot_data = json.load(f)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    ucs = ["UC1", "UC2", "UC3"]
    uc_map = {uc["use_case_id"].split("_")[0]: uc for uc in pilot_data.get("use_cases", [])}
    uc_labels = [
        "UC1: Schema Evolution\n(M1a Allowlist l_promo_code)",
        "UC2: Row Corruption\n(M4a+M4c Quarantine & Replay)",
        "UC3: Catastrophic Drift\n(M5a Discount ×100 Rollback)"
    ]

    mttd = [uc_map[uc]["mttd_ms"] for uc in ucs]
    mttr = [uc_map[uc]["mttr_ms"] for uc in ucs]

    x = np.arange(len(ucs))
    w = 0.35

    # Panel A: MTTD vs MTTR
    b1 = ax1.bar(x - w/2, mttd, w, label="MTTD (Detection Latency)", color="#2980b9", edgecolor="black", linewidth=0.6)
    b2 = ax1.bar(x + w/2, mttr, w, label="MTTR (Recovery Latency)", color="#e67e22", edgecolor="black", linewidth=0.6)

    for bar, val in zip(b1, mttd):
        ax1.annotate(f"{val:.1f}ms", xy=(bar.get_x() + bar.get_width() / 2, val),
                     xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8, weight="bold")
    for bar, val in zip(b2, mttr):
        ax1.annotate(f"{val:.1f}ms", xy=(bar.get_x() + bar.get_width() / 2, val),
                     xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8, weight="bold")

    ax1.set_title("Panel A: MTTD and MTTR Across 3 Real-World Pilots (CT3)", pad=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(uc_labels)
    ax1.set_ylabel("Latency (ms)")
    ax1.set_yscale("log")
    ax1.set_ylim(10, 45000)
    ax1.legend(loc="upper left", frameon=True, fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.6)

    # Panel B: Blast Radius Before vs After Recovery
    br_before = [uc_map[uc]["pre_remediation_blast_radius"] * 100.0 for uc in ucs]
    br_after = [uc_map[uc]["post_remediation_blast_radius"] * 100.0 for uc in ucs]

    bb1 = ax2.bar(x - w/2, br_before, w, label="Blast Radius (Before Recovery)", color="#c0392b", edgecolor="black", linewidth=0.6)
    bb2 = ax2.bar(x + w/2, br_after, w, label="Blast Radius (After Replay/Rollback)", color="#27ae60", edgecolor="black", linewidth=0.6)

    for bar, val in zip(bb1, br_before):
        ax2.annotate(f"{val:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, val),
                     xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8, weight="bold")
    for bar, val in zip(bb2, br_after):
        ax2.annotate(f"{val:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, val),
                     xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8, weight="bold")

    ax2.set_title("Panel B: Blast Radius Before vs After Automated Healing", pad=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(uc_labels)
    ax2.set_ylabel("Blast Radius at Gold Table (%)")
    ax2.set_ylim(0, 30)
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(100))
    ax2.legend(loc="upper right", frameon=True, fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.6)

    out_path = CHARTS_DIR / "fig6_ct3_pilot_mttd_mttr_recovery.png"
    plt.savefig(out_path)
    plt.close()
    print(f"  [Chart] Saved {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


def main():
    print("=" * 80)
    print("  GENERATING 6 PUBLICATION-QUALITY CHARTS (300 DPI)")
    print("=" * 80)
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_fig5()
    plot_fig6()
    print("=" * 80)
    print("  ALL 6 CHARTS SUCCESSFULLY GENERATED IN results/charts/")
    print("=" * 80)


if __name__ == "__main__":
    main()
