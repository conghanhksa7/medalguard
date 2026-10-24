"""MedalGuard Experiment Runner — Staged Pipeline Execution.

Implements the corrected experiment flow:
  1. Reset database to clean TPC-H state
  2. Apply mutation to source schema
  3. Swap dbt contract config
  4. Stage 1: dbt run --select tag:bronze
  5. MedalGuard Gate 1: validate_pre_transform (quarantine / block)
  6. Stage 2: dbt run --select tag:silver tag:gold
  7. MedalGuard Gate 2: validate post-transform
  8. GX validation: run_gx_silver_suite (for C2 / C3)
  9. Measure Blast Radius & Quarantine Effectiveness
  10. Revert mutation & restore dbt config
"""
import os
import sys
import json
import time
import random
import re
import shutil
import subprocess
import statistics
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

import duckdb
import yaml
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from medalguard.gate import ContractGate, ContractViolationError, MeasurementType
from medalguard.gx_runner import run_gx_silver_suite
from medalguard.utils import quote_identifier, quote_table, parse_table_ref

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_PATH = str(PROJECT_ROOT / "data" / "warehouse.duckdb")
DBT_PROJECT = str(PROJECT_ROOT / "dbt_project")
CONTRACTS_DIR = str(PROJECT_ROOT / "contracts")
RESULTS_DIR = str(PROJECT_ROOT / "results" / "raw")
CONFIG_PATH = str(PROJECT_ROOT / "experiments" / "config.yaml")

REL_TOL = 1e-9

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


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ExperimentResult:
    """Full result of one experiment run."""
    experiment_id: str
    mutation_name: str
    category: str
    config_name: str
    scale_factor: float
    run_index: int

    # Pipeline outcome
    pipeline_status: str = "SUCCESS"    # SUCCESS | BLOCKED | CRASH | PARTIAL
    measurement_type: str = "MEASURED"  # MEASURED | ASSIGNED_BLOCK | ASSIGNED_CRASH

    # 7 Metrics
    detected: bool = False
    blast_radius: float = 0.0
    detection_depth: int = -1           # 0=Gate1, 1=Silver contract, 2=Gate2/GX, -1=NOT_DETECTED
    detection_stage: str = "NOT_DETECTED" # PRE_TRANSFORM | SILVER_CONTRACT | POST_TRANSFORM | NOT_DETECTED
    false_positive: bool = False        # For benign mutations only
    pipeline_wall_ms: float = 0.0
    dbt_elapsed_ms: float = 0.0
    validation_ms: float = 0.0
    quarantined_rows: int = 0
    quarantine_effective: bool = False   # Gold contains only clean data?
    quarantine_effectiveness_pct: float = 0.0

    # Gate details
    gate1_violations: int = 0
    gate2_violations: int = 0
    gx_violations: int = 0
    gold_residual_diff_ratio: float = 0.0

    # Metadata
    timestamp: str = ""
    error_message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Database & dbt helpers
# ---------------------------------------------------------------------------
def reset_database(db_path: str = DB_PATH, scale_factor: float = 0.1):
    """Reset DuckDB to clean TPC-H state."""
    for p in (db_path, db_path + ".wal"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = duckdb.connect(db_path)
    con.execute("DROP SCHEMA IF EXISTS source CASCADE;")
    con.execute("CREATE SCHEMA IF NOT EXISTS source")
    con.execute("INSTALL tpch; LOAD tpch;")
    con.execute(f"CALL dbgen(sf={scale_factor}, schema='source', overwrite=true)")
    con.close()


def swap_dbt_config(dbt_contracts_enabled: bool, project_dir: str = DBT_PROJECT):
    """Swap dbt models yaml between with_contract and no_contract."""
    silver_dir = Path(project_dir) / "models" / "silver"
    target = silver_dir / "_silver_models.yml"
    if dbt_contracts_enabled:
        src = silver_dir / "_silver_models_with_contract.yml.bak"
    else:
        src = silver_dir / "_silver_models_no_contract.yml.bak"
    assert src.exists(), f"Contract backup file not found: {src}"
    shutil.copy(src, target)


def run_dbt(select: str, project_dir: str = DBT_PROJECT) -> tuple[str, float, float, str]:
    """Run dbt with given select, return (status, wall_ms, dbt_elapsed_ms, error_msg)."""
    start = time.perf_counter()
    try:
        res = subprocess.run(
            ["dbt", "run", "--select", select, "--profiles-dir", ".", "--project-dir", "."],
            capture_output=True, text=True, check=True,
            cwd=str(project_dir), timeout=600,
        )
        status, error_msg = "SUCCESS", ""
    except subprocess.CalledProcessError as e:
        status = "CRASH"
        error_msg = (e.stderr or e.stdout or str(e))[:500]
    except subprocess.TimeoutExpired:
        status = "CRASH"
        error_msg = "dbt run timed out (600s)"

    wall_ms = (time.perf_counter() - start) * 1000
    dbt_elapsed_ms = 0.0
    try:
        rr = Path(project_dir) / "target" / "run_results.json"
        if rr.exists():
            data = json.loads(rr.read_text(encoding="utf-8"))
            dbt_elapsed_ms = round(data.get("elapsed_time", 0) * 1000, 1)
    except Exception:
        pass

    return status, wall_ms, dbt_elapsed_ms, error_msg


# ---------------------------------------------------------------------------
# Gold snapshot & diffing
# ---------------------------------------------------------------------------
def snapshot_gold(db_path: str = DB_PATH) -> dict:
    """Return {table: DataFrame} of current Gold tables (None if missing)."""
    snap = {}
    con = duckdb.connect(db_path, read_only=True)
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


def diff_gold(reference: dict, current: dict) -> tuple[float, int, int, dict]:
    """Compare Gold snapshots against clean reference. Returns (br, dev_total, row_total, per_table)."""
    per_table, dev_total, row_total = {}, 0, 0
    for tbl, (keys, metrics) in GOLD_TABLES.items():
        ref, cur = reference.get(tbl), current.get(tbl)
        if cur is None or ref is None:
            per_table[tbl] = {"status": "MISSING"}
            continue
        ref_k = ref.copy()
        cur_k = cur.copy()
        for k in keys:
            ref_k[k] = ref_k[k].astype(str)
            cur_k[k] = cur_k[k].astype(str)
        m = ref_k.merge(cur_k, on=keys, how="outer", suffixes=("_ref", "_cur"), indicator=True)
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


def build_clean_reference(scale_factor: float = 0.1, db_path: str = DB_PATH) -> dict:
    """Load pre-generated clean Gold reference CSVs if available, otherwise build fresh."""
    ref_rev = Path(PROJECT_ROOT) / "results" / "baseline" / "gold_reference_gold_revenue_by_nation.csv"
    ref_prio = Path(PROJECT_ROOT) / "results" / "baseline" / "gold_reference_gold_order_priority_summary.csv"
    if scale_factor == 0.1 and ref_rev.exists() and ref_prio.exists():
        return {
            "gold.gold_revenue_by_nation": pd.read_csv(ref_rev),
            "gold.gold_order_priority_summary": pd.read_csv(ref_prio),
        }

    reset_database(db_path, scale_factor)
    swap_dbt_config(False)
    run_dbt("tag:bronze tag:silver tag:gold")
    return snapshot_gold(db_path)


def _revert_mutation(mutation):
    """Safely revert mutation if applied."""
    if getattr(mutation, "applied", False):
        try:
            con = duckdb.connect(DB_PATH)
            mutation.revert(con)
            con.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Core single experiment runner
# ---------------------------------------------------------------------------
def run_single_experiment(
    mutation,
    config: dict,
    config_name: str,
    reference: dict,
    scale_factor: float = 0.1,
    run_index: int = 0,
) -> ExperimentResult:
    """Run one experiment: 1 mutation × 1 config through the staged pipeline."""
    is_benign = getattr(mutation, "category", "") == "BENIGN"
    dbt_contracts_on = config.get("dbt_contracts", False)
    medalguard_on = config.get("medalguard", False)
    gx_on = config.get("great_expectations", False)
    gate_mode = config.get("gate_mode", "quarantine")
    enabled_validators = config.get("enabled_validators", ["schema", "constraint", "semantic"])

    exp_id = f"{mutation.name}__{config_name}__SF{scale_factor}__run{run_index}"
    result = ExperimentResult(
        experiment_id=exp_id,
        mutation_name=mutation.name,
        category=getattr(mutation, "category", "FAULT"),
        config_name=config_name,
        scale_factor=scale_factor,
        run_index=run_index,
        timestamp=datetime.now().isoformat(),
    )

    try:
        # Bước 1: Reset DB và apply mutation
        reset_database(DB_PATH, scale_factor)
        con = duckdb.connect(DB_PATH)
        mutation.apply(con)
        con.close()

        # Swap dbt config
        swap_dbt_config(dbt_contracts_on)

        t0 = time.perf_counter()

        # Bước 2 (Stage 1): Run bronze
        st_b, wall_b, el_b, err_b = run_dbt("tag:bronze")
        result.dbt_elapsed_ms = round(el_b, 1)
        if st_b == "CRASH":
            result.pipeline_status = "CRASH"
            result.measurement_type = "ASSIGNED_CRASH"
            result.blast_radius = 0.0
            result.error_message = f"Bronze crash: {err_b}"
            result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
            swap_dbt_config(False)
            _revert_mutation(mutation)
            return result

        # Bước 3 (Gate 1 — nếu medalguard_on):
        if medalguard_on:
            contracts = [
                ("orders", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "orders.yaml"), "bronze.bronze_orders"),
                ("lineitem", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "lineitem.yaml"), "bronze.bronze_lineitem"),
                ("customer", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "customer.yaml"), "bronze.bronze_customer"),
            ]
            g1_blocked = False
            for name, cpath, tbl in contracts:
                g1 = ContractGate(
                    gate_name=f"B->S:{name}",
                    contract_path=cpath,
                    db_path=DB_PATH,
                    mode=gate_mode,
                    enabled_validators=enabled_validators,
                )
                t_g1 = time.perf_counter()
                try:
                    res1 = g1.validate_pre_transform(tbl, injected_fault_count=getattr(mutation, "injected_fault_count", 0))
                    result.validation_ms += (res1.validation_time_ms if hasattr(res1, "validation_time_ms") and res1.validation_time_ms else (time.perf_counter() - t_g1) * 1000)
                    result.gate1_violations += len(res1.violations)
                    result.quarantined_rows += res1.quarantined_rows
                    if not res1.passed and not result.detected:
                        result.detected = True
                        result.detection_stage = "PRE_TRANSFORM"
                        result.detection_depth = 0
                except ContractViolationError as e:
                    result.validation_ms += (time.perf_counter() - t_g1) * 1000
                    g1_blocked = True
                    result.detected = True
                    result.detection_stage = "PRE_TRANSFORM"
                    result.detection_depth = 0
                    result.gate1_violations += len(e.violations)
                    break

            if g1_blocked:
                result.pipeline_status = "BLOCKED"
                result.measurement_type = "ASSIGNED_BLOCK"
                result.blast_radius = 0.0
                result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
                swap_dbt_config(False)
                _revert_mutation(mutation)
                return result

        # Bước 4 (Stage 2): Run silver and gold
        st_sg, wall_sg, el_sg, err_sg = run_dbt("tag:silver tag:gold")
        result.dbt_elapsed_ms = round(result.dbt_elapsed_ms + el_sg, 1)
        if st_sg == "CRASH":
            if dbt_contracts_on:
                if not result.detected:
                    result.detected = True
                    result.detection_stage = "SILVER_CONTRACT"
                    result.detection_depth = 1
                result.pipeline_status = "BLOCKED"
                result.measurement_type = "ASSIGNED_BLOCK"
                result.blast_radius = 0.0
            else:
                result.pipeline_status = "CRASH"
                result.measurement_type = "ASSIGNED_CRASH"
                result.blast_radius = 0.0
            result.error_message = f"Silver/Gold error: {err_sg}"
            result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
            swap_dbt_config(False)
            _revert_mutation(mutation)
            return result

        # Bước 5 (Gate 2 — nếu medalguard_on):
        if medalguard_on:
            g2_contracts = [
                ("revenue_by_nation", os.path.join(CONTRACTS_DIR, "silver_to_gold", "revenue_by_nation.yaml"), "silver.silver_orders", "gold.gold_revenue_by_nation"),
                ("order_priority_summary", os.path.join(CONTRACTS_DIR, "silver_to_gold", "order_priority_summary.yaml"), "silver.silver_orders", "gold.gold_order_priority_summary"),
            ]
            for g2_name, g2_cpath, s_tbl, g_tbl in g2_contracts:
                if os.path.exists(g2_cpath):
                    g2 = ContractGate(
                        gate_name=f"S->G:{g2_name}",
                        contract_path=g2_cpath,
                        db_path=DB_PATH,
                        mode="log_only",
                        enabled_validators=enabled_validators,
                    )
                    t_g2 = time.perf_counter()
                    res2 = g2.validate(s_tbl, g_tbl, injected_fault_count=getattr(mutation, "injected_fault_count", 0))
                    result.validation_ms += (res2.validation_time_ms if hasattr(res2, "validation_time_ms") and res2.validation_time_ms else (time.perf_counter() - t_g2) * 1000)
                    result.gate2_violations += len(res2.violations)
                    if not res2.passed and not result.detected:
                        result.detected = True
                        result.detection_stage = "POST_TRANSFORM"
                        result.detection_depth = 2
                        result.pipeline_status = "BLOCKED"
                        result.measurement_type = "ASSIGNED_BLOCK"

        # Bước 6 (Great Expectations — nếu gx_on):
        if gx_on:
            t_gx0 = time.perf_counter()
            gx_violated, gx_viols = run_gx_silver_suite(DB_PATH)
            result.validation_ms += (time.perf_counter() - t_gx0) * 1000
            result.gx_violations = len(gx_viols)
            if gx_violated and not result.detected:
                result.detected = True
                result.detection_stage = "POST_TRANSFORM"
                result.detection_depth = 2
                result.pipeline_status = "BLOCKED"
                result.measurement_type = "ASSIGNED_BLOCK"

        # Bước 7 (Đo Blast Radius & Quarantine Effectiveness):
        br, dev_rows, total_rows, _ = diff_gold(reference, snapshot_gold(DB_PATH))

        if result.quarantined_rows > 0:
            leaked_det, _ = run_gx_silver_suite(DB_PATH)
            if not leaked_det:
                result.quarantine_effective = True
                result.quarantine_effectiveness_pct = 100.0
                result.blast_radius = 0.0
                result.pipeline_status = "SUCCESS"
                result.measurement_type = "MEASURED"
                result.gold_residual_diff_ratio = round(br, 4)
            else:
                result.quarantine_effective = False
                result.quarantine_effectiveness_pct = 0.0
                result.blast_radius = round(br, 4)
                result.pipeline_status = "SUCCESS"
                result.measurement_type = "MEASURED"
                result.gold_residual_diff_ratio = round(br, 4)
        elif result.pipeline_status == "BLOCKED":
            result.blast_radius = 0.0
            result.measurement_type = "ASSIGNED_BLOCK"
        else:
            result.blast_radius = 0.0 if is_benign else round(br, 4)
            result.measurement_type = "MEASURED"
            result.pipeline_status = "SUCCESS"

        if is_benign and result.detected:
            result.false_positive = True

        result.validation_ms = round(result.validation_ms, 1)
        result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)

    except Exception as e:
        result.pipeline_status = "CRASH"
        result.measurement_type = "ASSIGNED_CRASH"
        result.error_message = str(e)[:500]
        result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)

    finally:
        swap_dbt_config(False)
        _revert_mutation(mutation)

    return result


def _save_result(result: ExperimentResult):
    """Save experiment result to JSON file."""
    raw_dir = Path(RESULTS_DIR)
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_id = re.sub(r'[^\w\-_\.]', '_', result.experiment_id)
    clean_ts = result.timestamp.replace(":", "")
    filepath = raw_dir / f"{clean_id}__{clean_ts}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)


def _load_config() -> dict:
    """Load experiment config from YAML."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="MedalGuard Experiment Runner")
    parser.add_argument("--mode", choices=["smoke", "matrix", "overhead", "single"],
                        default="smoke", help="Execution mode")
    parser.add_argument("--sf", type=float, default=0.1, help="Scale factor (default 0.1)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-randomize", action="store_true", help="Disable randomization")
    parser.add_argument("--mutation", type=str, help="Specific mutation name")
    parser.add_argument("--config", type=str, help="Specific config name")

    args = parser.parse_args()

    full_cfg = _load_config()
    configs = full_cfg.get("configs", {})

    # Import mutations
    from mutations.m1_additive import M1a_AddSingleCol, M1b_AddMultiCol
    from mutations.m2_destructive import M2a_DropNonKey, M2b_DropKeyCol, M2c_RenameCol
    from mutations.m3_type_change import M3a_DoubleToVarchar, M3b_IntegerToDouble, M3c_DateToVarchar
    from mutations.m4_constraint_breach import M4a_NullAndNegative, M4b_NullSmall, M4c_DuplicateKeys
    from mutations.m5_semantic_drift import M5a_MULTIPLY_100, M5b_MULTIPLY_1_5, M5c_CATEGORICAL_SHIFT
    from mutations.benign_mutations import B1_AddColumn, B2_ValueInRange, B3_InsertRows, B5_AddValidStatus, B7_LargeBatchInsert

    print("Building/loading clean Gold reference...")
    reference = build_clean_reference(args.sf, DB_PATH)
    print(f"Reference ready: {len(reference)} tables.")

    if args.mode == "smoke":
        smoke_mutations = [
            M2a_DropNonKey(args.sf),
            M4a_NullAndNegative(args.sf),
            M5a_MULTIPLY_100(args.sf),
            B1_AddColumn(args.sf),
        ]
        smoke_config_names = ["C1", "C2", "C3_standalone"]

        print("\n" + "=" * 90)
        print(f"  MEDALGUARD SMOKE TEST: {len(smoke_mutations)} mutations × {len(smoke_config_names)} configs (SF={args.sf})")
        print("=" * 90)

        results = []
        for cfg_name in smoke_config_names:
            cfg = configs[cfg_name]
            print(f"\n--- Running Config: {cfg_name} ({cfg.get('description', '')}) ---")
            for mut in smoke_mutations:
                print(f"  Testing {mut.name}...")
                res = run_single_experiment(
                    mutation=mut,
                    config=cfg,
                    config_name=cfg_name,
                    reference=reference,
                    scale_factor=args.sf,
                )
                results.append(res)
                _save_result(res)
                print(f"    -> status={res.pipeline_status:<8} det={res.detected!s:<5} DDI={res.detection_depth:<2} "
                      f"stage={res.detection_stage:<16} Q={res.quarantined_rows:<2} BR={res.blast_radius:>6.1%}")

        # Summary Table
        print("\n" + "=" * 122)
        print(f"{'Config':<15} {'Mutation':<22} {'Status':<9} {'Det':<6} {'DDI':<5} {'Stage':<16} {'Q_Rows':<7} {'QE':<7} {'BlastRadius':<11} {'Wall(ms)':<9} {'dbt(ms)':<8} {'val(ms)':<8}")
        print("-" * 122)
        for r in results:
            qe_str = f"{r.quarantine_effectiveness_pct:.0f}%" if r.quarantined_rows > 0 else "N/A"
            br_str = f"{r.blast_radius:.1%}"
            print(f"{r.config_name:<15} {r.mutation_name:<22} {r.pipeline_status:<9} {r.detected!s:<6} {r.detection_depth:<5} "
                  f"{r.detection_stage:<16} {r.quarantined_rows:<7} {qe_str:<7} {br_str:<11} {r.pipeline_wall_ms:<9.0f} {r.dbt_elapsed_ms:<8.0f} {r.validation_ms:<8.0f}")
        print("=" * 122)
        print("\nSmoke test completed successfully!")

    elif args.mode == "matrix":
        print("Matrix mode placeholder for Task 4")


if __name__ == "__main__":
    main()
