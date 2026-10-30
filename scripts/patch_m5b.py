"""
Surgical Patch for M5b_MULTIPLY_1_5
===================================
Re-runs M5b_MULTIPLY_1_5 across E1 and E2 configs,
updates JSON and CSV results, and re-generates summary tables.
"""

import os
import sys
import json
import time
from pathlib import Path
import statistics
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.runner import (
    run_single_experiment,
    build_clean_reference,
    _load_config,
    DB_PATH,
)
from mutations import get_mutation_suite
from scripts.run_phase2_experiments import (
    SUMMARY_DIR,
    save_csv,
    wilson_score_interval,
    bootstrap_ci,
    bootstrap_paired_diff_ci,
    mcnemar_exact_test,
    generate_e1_markdown,
    generate_e2_markdown,
)

def patch_m5b():
    print("=" * 80)
    print("  SURGICAL RE-EXECUTION FOR M5b_MULTIPLY_1_5")
    print("=" * 80)

    cfg_data = _load_config()
    configs = cfg_data.get("configs", {})
    ablation_cfgs = cfg_data.get("ablation", {})
    boundary_cfgs = cfg_data.get("boundary_ablation", {})

    print("Loading clean Gold reference...")
    reference = build_clean_reference(0.1, DB_PATH)

    mutations = {m.name: m for m in get_mutation_suite(0.1, "expanded")}
    m5b = mutations["M5b_MULTIPLY_1_5"]

    # 1. Run M5b on E1 configs
    e1_cfgs = ["C0", "C1", "C2", "C3_standalone", "C3"]
    e1_patched_runs = {}
    print("\n--- Running M5b on E1 configurations ---")
    for cname in e1_cfgs:
        cfg = configs[cname]
        t0 = time.perf_counter()
        res = run_single_experiment(m5b, cfg, cname, reference, 0.1, use_fast_bronze=True)
        el_ms = (time.perf_counter() - t0) * 1000
        e1_patched_runs[cname] = res
        print(f"  {cname:<15} -> status={res.pipeline_status:<7} det={res.detected!s:<5} DDI={res.detection_depth_index!s:<2} BR={res.blast_radius:>6.1%} ({el_ms:.1f}ms)")

    # 2. Run M5b on E2a configs
    e2a_cfgs = ["A1_NO_SCHEMA", "A2_NO_CONSTRAINT", "A3_NO_SEMANTIC", "A4_SCHEMA_ONLY", "A5_CONSTRAINT_ONLY", "A6_SEMANTIC_ONLY"]
    e2a_patched_runs = {}
    print("\n--- Running M5b on E2a configurations ---")
    for cname in e2a_cfgs:
        cfg = ablation_cfgs[cname]
        t0 = time.perf_counter()
        res = run_single_experiment(m5b, cfg, cname, reference, 0.1, use_fast_bronze=True)
        el_ms = (time.perf_counter() - t0) * 1000
        e2a_patched_runs[cname] = res
        print(f"  {cname:<18} -> status={res.pipeline_status:<7} det={res.detected!s:<5} DDI={res.detection_depth_index!s:<2} BR={res.blast_radius:>6.1%} ({el_ms:.1f}ms)")

    # 3. Run M5b on E2b configs
    e2b_cfgs = ["B1_GATE1_ONLY", "B2_GATE2_ONLY"]
    e2b_patched_runs = {}
    print("\n--- Running M5b on E2b configurations ---")
    for cname in e2b_cfgs:
        cfg = boundary_cfgs[cname]
        t0 = time.perf_counter()
        res = run_single_experiment(m5b, cfg, cname, reference, 0.1, use_fast_bronze=True)
        el_ms = (time.perf_counter() - t0) * 1000
        e2b_patched_runs[cname] = res
        print(f"  {cname:<15} -> status={res.pipeline_status:<7} det={res.detected!s:<5} DDI={res.detection_depth_index!s:<2} BR={res.blast_radius:>6.1%} ({el_ms:.1f}ms)")

    # 4. Update E1 expanded36
    exp36_path = SUMMARY_DIR / "e1_main_matrix_expanded36.json"
    with open(exp36_path, "r", encoding="utf-8") as f:
        all_e1_runs = json.load(f)

    for i, r in enumerate(all_e1_runs):
        if r["mutation_name"] == "M5b_MULTIPLY_1_5" and r["config_name"] in e1_patched_runs:
            all_e1_runs[i] = e1_patched_runs[r["config_name"]].to_dict()

    with open(exp36_path, "w", encoding="utf-8") as f:
        json.dump(all_e1_runs, f, indent=2, default=str)
    save_csv(all_e1_runs, SUMMARY_DIR / "e1_main_matrix_expanded36.csv")

    # Update E1 core19
    core19_path = SUMMARY_DIR / "e1_main_matrix_core19.json"
    with open(core19_path, "r", encoding="utf-8") as f:
        core19_runs = json.load(f)

    for i, r in enumerate(core19_runs):
        if r["mutation_name"] == "M5b_MULTIPLY_1_5" and r["config_name"] in e1_patched_runs:
            core19_runs[i] = e1_patched_runs[r["config_name"]].to_dict()

    with open(core19_path, "w", encoding="utf-8") as f:
        json.dump(core19_runs, f, indent=2, default=str)
    save_csv(core19_runs, SUMMARY_DIR / "e1_main_matrix_core19.csv")

    # 5. Recompute E1 statistics
    def compute_suite_stats(results_list: list) -> dict:
        by_cfg = {cfg: [r for r in results_list if r["config_name"] == cfg] for cfg in e1_cfgs}
        cfg_stats = {}

        for cfg_name, runs in by_cfg.items():
            harmful = [r for r in runs if r["category"] != "BENIGN"]
            benign = [r for r in runs if r["category"] == "BENIGN"]

            n_harm = len(harmful)
            n_ben = len(benign)

            det_harm = sum(1 for r in harmful if r["detected"])
            dr_pct = round((det_harm / n_harm) * 100.0, 2) if n_harm else 0.0
            dr_ci = wilson_score_interval(det_harm, n_harm)

            fp_ben = sum(1 for r in benign if r["detected"])
            fpr_pct = round((fp_ben / n_ben) * 100.0, 2) if n_ben else 0.0
            fpr_ci = wilson_score_interval(fp_ben, n_ben)

            br_vals = [r["blast_radius"] * 100.0 for r in harmful]
            mean_br = round(statistics.mean(br_vals), 2) if br_vals else 0.0
            br_ci = bootstrap_ci(br_vals)

            res_diff_vals = [r["gold_residual_diff_ratio"] * 100.0 for r in harmful]
            mean_res_diff = round(statistics.mean(res_diff_vals), 2) if res_diff_vals else 0.0

            q_runs = [r for r in harmful if r.get("quarantined_rows", 0) > 0]
            mean_qe = round(statistics.mean([r["quarantine_effectiveness_pct"] for r in q_runs]), 2) if q_runs else 0.0
            qr_vals = [r["quarantine_recall"] for r in q_runs if r.get("quarantine_recall") is not None]
            mean_qr = round(statistics.mean(qr_vals) * 100.0, 2) if qr_vals else 0.0

            cfg_stats[cfg_name] = {
                "total_runs": len(runs),
                "harmful_count": n_harm,
                "benign_count": n_ben,
                "detection_count": det_harm,
                "detection_rate_pct": dr_pct,
                "detection_rate_ci_95": dr_ci,
                "false_positive_count": fp_ben,
                "false_positive_rate_pct": fpr_pct,
                "false_positive_rate_ci_95": fpr_ci,
                "mean_blast_radius_pct": mean_br,
                "blast_radius_ci_95": br_ci,
                "mean_gold_residual_diff_pct": mean_res_diff,
                "quarantine_runs_count": len(q_runs),
                "quarantine_effectiveness_pct": mean_qe,
                "quarantine_recall_pct": mean_qr,
                "mean_pipeline_wall_ms": round(statistics.mean([r["pipeline_wall_ms"] for r in runs]), 1),
                "mean_dbt_elapsed_ms": round(statistics.mean([r["dbt_elapsed_ms"] for r in runs]), 1),
                "mean_validation_ms": round(statistics.mean([r["validation_ms"] for r in runs]), 1),
                "mean_core_execution_ms": round(statistics.mean([r["core_execution_ms"] for r in runs]), 1),
                "mean_completeness_pct": round(statistics.mean([r["completeness_pct"] for r in runs]), 2),
                "mean_validity_pct": round(statistics.mean([r["validity_pct"] for r in runs]), 2),
                "mean_duplication_rate_pct": round(statistics.mean([r["duplication_rate_pct"] for r in runs]), 2),
                "ingest_correctness_rate_pct": round(statistics.mean([100.0 if r["ingest_correctness"] else 0.0 for r in runs]), 2),
                "sla_attainment_rate_pct": round(statistics.mean([100.0 if r["sla_attained"] else 0.0 for r in runs]), 2),
            }

        # Paired comparisons vs C3
        c3_harmful_map = {r["mutation_name"]: r for r in by_cfg["C3"] if r["category"] != "BENIGN"}
        paired_vs_c3 = {}

        for cfg_name in ["C0", "C1", "C2", "C3_standalone"]:
            ci_harmful_map = {r["mutation_name"]: r for r in by_cfg[cfg_name] if r["category"] != "BENIGN"}
            common_muts = [m for m in c3_harmful_map if m in ci_harmful_map]

            c3_dets = [c3_harmful_map[m]["detected"] for m in common_muts]
            ci_dets = [ci_harmful_map[m]["detected"] for m in common_muts]
            p_val = mcnemar_exact_test(c3_dets, ci_dets)

            c3_br = [c3_harmful_map[m]["blast_radius"] * 100.0 for m in common_muts]
            ci_br = [ci_harmful_map[m]["blast_radius"] * 100.0 for m in common_muts]
            delta_br = round(statistics.mean(ci_br) - statistics.mean(c3_br), 2)
            delta_br_ci = bootstrap_paired_diff_ci(ci_br, c3_br)

            c3_dr_arr = [100.0 if d else 0.0 for d in c3_dets]
            ci_dr_arr = [100.0 if d else 0.0 for d in ci_dets]
            delta_dr = round(statistics.mean(c3_dr_arr) - statistics.mean(ci_dr_arr), 2)
            delta_dr_ci = bootstrap_paired_diff_ci(c3_dr_arr, ci_dr_arr)

            paired_vs_c3[cfg_name] = {
                "common_harmful_count": len(common_muts),
                "mcnemar_exact_pvalue": p_val,
                "delta_detection_rate_pct": delta_dr,
                "delta_detection_rate_ci_95": delta_dr_ci,
                "delta_blast_radius_pct": delta_br,
                "delta_blast_radius_ci_95": delta_br_ci,
            }

        return {"configs": cfg_stats, "paired_comparisons_vs_c3": paired_vs_c3}

    stats_core = compute_suite_stats(core19_runs)
    stats_expanded = compute_suite_stats(all_e1_runs)

    expanded_harmful = [r for r in all_e1_runs if r["category"] != "BENIGN"]
    severity_breakdown = {}
    for sev in ["CRITICAL", "HIGH", "MEDIUM"]:
        sev_runs = [r for r in expanded_harmful if r["severity"] == sev]
        sev_mut_count = len(set(r["mutation_name"] for r in sev_runs))
        sev_stats = {}
        for cfg_name in e1_cfgs:
            cfg_sev_runs = [r for r in sev_runs if r["config_name"] == cfg_name]
            det_cnt = sum(1 for r in cfg_sev_runs if r["detected"])
            rate = round((det_cnt / len(cfg_sev_runs)) * 100.0, 2) if cfg_sev_runs else 0.0
            sev_stats[cfg_name] = {
                "detected": det_cnt,
                "total": len(cfg_sev_runs),
                "detection_rate_pct": rate,
            }
        severity_breakdown[sev] = {
            "mutations_count": sev_mut_count,
            "configs": sev_stats,
        }

    full_statistical_artifact = {
        "metadata": {
            "scale_factor": 0.1,
            "total_runs": len(all_e1_runs),
            "total_mutations_expanded": 36,
            "harmful_mutations_expanded": 24,
            "benign_mutations_expanded": 12,
            "total_mutations_core": 19,
            "harmful_mutations_core": 14,
            "benign_mutations_core": 5,
            "configs": e1_cfgs,
            "bootstrap_samples": 2000,
            "confidence_level": 0.95,
            "timestamp": datetime.now().isoformat(),
        },
        "core19": stats_core,
        "expanded36": stats_expanded,
        "severity_breakdown_expanded36": severity_breakdown,
    }

    with open(SUMMARY_DIR / "e1_paired_statistical_ci.json", "w", encoding="utf-8") as f:
        json.dump(full_statistical_artifact, f, indent=2, default=str)

    md_e1 = generate_e1_markdown(full_statistical_artifact)
    with open(SUMMARY_DIR / "e1_summary_tables.md", "w", encoding="utf-8") as f:
        f.write(md_e1)

    # 6. Update E2a
    e2a_path = SUMMARY_DIR / "e2_ablation_validators.json"
    with open(e2a_path, "r", encoding="utf-8") as f:
        all_e2a = json.load(f)

    for i, r in enumerate(all_e2a):
        if r["mutation_name"] == "M5b_MULTIPLY_1_5":
            cname = r["config_name"]
            if cname in e2a_patched_runs:
                all_e2a[i] = e2a_patched_runs[cname].to_dict()
            elif cname == "C3_standalone":
                all_e2a[i] = e1_patched_runs["C3_standalone"].to_dict()

    with open(e2a_path, "w", encoding="utf-8") as f:
        json.dump(all_e2a, f, indent=2, default=str)
    save_csv(all_e2a, SUMMARY_DIR / "e2_ablation_validators.csv")

    # 7. Update E2b
    e2b_path = SUMMARY_DIR / "e2_ablation_boundaries.json"
    with open(e2b_path, "r", encoding="utf-8") as f:
        all_e2b = json.load(f)

    for i, r in enumerate(all_e2b):
        if r["mutation_name"] == "M5b_MULTIPLY_1_5":
            cname = r["config_name"]
            if cname in e2b_patched_runs:
                d = e2b_patched_runs[cname].to_dict()
                d["config_name"] = cname
                all_e2b[i] = d
            elif cname == "C3_DUAL_GATE":
                d = e1_patched_runs["C3"].to_dict()
                d["config_name"] = "C3_DUAL_GATE"
                all_e2b[i] = d

    with open(e2b_path, "w", encoding="utf-8") as f:
        json.dump(all_e2b, f, indent=2, default=str)
    save_csv(all_e2b, SUMMARY_DIR / "e2_ablation_boundaries.csv")

    # 8. Re-generate E2 markdown summary
    md_e2 = generate_e2_markdown(all_e2a, all_e2b)
    with open(SUMMARY_DIR / "e2_ablation_summary.md", "w", encoding="utf-8") as f:
        f.write(md_e2)

    print("\n" + "=" * 80)
    print("  SURGICAL PATCH COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    patch_m5b()
