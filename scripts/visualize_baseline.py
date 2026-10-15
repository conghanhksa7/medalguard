"""Visualize Baseline C0 Results — charts + data-driven summary for the GVHD report.

Outputs (results/baseline/):
  - blast_radius_by_mutation.png
  - outcome_by_category.png
  - pipeline_overhead.png
  - baseline_c0_summary.json
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "baseline"
results = json.loads((RESULTS_DIR / "baseline_c0_results.json").read_text(encoding="utf-8"))
overhead = json.loads((RESULTS_DIR / "baseline_c0_overhead.json").read_text(encoding="utf-8"))

faults = [r for r in results if r["category"] != "BENIGN"]
benign = [r for r in results if r["category"] == "BENIGN"]


def outcome(r):
    """Classify what happened to a fault under C0."""
    if r["pipeline_status"] == "CRASH":
        return "CRASH"                      # pipeline broke (accidental protection)
    if r["fault_propagated_to_gold"]:
        return "SILENT_PROPAGATION"         # SUCCESS + Gold corrupted
    return "NEUTRALISED"                    # SUCCESS + Gold identical to clean


for r in faults:
    r["outcome"] = outcome(r)

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
cats = {}
for r in faults:
    c = cats.setdefault(r["category"], {"n": 0, "det": 0, "br": 0.0,
                                          "CRASH": 0, "SILENT_PROPAGATION": 0, "NEUTRALISED": 0})
    c["n"] += 1; c["det"] += int(r["detected"]); c["br"] += r["blast_radius"]; c[r["outcome"]] += 1

per_category = [{
    "category": k, "mutations": v["n"],
    "detection_rate_pct": round(v["det"] / v["n"] * 100, 1),
    "avg_blast_radius_pct": round(v["br"] / v["n"] * 100, 1),
    "crash": v["CRASH"], "silent_propagation": v["SILENT_PROPAGATION"], "neutralised": v["NEUTRALISED"],
} for k, v in cats.items()]

n_f = len(faults)
counts = {o: sum(r["outcome"] == o for r in faults) for o in ("CRASH", "SILENT_PROPAGATION", "NEUTRALISED")}
silent = [r for r in faults if r["outcome"] == "SILENT_PROPAGATION"]
by = {r["mutation"]: r for r in faults}

wall = overhead.get("wall", {"median_ms": overhead["median_ms"], "stdev_ms": overhead["stdev_ms"]})
dbt_el = overhead.get("dbt_elapsed", {})

summary = {
    "config": "C0 (No Enforcement)",
    "dataset": "TPC-H SF=0.1 (866,602 rows)",
    "blast_radius_definition": ("BR = |Gold rows deviating from clean reference (changed, missing or "
                                "unexpected)| / |Gold rows in reference ∪ current|; CRASH -> 0 (ASSIGNED_CRASH)"),
    "overall": {
        "detection_rate": f"0/{n_f} = 0%" if not any(r["detected"] for r in faults) else "see data",
        "false_positive_rate": f"{sum(r['detected'] for r in benign)}/{len(benign)}",
        "avg_blast_radius_all_faults_pct": round(sum(r["blast_radius"] for r in faults) / n_f * 100, 1),
        "avg_blast_radius_silent_only_pct": round(sum(r["blast_radius"] for r in silent) / len(silent) * 100, 1) if silent else 0,
        "outcomes": counts,
        "pipeline_wall_median_ms": wall["median_ms"],
        "pipeline_wall_stdev_ms": wall["stdev_ms"],
        "dbt_elapsed_median_ms": dbt_el.get("median_ms"),
        "dbt_elapsed_stdev_ms": dbt_el.get("stdev_ms"),
    },
    "per_category": per_category,
    "key_findings": [
        f"{counts['SILENT_PROPAGATION']}/{n_f} faults corrupt Gold while the pipeline reports SUCCESS "
        f"(silent propagation): {', '.join(r['mutation'] for r in silent)}.",
        f"M5a (discount x100) and M5b (x1.5) each corrupt {by['M5a_MULTIPLY_100']['gold_deviated_rows']}/"
        f"{by['M5a_MULTIPLY_100']['gold_total_rows']} Gold rows (BR {by['M5a_MULTIPLY_100']['blast_radius']:.1%}).",
        f"Even tiny injections propagate: M4b injects only {by['M4b_NullSmall']['inject_count']} NULL keys yet "
        f"changes {by['M4b_NullSmall']['gold_deviated_rows']} Gold rows; M4c ({by['M4c_DuplicateKeys']['inject_count']} "
        f"duplicate PKs) changes {by['M4c_DuplicateKeys']['gold_deviated_rows']} rows.",
        f"All {cats.get('TYPE_CHANGE', {}).get('n', 0)} type mutations are NEUTRALISED: Silver CASTs restore the "
        "type, so Gold is bit-identical. The schema contract is violated but data is not corrupted — "
        "a latent risk, not an observable failure (important for interpreting Detection Rate).",
        f"All {cats.get('DESTRUCTIVE', {}).get('n', 0)} destructive mutations CRASH the pipeline: "
        "protection by accident, with no diagnosis of the root cause.",
        "Additive mutations are harmless (explicit SELECT in Silver).",
        "Gold-row BR understates severity for small injections because Gold is aggregated; "
        "report BR together with the binary 'propagated' outcome.",
        f"Benign mutations: FPR = 0/{len(benign)} trivially (C0 raises no alarms). Some benign mutations "
        "legitimately change Gold (e.g. B2 value shift) — a value-diff alone cannot separate fault from benign, "
        "which motivates contract-based validation.",
    ],
}
(RESULTS_DIR / "baseline_c0_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print("✅ Summary saved")

# ------------------------------------------------------------------
# Charts
# ------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
plt.rcParams.update({"font.size": 10, "figure.dpi": 150})

cat_colors = {"ADDITIVE": "#4CAF50", "DESTRUCTIVE": "#F44336", "TYPE_CHANGE": "#FF9800",
              "CONSTRAINT_BREACH": "#9C27B0", "SEMANTIC_DRIFT": "#2196F3"}

# Chart 1 — measured BR per mutation, annotated with outcome
fig, ax = plt.subplots(figsize=(14, 6))
vals = [r["blast_radius"] * 100 for r in faults]
bars = ax.bar(range(n_f), vals, color=[cat_colors[r["category"]] for r in faults], edgecolor="black", linewidth=0.6)
labels_map = {"CRASH": "CRASH", "NEUTRALISED": "0 dev", "SILENT_PROPAGATION": None}
for i, r in enumerate(faults):
    txt = labels_map[r["outcome"]] or f"{r['blast_radius']:.1%}\n({r['gold_deviated_rows']}/{r['gold_total_rows']})"
    ax.text(i, vals[i] + 1.5, txt, ha="center", va="bottom", fontsize=7,
            color="red" if r["outcome"] == "SILENT_PROPAGATION" else "dimgray")
ax.set_xticks(range(n_f))
ax.set_xticklabels([r["mutation"] for r in faults], rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Measured Blast Radius (% Gold rows deviating)")
ax.set_ylim(0, 110)
ax.set_title("C0 Baseline — Measured Blast Radius per Fault Mutation (diff vs. clean Gold reference)")
ax.legend(handles=[mpatches.Patch(color=c, label=k) for k, c in cat_colors.items()], fontsize=8, loc="upper left")
plt.tight_layout(); fig.savefig(RESULTS_DIR / "blast_radius_by_mutation.png", bbox_inches="tight"); plt.close(fig)

# Chart 2 — outcome distribution per category (stacked)
fig, ax = plt.subplots(figsize=(10, 4.5))
names = [p["category"] for p in per_category]
o_cols = {"silent_propagation": ("#D32F2F", "Silent propagation (SUCCESS + Gold corrupted)"),
          "crash": ("#757575", "Pipeline crash"),
          "neutralised": ("#81C784", "Neutralised (Gold identical)")}
left = [0] * len(names)
for key, (col, lab) in o_cols.items():
    v = [p[key] for p in per_category]
    ax.barh(names, v, left=left, color=col, label=lab, edgecolor="white")
    left = [a + b for a, b in zip(left, v)]
ax.set_xticks([0, 1, 2, 3]); ax.set_xlabel("Number of mutations")
ax.set_title("C0 Baseline — Fault outcome by category (Detection Rate = 0% in all categories)")
ax.legend(fontsize=8, loc="lower right")
plt.tight_layout(); fig.savefig(RESULTS_DIR / "outcome_by_category.png", bbox_inches="tight"); plt.close(fig)
old = RESULTS_DIR / "summary_by_category.png"
if old.exists():
    old.unlink()

# Chart 3 — overhead: wall vs dbt elapsed
fig, ax = plt.subplots(figsize=(9, 4))
w = overhead.get("wall", {}).get("values_ms", overhead["times_ms"])
d = overhead.get("dbt_elapsed", {}).get("values_ms")
x = range(1, len(w) + 1)
ax.bar([i - 0.2 for i in x], w, width=0.4, color="#607D8B", label=f"Wall-clock (median {wall['median_ms']:.0f} ms)")
if d:
    ax.bar([i + 0.2 for i in x], d, width=0.4, color="#FFB300", label=f"dbt elapsed (median {dbt_el['median_ms']:.0f} ms)")
ax.set_xticks(list(x)); ax.set_ylim(0, 9600); ax.set_xlabel("Run #"); ax.set_ylabel("Time (ms)")
ax.set_title("C0 Baseline — Pipeline time, 7 runs on clean data (TPC-H SF=0.1)")
ax.legend(fontsize=8)
plt.tight_layout(); fig.savefig(RESULTS_DIR / "pipeline_overhead.png", bbox_inches="tight"); plt.close(fig)
print("✅ Charts saved")

# ------------------------------------------------------------------
print(json.dumps(summary["overall"], indent=2, ensure_ascii=False))
for p in per_category:
    print(p)
for i, f in enumerate(summary["key_findings"], 1):
    print(f"{i}. {f}")
