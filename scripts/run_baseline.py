"""Baseline Experiment Runner v4 — C0 (no enforcement) with MEASURED Blast Radius.

Method:
  1. Build a clean Gold reference once (TPC-H dbgen is deterministic).
  2. For each mutation: reset DB -> apply mutation -> dbt run -> diff Gold vs reference.

Blast Radius (operational definition, Gold-row granularity):
  Gold tables are aggregates, so source records do not map 1:1 to Gold rows.
  We therefore measure corruption at the Gold layer:
      BR = |Gold rows whose values deviate from the clean reference
            (incl. missing / unexpected rows)| / |Gold rows in reference ∪ current|
  - Pipeline CRASH  -> BR = 0 (ASSIGNED_CRASH): nothing new reaches Gold.
  - Pipeline SUCCESS -> BR measured by diff (MEASURED).
"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "data" / "warehouse.duckdb")
DBT_DIR = PROJECT_ROOT / "dbt_project"
RESULTS_DIR = PROJECT_ROOT / "results" / "baseline"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

REL_TOL = 1e-9

# Gold tables: (table, key columns, metric columns)
GOLD_TABLES = {
    "gold.gold_revenue_by_nation": (
        ["nation", "order_year"],
        ["total_orders", "total_revenue", "avg_discount"],
    ),
    "gold.gold_order_priority_summary": (
        ["o_orderpriority", "o_orderstatus"],
        ["order_count", "total_value", "avg_order_value"],
    ),
}

from mutations.m1_additive import M1a_AddSingleCol, M1b_AddMultiCol
from mutations.m2_destructive import M2a_DropNonKey, M2b_DropKeyCol, M2c_RenameCol
from mutations.m3_type_change import M3a_DoubleToVarchar, M3b_IntegerToDouble, M3c_DateToVarchar
from mutations.m4_constraint_breach import M4a_NullAndNegative, M4b_NullSmall, M4c_DuplicateKeys
from mutations.m5_semantic_drift import M5a_MULTIPLY_100, M5b_MULTIPLY_1_5, M5c_CATEGORICAL_SHIFT
from mutations.benign_mutations import (
    B1_AddColumn, B2_ValueInRange, B3_InsertRows,
    B5_AddValidStatus, B7_LargeBatchInsert
)


# ------------------------------------------------------------------
# Pipeline helpers
# ------------------------------------------------------------------
def reset_db(sf=0.1):
    """Regenerate TPC-H data from scratch (deterministic)."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    for p in (DB_PATH, DB_PATH + ".wal"):
        if os.path.exists(p):
            os.remove(p)
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS source")
    con.execute("INSTALL tpch; LOAD tpch;")
    con.execute(f"CALL dbgen(sf={sf}, schema='source')")
    count = con.execute("SELECT COUNT(*) FROM source.orders").fetchone()[0]
    con.close()
    return count


def read_dbt_exec_time():
    """Sum of model execution times reported by dbt (excludes CLI startup)."""
    rr = DBT_DIR / "target" / "run_results.json"
    try:
        data = json.loads(rr.read_text(encoding="utf-8"))
        return round(sum(r.get("execution_time", 0) for r in data["results"]) * 1000, 1), \
               round(data.get("elapsed_time", 0) * 1000, 1)
    except Exception:
        return None, None


def run_dbt():
    """Run full dbt pipeline (C0 = no contracts, no tests)."""
    start = time.perf_counter()
    try:
        subprocess.run(
            ["dbt", "run", "--profiles-dir", ".", "--project-dir", "."],
            capture_output=True, text=True, check=True,
            cwd=str(DBT_DIR), timeout=180,
        )
        status, error = "SUCCESS", ""
    except subprocess.CalledProcessError as e:
        status, error = "CRASH", (e.stdout or e.stderr or str(e))[-500:]
    except subprocess.TimeoutExpired:
        status, error = "CRASH", "Timeout 180s"
    wall_ms = (time.perf_counter() - start) * 1000
    return status, wall_ms, error


def snapshot_gold():
    """Return {table: DataFrame} of current Gold tables (None if missing)."""
    snap = {}
    con = duckdb.connect(DB_PATH, read_only=True)
    for tbl in GOLD_TABLES:
        try:
            snap[tbl] = con.execute(f"SELECT * FROM {tbl}").fetchdf()
        except Exception:
            snap[tbl] = None
    con.close()
    return snap


def _values_differ(a, b):
    if pd.isna(a) and pd.isna(b):
        return False
    if pd.isna(a) or pd.isna(b):
        return True
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return a != b
    denom = max(abs(a), abs(b), 1e-12)
    return abs(a - b) / denom > REL_TOL


def diff_gold(reference, current):
    """Compare Gold snapshots. Returns per-table stats and overall BR."""
    per_table, dev_total, row_total = {}, 0, 0
    for tbl, (keys, metrics) in GOLD_TABLES.items():
        ref, cur = reference[tbl], current.get(tbl)
        if cur is None:
            per_table[tbl] = {"status": "MISSING"}
            continue
        ref_k = ref.copy(); cur_k = cur.copy()
        for k in keys:  # normalise key types (e.g. year as int vs float)
            ref_k[k] = ref_k[k].astype(str); cur_k[k] = cur_k[k].astype(str)
        m = ref_k.merge(cur_k, on=keys, how="outer",
                        suffixes=("_ref", "_cur"), indicator=True)
        missing = int((m["_merge"] == "left_only").sum())
        unexpected = int((m["_merge"] == "right_only").sum())
        both = m[m["_merge"] == "both"]
        changed = int(sum(
            any(_values_differ(r[f"{c}_ref"], r[f"{c}_cur"]) for c in metrics)
            for _, r in both.iterrows()
        ))
        deviated = missing + unexpected + changed
        per_table[tbl] = {
            "rows_union": len(m), "changed": changed,
            "missing": missing, "unexpected": unexpected, "deviated": deviated,
        }
        dev_total += deviated
        row_total += len(m)
    br = dev_total / row_total if row_total else 0.0
    return br, dev_total, row_total, per_table


# ------------------------------------------------------------------
# Experiment
# ------------------------------------------------------------------
def run_single_test(mutation, reference, sf=0.1):
    print(f"\n{'='*64}\n  {mutation.name} [{mutation.category}]\n  {mutation.description}\n{'='*64}")

    reset_db(sf)
    con = duckdb.connect(DB_PATH)
    mutation.apply(con)
    con.close()
    inject_count = mutation.injected_fault_count

    status, wall_ms, error = run_dbt()
    exec_ms, dbt_elapsed_ms = read_dbt_exec_time() if status == "SUCCESS" else (None, None)
    print(f"  dbt: {status} (wall {wall_ms:.0f}ms)" + (f" | {error[-150:]}" if error else ""))

    if status == "CRASH":
        br, dev, total, per_table = 0.0, 0, 0, {}
        measurement_type = "ASSIGNED_CRASH"
    else:
        br, dev, total, per_table = diff_gold(reference, snapshot_gold())
        measurement_type = "MEASURED"

    is_benign = mutation.category == "BENIGN"
    result = {
        "mutation": mutation.name,
        "category": mutation.category,
        "description": mutation.description,
        "config": "C0",
        "timestamp": datetime.now().isoformat(),
        "pipeline_status": status,
        "pipeline_wall_ms": round(wall_ms, 1),
        "dbt_model_exec_ms": exec_ms,
        "detected": False,                      # C0 has no enforcement
        "detection_stage": "NOT_DETECTED",
        "inject_count": inject_count,
        "fault_propagated_to_gold": dev > 0,
        "gold_deviated_rows": dev,
        "gold_total_rows": total,
        # BR is only meaningful for fault mutations; for benign it is a legit change
        "blast_radius": None if is_benign else round(br, 4),
        "gold_change_ratio": round(br, 4),
        "measurement_type": measurement_type,
        "gold_diff_detail": per_table,
        "error": error[-300:] if error else "",
    }
    print(f"  Gold deviated: {dev}/{total} rows -> "
          f"{'change' if is_benign else 'BR'}={br:.1%} [{measurement_type}]")
    return result


def main():
    sf = 0.1
    fault_mutations = [
        M1a_AddSingleCol(sf), M1b_AddMultiCol(sf),
        M2a_DropNonKey(sf), M2b_DropKeyCol(sf), M2c_RenameCol(sf),
        M3a_DoubleToVarchar(sf), M3b_IntegerToDouble(sf), M3c_DateToVarchar(sf),
        M4a_NullAndNegative(sf), M4b_NullSmall(sf), M4c_DuplicateKeys(sf),
        M5a_MULTIPLY_100(sf), M5b_MULTIPLY_1_5(sf), M5c_CATEGORICAL_SHIFT(sf),
    ]
    benign_mutations = [
        B1_AddColumn(sf), B2_ValueInRange(sf), B3_InsertRows(sf),
        B5_AddValidStatus(sf), B7_LargeBatchInsert(sf),
    ]

    print("=" * 64)
    print("  MedalGuard Baseline — C0 (No Enforcement), MEASURED Blast Radius")
    print(f"  SF={sf}: {len(fault_mutations)} fault + {len(benign_mutations)} benign")
    print("=" * 64)

    # 1. Clean Gold reference
    print("\n[Reference] Building clean Gold snapshot...")
    reset_db(sf)
    status, _, err = run_dbt()
    if status != "SUCCESS":
        raise RuntimeError(f"Clean pipeline failed: {err}")
    reference = snapshot_gold()
    for tbl, df in reference.items():
        df.to_csv(RESULTS_DIR / f"gold_reference_{tbl.split('.')[-1]}.csv", index=False)
        print(f"  {tbl}: {len(df)} rows")

    # 2. Experiments
    results = [run_single_test(m, reference, sf) for m in fault_mutations + benign_mutations]

    out = RESULTS_DIR / "baseline_c0_results.json"
    out.write_text(json.dumps(results, indent=2, default=str, ensure_ascii=False), encoding="utf-8")

    # 3. Summary
    print("\n" + "=" * 92)
    print(f"{'Mutation':<24}{'Category':<19}{'Status':<9}{'Inject':>8}{'GoldDev':>10}{'BR':>9}  Type")
    print("-" * 92)
    for r in results:
        br = "n/a" if r["blast_radius"] is None else f"{r['blast_radius']:.1%}"
        print(f"{r['mutation']:<24}{r['category']:<19}{r['pipeline_status']:<9}"
              f"{r['inject_count']:>8}{r['gold_deviated_rows']:>5}/{r['gold_total_rows']:<4}"
              f"{br:>9}  {r['measurement_type']}")

    faults = [r for r in results if r["category"] != "BENIGN"]
    benign = [r for r in results if r["category"] == "BENIGN"]
    print(f"\nDetection Rate: {sum(r['detected'] for r in faults)}/{len(faults)}")
    print(f"False Positive Rate: {sum(r['detected'] for r in benign)}/{len(benign)}")
    print(f"Avg BR (faults): {sum(r['blast_radius'] for r in faults) / len(faults):.1%}")
    print(f"Faults silently propagated to Gold: "
          f"{sum(r['fault_propagated_to_gold'] for r in faults)}/{len(faults)}")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
