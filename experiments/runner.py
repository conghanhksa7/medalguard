"""MedalGuard Experiment Runner — Staged Pipeline Execution.

Implements the corrected staged experiment flow:
  1. Reset database to clean TPC-H state
  2. Apply mutation to source schema
  3. Swap dbt contract config
  4. Stage 1: dbt run --select tag:bronze
  5. Gate 1 (Pre-transform Bronze -> Silver): validate_pre_transform (quarantine / block)
  6. Stage 2: dbt run --select tag:silver
  7. Post-Silver check: Great Expectations suite (C2 / C3) before Gold
  8. Stage 3: dbt run --select tag:gold
  9. Gate 2 (Post-transform Silver -> Gold): validate post-transform
  10. Measure Blast Radius & Quarantine Effectiveness
  11. Revert mutation & restore dbt config
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

    # Metrics
    detected: bool = False
    blast_radius: float = 0.0
    source_fault_leakage: float = 0.0
    detection_depth: int = -1           # 0=Gate1, 1=Silver contract, 2=Gate2/GX, -1=NOT_DETECTED
    detection_depth_index: int = -1     # Canonical alias for detection_depth
    detection_stage: str = "NOT_DETECTED" # PRE_TRANSFORM | SILVER_CONTRACT | POST_TRANSFORM | NOT_DETECTED
    false_positive: bool = False        # For benign mutations only
    pipeline_wall_ms: float = 0.0
    dbt_elapsed_ms: float = 0.0
    validation_ms: float = 0.0
    quarantined_rows: int = 0
    quarantine_effective: bool = False   # Gold contains only clean data?
    quarantine_effectiveness_pct: float = 0.0
    quarantine_recall: float | None = None
    clean_rows_preserved_pct: float = 100.0

    # Gate details
    gate1_violations: int = 0
    gate2_violations: int = 0
    gx_violations: int = 0
    gold_residual_diff_ratio: float = 0.0

    # Quality metrics (DE-A/B/C)
    completeness_pct: float = 100.0
    validity_pct: float = 100.0
    duplication_rate_pct: float = 0.0
    ingest_correctness: bool = True
    sla_attained: bool = True
    recoverability_pct: float = 100.0
    core_execution_ms: float = 0.0   # dbt_elapsed_ms + validation_ms

    # Metadata
    severity: str = "HIGH"
    schema_version: str = "v1.0"
    target_table: str = "orders"
    is_core: bool = True
    timestamp: str = ""
    error_message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Database & dbt helpers
# ---------------------------------------------------------------------------
def reset_database(db_path: str = DB_PATH, scale_factor: float = 0.1):
    """Reset DuckDB to clean TPC-H state using fast template cache."""
    template_path = Path(PROJECT_ROOT) / "data" / f"warehouse_template_sf{scale_factor}.duckdb"
    if not template_path.exists():
        template_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(template_path))
        con.execute("CREATE SCHEMA IF NOT EXISTS source")
        con.execute("INSTALL tpch; LOAD tpch;")
        con.execute(f"CALL dbgen(sf={scale_factor}, schema='source', overwrite=true)")
        con.close()

    for p in (db_path, db_path + ".wal"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    shutil.copy2(template_path, db_path)


def ingest_bronze_fast(db_path: str = DB_PATH) -> tuple[str, float, float, str]:
    """Fast in-process bronze ingestion for high-throughput batch experimentation."""
    t0 = time.perf_counter()
    con = duckdb.connect(db_path)
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    for tbl in ("orders", "lineitem", "customer"):
        con.execute(f"CREATE OR REPLACE TABLE bronze.bronze_{tbl} AS SELECT * FROM source.{tbl}")
    con.close()
    el_ms = round((time.perf_counter() - t0) * 1000, 1)
    return "SUCCESS", el_ms, el_ms, ""


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
    rr = Path(project_dir) / "target" / "run_results.json"
    rr.unlink(missing_ok=True)

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
    if status == "SUCCESS" and rr.exists():
        try:
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
        if ref is None:
            raise ValueError(f"Reference Gold table missing: {tbl}")
        if cur is None:
            missing = len(ref)
            per_table[tbl] = {
                "status": "MISSING",
                "rows_union": missing,
                "changed": 0,
                "missing": missing,
                "unexpected": 0,
                "deviated": missing,
            }
            dev_total += missing
            row_total += missing
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


def _finalize_quality_metrics(result: ExperimentResult, mutation, scale_factor: float, is_benign: bool, medalguard_on: bool):
    """Compute DE-A/B/C quality and SLA metrics."""
    result.core_execution_ms = round(result.dbt_elapsed_ms + result.validation_ms, 1)
    if result.pipeline_status == "CRASH":
        result.completeness_pct = 0.0
        result.validity_pct = 0.0
        result.ingest_correctness = False
        result.sla_attained = False
        result.recoverability_pct = 0.0
    elif result.pipeline_status == "BLOCKED":
        if result.detection_depth_index in (0, 1):
            result.validity_pct = 100.0
            result.completeness_pct = 100.0 if medalguard_on else 0.0
            result.ingest_correctness = True
            result.sla_attained = (result.detection_depth_index == 0)
        else:
            result.validity_pct = round(max(0.0, (1.0 - result.gold_residual_diff_ratio) * 100.0), 2)
            result.sla_attained = False
    elif result.pipeline_status == "SUCCESS":
        if result.quarantined_rows > 0 and result.quarantine_effective:
            result.validity_pct = 100.0
            result.completeness_pct = round((1.0 - result.quarantined_rows / max(1, 150000 * scale_factor)) * 100.0, 4)
            result.duplication_rate_pct = 0.0
            result.ingest_correctness = True
            result.sla_attained = True
        elif not is_benign and not result.detected:
            result.validity_pct = round(max(0.0, (1.0 - result.blast_radius) * 100.0), 2)
            result.duplication_rate_pct = round((getattr(mutation, "injected_fault_count", 0) / max(1, 150000 * scale_factor)) * 100.0, 4) if "Duplicate" in mutation.name else 0.0
            result.ingest_correctness = (result.blast_radius == 0.0)
            result.sla_attained = False
        else:
            result.validity_pct = 100.0
            result.completeness_pct = 100.0
            result.duplication_rate_pct = 0.0
            result.ingest_correctness = True
            result.sla_attained = True


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
    use_fast_bronze: bool = False,
) -> ExperimentResult:
    """Run one experiment: 1 mutation × 1 config through the staged pipeline."""
    is_benign = getattr(mutation, "category", "") == "BENIGN"
    dbt_contracts_on = config.get("dbt_contracts", False)
    medalguard_on = config.get("medalguard", False)
    gx_on = config.get("great_expectations", False)
    gate_mode = config.get("gate_mode", "quarantine")
    gate1_enabled = config.get("gate1_enabled", True)
    gate2_enabled = config.get("gate2_enabled", True)
    gate2_mode = config.get("gate2_mode", "log_only")
    enabled_validators = config.get("enabled_validators", ["schema", "constraint", "semantic"])

    exp_id = f"{mutation.name}__{config_name}__SF{scale_factor}__run{run_index}"
    result = ExperimentResult(
        experiment_id=exp_id,
        mutation_name=mutation.name,
        category=getattr(mutation, "category", "FAULT"),
        config_name=config_name,
        scale_factor=scale_factor,
        run_index=run_index,
        severity=getattr(mutation, "severity", "HIGH"),
        schema_version=getattr(mutation, "schema_version", "v1.0"),
        target_table=getattr(mutation, "target_table", "orders"),
        is_core=getattr(mutation, "is_core", True),
        timestamp=datetime.now().isoformat(),
    )

    exp_t0 = time.perf_counter()
    t0 = exp_t0

    try:
        # Bước 1: Reset DB và apply mutation
        reset_database(DB_PATH, scale_factor)
        con = duckdb.connect(DB_PATH)
        mutation.apply(con)
        con.close()

        # Swap dbt config
        swap_dbt_config(dbt_contracts_on)

        t0 = time.perf_counter()

        # Chặng 1 (Stage 1): Run bronze
        if use_fast_bronze:
            st_b, wall_b, el_b, err_b = ingest_bronze_fast(DB_PATH)
        else:
            st_b, wall_b, el_b, err_b = run_dbt("tag:bronze")
        result.dbt_elapsed_ms += el_b
        if st_b == "CRASH":
            result.pipeline_status = "CRASH"
            result.measurement_type = "ASSIGNED_CRASH"
            result.blast_radius = 0.0
            result.source_fault_leakage = 0.0
            result.error_message = f"Bronze crash: {err_b}"
            result.validation_ms = round(result.validation_ms, 1)
            result.dbt_elapsed_ms = round(result.dbt_elapsed_ms, 1)
            result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
            _finalize_quality_metrics(result, mutation, scale_factor, is_benign, medalguard_on)
            return result

        # Gate 1: Pre-transform validation on Bronze (nếu medalguard_on và gate1_enabled)
        if medalguard_on and gate1_enabled:
            contracts = [
                ("orders", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "orders.yaml"), "bronze.bronze_orders"),
                ("lineitem", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "lineitem.yaml"), "bronze.bronze_lineitem"),
                ("customer", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "customer.yaml"), "bronze.bronze_customer"),
            ]
            for name, cpath, tbl in contracts:
                g1 = ContractGate(
                    gate_name=f"B->S:{name}",
                    contract_path=cpath,
                    db_path=DB_PATH,
                    mode=gate_mode,
                    enabled_validators=enabled_validators,
                    experiment_id=exp_id,
                )
                t_g1 = time.perf_counter()
                try:
                    res1 = g1.validate_pre_transform(tbl, injected_fault_count=getattr(mutation, "injected_fault_count", 0))
                    val_time = getattr(res1, "validation_time_ms", 0.0) or ((time.perf_counter() - t_g1) * 1000)
                    result.validation_ms += val_time
                    result.gate1_violations += len(res1.violations)
                    result.quarantined_rows += res1.quarantined_rows
                    if not res1.passed and not result.detected:
                        result.detected = True
                        result.detection_stage = "PRE_TRANSFORM"
                        result.detection_depth = 0
                        result.detection_depth_index = 0
                except ContractViolationError as e:
                    val_time = getattr(e, "validation_time_ms", 0.0) or ((time.perf_counter() - t_g1) * 1000)
                    result.validation_ms += val_time
                    result.gate1_violations += len(e.violations)
                    result.detected = True
                    result.detection_stage = "PRE_TRANSFORM"
                    result.detection_depth = 0
                    result.detection_depth_index = 0
                    result.pipeline_status = "BLOCKED"
                    result.measurement_type = "ASSIGNED_BLOCK"
                    result.blast_radius = 0.0
                    result.source_fault_leakage = 0.0
                    result.validation_ms = round(result.validation_ms, 1)
                    result.dbt_elapsed_ms = round(result.dbt_elapsed_ms, 1)
                    result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
                    _finalize_quality_metrics(result, mutation, scale_factor, is_benign, medalguard_on)
                    return result

        # Chặng 2 (Stage 2): Run silver
        st_s, wall_s, el_s, err_s = run_dbt("tag:silver")
        result.dbt_elapsed_ms += el_s
        if st_s == "CRASH":
            if dbt_contracts_on:
                if not result.detected:
                    result.detected = True
                    result.detection_stage = "SILVER_CONTRACT"
                    result.detection_depth = 1
                    result.detection_depth_index = 1
                result.pipeline_status = "BLOCKED"
                result.measurement_type = "ASSIGNED_BLOCK"
                result.blast_radius = 0.0
                result.source_fault_leakage = 0.0
            else:
                result.pipeline_status = "CRASH"
                result.measurement_type = "ASSIGNED_CRASH"
                result.blast_radius = 0.0
                result.source_fault_leakage = 0.0
            result.error_message = f"Silver error: {err_s}"
            result.validation_ms = round(result.validation_ms, 1)
            result.dbt_elapsed_ms = round(result.dbt_elapsed_ms, 1)
            result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
            _finalize_quality_metrics(result, mutation, scale_factor, is_benign, medalguard_on)
            return result

        # Post-Silver Check (Great Expectations Suite, nếu gx_on)
        # Chạy ngay sau Silver và TRƯỚC KHI chạy tag:gold!
        if gx_on:
            t_gx0 = time.perf_counter()
            gx_violated, gx_viols = run_gx_silver_suite(DB_PATH)
            result.validation_ms += (time.perf_counter() - t_gx0) * 1000
            result.gx_violations = len(gx_viols)
            if gx_violated and not result.detected:
                result.detected = True
                result.detection_stage = "POST_TRANSFORM"
                result.detection_depth = 2
                result.detection_depth_index = 2
                result.pipeline_status = "BLOCKED"
                result.measurement_type = "ASSIGNED_BLOCK"
                result.blast_radius = 0.0
                result.source_fault_leakage = 0.0
                result.validation_ms = round(result.validation_ms, 1)
                result.dbt_elapsed_ms = round(result.dbt_elapsed_ms, 1)
                result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
                _finalize_quality_metrics(result, mutation, scale_factor, is_benign, medalguard_on)
                return result

        # Chặng 3 (Stage 3): Run gold
        st_g, wall_g, el_g, err_g = run_dbt("tag:gold")
        result.dbt_elapsed_ms += el_g
        if st_g == "CRASH":
            result.pipeline_status = "CRASH"
            result.measurement_type = "ASSIGNED_CRASH"
            result.blast_radius = 0.0
            result.source_fault_leakage = 0.0
            result.error_message = f"Gold error: {err_g}"
            result.validation_ms = round(result.validation_ms, 1)
            result.dbt_elapsed_ms = round(result.dbt_elapsed_ms, 1)
            result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
            _finalize_quality_metrics(result, mutation, scale_factor, is_benign, medalguard_on)
            return result

        # Gate 2: Post-transform Gold Validation (nếu medalguard_on và gate2_enabled)
        if medalguard_on and gate2_enabled:
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
                        mode=gate2_mode,
                        enabled_validators=enabled_validators,
                        experiment_id=exp_id,
                    )
                    t_g2 = time.perf_counter()
                    try:
                        res2 = g2.validate(s_tbl, g_tbl, injected_fault_count=getattr(mutation, "injected_fault_count", 0))
                        val_time = getattr(res2, "validation_time_ms", 0.0) or ((time.perf_counter() - t_g2) * 1000)
                        result.validation_ms += val_time
                        result.gate2_violations += len(res2.violations)
                        if not res2.passed and not result.detected:
                            result.detected = True
                            result.detection_stage = "POST_TRANSFORM"
                            result.detection_depth = 2
                            result.detection_depth_index = 2
                    except ContractViolationError as e:
                        val_time = getattr(e, "validation_time_ms", 0.0) or ((time.perf_counter() - t_g2) * 1000)
                        result.validation_ms += val_time
                        result.gate2_violations += len(e.violations)
                        result.detected = True
                        result.detection_stage = "POST_TRANSFORM"
                        result.detection_depth = 2
                        result.detection_depth_index = 2
                        result.pipeline_status = "BLOCKED"
                        result.measurement_type = "ASSIGNED_BLOCK"
                        br_leak, _, _, _ = diff_gold(reference, snapshot_gold(DB_PATH))
                        result.gold_residual_diff_ratio = round(br_leak, 4)
                        if not gate1_enabled:
                            result.blast_radius = round(br_leak, 4)
                            result.source_fault_leakage = round(br_leak, 4)

        # Đo Blast Radius tại Gold
        br, dev_rows, total_rows, _ = diff_gold(reference, snapshot_gold(DB_PATH))
        injected_cnt = getattr(mutation, "injected_fault_count", 0)

        if result.quarantined_rows > 0:
            leaked_det, _ = run_gx_silver_suite(DB_PATH)
            if not leaked_det:
                result.quarantine_effective = True
                result.quarantine_effectiveness_pct = 100.0
                result.blast_radius = 0.0
                result.source_fault_leakage = 0.0
                result.pipeline_status = "SUCCESS"
                result.measurement_type = "MEASURED"
                result.gold_residual_diff_ratio = round(br, 4)
                result.clean_rows_preserved_pct = 100.0
                if injected_cnt > 0:
                    result.quarantine_recall = round(result.quarantined_rows / injected_cnt, 4)
            else:
                result.quarantine_effective = False
                result.quarantine_effectiveness_pct = 0.0
                result.blast_radius = round(br, 4)
                result.source_fault_leakage = round(br, 4)
                result.pipeline_status = "SUCCESS"
                result.measurement_type = "MEASURED"
                result.gold_residual_diff_ratio = round(br, 4)
                result.clean_rows_preserved_pct = 100.0
                if injected_cnt > 0:
                    result.quarantine_recall = round(result.quarantined_rows / injected_cnt, 4)
        elif result.pipeline_status == "BLOCKED":
            if not (medalguard_on and not gate1_enabled and gate2_enabled):
                result.blast_radius = 0.0
                result.source_fault_leakage = 0.0
            result.measurement_type = "ASSIGNED_BLOCK"
        else:
            result.blast_radius = 0.0 if is_benign else round(br, 4)
            result.source_fault_leakage = 0.0 if is_benign else round(br, 4)
            result.measurement_type = "MEASURED"
            result.pipeline_status = "SUCCESS"

        if is_benign and result.detected:
            result.false_positive = True

        result.validation_ms = round(result.validation_ms, 1)
        result.dbt_elapsed_ms = round(result.dbt_elapsed_ms, 1)
        result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)

        # DE-A/B/C Quality Metrics
        _finalize_quality_metrics(result, mutation, scale_factor, is_benign, medalguard_on)

    except Exception as e:
        result.pipeline_status = "CRASH"
        result.measurement_type = "ASSIGNED_CRASH"
        result.error_message = str(e)[:500]
        result.validation_ms = round(result.validation_ms, 1)
        result.dbt_elapsed_ms = round(result.dbt_elapsed_ms, 1)
        result.pipeline_wall_ms = round((time.perf_counter() - t0) * 1000, 1)
        _finalize_quality_metrics(result, mutation, scale_factor, is_benign, medalguard_on)

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


def generate_smoke_markdown_table(results: list[ExperimentResult]) -> str:
    """Format smoke test results as GitHub markdown table."""
    lines = [
        "| Config | Mutation | Pipeline Status | Detected | DDI | Detection Stage | Quarantined Rows | QE (%) | Blast Radius | Wall-clock (ms) | dbt (ms) | Validation (ms) |",
        "|:---|:---|:---:|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for r in results:
        qe_str = f"{r.quarantine_effectiveness_pct:.0f}%" if r.quarantined_rows > 0 else "N/A"
        br_str = f"{r.blast_radius:.1%}"
        lines.append(
            f"| **{r.config_name}** | `{r.mutation_name}` | `{r.pipeline_status}` | **{r.detected}** | {r.detection_depth_index} | "
            f"`{r.detection_stage}` | {r.quarantined_rows} | {qe_str} | **{br_str}** | "
            f"{r.pipeline_wall_ms:,.0f} | {r.dbt_elapsed_ms:,.0f} | {r.validation_ms:,.0f} |"
        )
    return "\n".join(lines) + "\n"


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
    parser.add_argument("--save", action="store_true", help="Save experiment result to JSON in results/raw")
    parser.add_argument("--suite", choices=["core", "expanded"], default="core",
                        help="Mutation suite to run (core=19 mutations, expanded=36 mutations)")
    parser.add_argument("--runs", type=int, default=7, help="Number of repetitions for overhead mode (default 7)")

    args = parser.parse_args()

    full_cfg = _load_config()
    configs = full_cfg.get("configs", {})

    # Import mutations
    from mutations import get_mutation_suite
    core_mutations = get_mutation_suite(sf=args.sf, suite="core")
    expanded_mutations = get_mutation_suite(sf=args.sf, suite="expanded")
    all_available_map = {m.name: m for m in expanded_mutations}
    active_mutations_list = expanded_mutations if args.suite in ("expanded", "all") else core_mutations
    mutation_map = {m.name: m for m in active_mutations_list}
    all_configs_map = {**configs, **full_cfg.get("ablation", {})}

    print("Building/loading clean Gold reference...")
    reference = build_clean_reference(args.sf, DB_PATH)
    print(f"Reference ready: {len(reference)} tables.")

    if args.mode == "smoke":
        smoke_mutations = [
            all_available_map["M2a_DropNonKey"],
            all_available_map["M4a_NullAndNegative"],
            all_available_map["M5a_MULTIPLY_100"],
            all_available_map["B1_AddColumn"],
        ]
        smoke_config_names = ["C1", "C2", "C3_standalone", "C3"]

        print("\n" + "=" * 95)
        print(f"  MEDALGUARD SMOKE TEST: {len(smoke_mutations)} mutations × {len(smoke_config_names)} configs (SF={args.sf})")
        print("=" * 95)

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
        print("\n" + "=" * 135)
        print(f"{'Config':<15} {'Mutation':<22} {'Status':<9} {'Det':<6} {'DDI':<5} {'Stage':<16} {'Q_Rows':<7} {'QE':<7} {'BlastRadius':<11} {'Wall(ms)':<9} {'dbt(ms)':<8} {'val(ms)':<8}")
        print("-" * 135)
        for r in results:
            qe_str = f"{r.quarantine_effectiveness_pct:.0f}%" if r.quarantined_rows > 0 else "N/A"
            br_str = f"{r.blast_radius:.1%}"
            print(f"{r.config_name:<15} {r.mutation_name:<22} {r.pipeline_status:<9} {r.detected!s:<6} {r.detection_depth:<5} "
                  f"{r.detection_stage:<16} {r.quarantined_rows:<7} {qe_str:<7} {br_str:<11} {r.pipeline_wall_ms:<9.0f} {r.dbt_elapsed_ms:<8.0f} {r.validation_ms:<8.0f}")
        print("=" * 135)

        # Save summary JSON and Markdown table
        summary_dir = Path(PROJECT_ROOT) / "results" / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_json_path = summary_dir / "smoke_test_results.json"
        with open(summary_json_path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, indent=2, default=str)
        print(f"Saved summary JSON to {summary_json_path}")

        summary_md_path = summary_dir / "smoke_test_table.md"
        with open(summary_md_path, "w", encoding="utf-8") as f:
            f.write(generate_smoke_markdown_table(results))
        print(f"Saved summary Markdown table to {summary_md_path}")
        print("\nSmoke test completed successfully!")

    elif args.mode == "single":
        if not args.mutation:
            print("Error: --mutation is required for single mode. Available choices:")
            print(", ".join(all_available_map.keys()))
            sys.exit(1)
        if not args.config:
            print("Error: --config is required for single mode. Available choices:")
            print(", ".join(all_configs_map.keys()))
            sys.exit(1)

        if args.mutation not in all_available_map:
            print(f"Error: Unknown mutation '{args.mutation}'. Available choices: {list(all_available_map.keys())}")
            sys.exit(1)
        if args.config not in all_configs_map:
            print(f"Error: Unknown config '{args.config}'. Available choices: {list(all_configs_map.keys())}")
            sys.exit(1)

        target_mut = all_available_map[args.mutation]
        target_cfg = all_configs_map[args.config]

        print(f"\nRunning Single Experiment: {target_mut.name} on {args.config} (SF={args.sf})...")
        res = run_single_experiment(
            mutation=target_mut,
            config=target_cfg,
            config_name=args.config,
            reference=reference,
            scale_factor=args.sf,
        )

        if args.save:
            _save_result(res)
            print("Saved result to results/raw/")

        print("\n" + "=" * 60)
        print("  SINGLE EXPERIMENT RESULT")
        print("=" * 60)
        print(f"Experiment ID:    {res.experiment_id}")
        print(f"Mutation:         {res.mutation_name} ({res.category})")
        print(f"Configuration:    {res.config_name}")
        print(f"Severity:         {res.severity}")
        print(f"Schema Version:   {res.schema_version}")
        print(f"Target Table:     {res.target_table}")
        print(f"Is Core:          {res.is_core}")
        print(f"Pipeline Status:  {res.pipeline_status}")
        print(f"Detected:         {res.detected} (Stage: {res.detection_stage}, DDI: {res.detection_depth_index})")
        print(f"Quarantined Rows: {res.quarantined_rows}")
        if res.quarantined_rows > 0:
            print(f"Quarantine Eff.:  {res.quarantine_effectiveness_pct:.1f}%")
        print(f"Blast Radius:     {res.blast_radius:.1%}")
        print(f"Pipeline Wall:    {res.pipeline_wall_ms:.1f} ms")
        print(f"dbt Elapsed:      {res.dbt_elapsed_ms:.1f} ms")
        print(f"Validation Time:  {res.validation_ms:.1f} ms")
        if res.error_message:
            print(f"Error Message:    {res.error_message}")
        print("=" * 60)

    elif args.mode == "matrix":
        print("\n" + "=" * 90)
        print(f"  MEDALGUARD FULL MATRIX ({args.suite.upper()} SUITE): {len(active_mutations_list)} mutations × {len(configs)} configs (SF={args.sf})")
        print("=" * 90)

        results = []
        for cfg_name, cfg in configs.items():
            print(f"\n--- Running Config: {cfg_name} ({cfg.get('description', '')}) ---")
            for mut in active_mutations_list:
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
        print("\n" + "=" * 135)
        print(f"{'Config':<15} {'Mutation':<22} {'Status':<9} {'Det':<6} {'DDI':<5} {'Stage':<16} {'Q_Rows':<7} {'QE':<7} {'BlastRadius':<11} {'Wall(ms)':<9} {'dbt(ms)':<8} {'val(ms)':<8}")
        print("-" * 135)
        for r in results:
            qe_str = f"{r.quarantine_effectiveness_pct:.0f}%" if r.quarantined_rows > 0 else "N/A"
            br_str = f"{r.blast_radius:.1%}"
            print(f"{r.config_name:<15} {r.mutation_name:<22} {r.pipeline_status:<9} {r.detected!s:<6} {r.detection_depth:<5} "
                  f"{r.detection_stage:<16} {r.quarantined_rows:<7} {qe_str:<7} {br_str:<11} {r.pipeline_wall_ms:<9.0f} {r.dbt_elapsed_ms:<8.0f} {r.validation_ms:<8.0f}")
        print("=" * 135)
        print("\nFull Matrix execution completed successfully!")

    elif args.mode == "overhead":
        overhead_configs = ["C0", "C1", "C2", "C3_standalone", "C3"]
        repeat_count = args.runs
        print("\n" + "=" * 80)
        print(f"  MEDALGUARD OVERHEAD BENCHMARK: {repeat_count} clean runs per config across {len(overhead_configs)} configs (SF={args.sf})")
        print("=" * 80)

        class CleanNoOpMutation:
            name = "CLEAN_DATA"
            category = "BENIGN"
            injected_fault_count = 0
            def apply(self, con): pass
            def revert(self, con): pass

        clean_mut = CleanNoOpMutation()
        overhead_summary = {}

        for cfg_name in overhead_configs:
            cfg = configs[cfg_name]
            print(f"\n--- Benchmarking {cfg_name} ({cfg.get('description', '')}) [{repeat_count} runs] ---")
            wall_list, dbt_list, val_list = [], [], []

            for i in range(1, repeat_count + 1):
                res = run_single_experiment(
                    mutation=clean_mut,
                    config=cfg,
                    config_name=cfg_name,
                    reference=reference,
                    scale_factor=args.sf,
                    run_index=i,
                )
                wall_list.append(res.pipeline_wall_ms)
                dbt_list.append(res.dbt_elapsed_ms)
                val_list.append(res.validation_ms)
                print(f"  Run {i}/{repeat_count}: wall={res.pipeline_wall_ms:.1f}ms dbt={res.dbt_elapsed_ms:.1f}ms val={res.validation_ms:.1f}ms")

            med_wall = statistics.median(wall_list)
            med_dbt = statistics.median(dbt_list)
            med_val = statistics.median(val_list)
            overhead_summary[cfg_name] = {
                "runs": repeat_count,
                "median_wall_ms": round(med_wall, 1),
                "median_dbt_ms": round(med_dbt, 1),
                "median_val_ms": round(med_val, 1),
                "wall_runs": wall_list,
                "dbt_runs": dbt_list,
                "val_runs": val_list,
            }
            print(f"  --> {cfg_name} Median: Wall={med_wall:.1f}ms, dbt={med_dbt:.1f}ms, Val={med_val:.1f}ms")

        # Save overhead summary
        summary_dir = Path(PROJECT_ROOT) / "results" / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        overhead_json_path = summary_dir / "overhead_results.json"
        with open(overhead_json_path, "w", encoding="utf-8") as f:
            json.dump(overhead_summary, f, indent=2, default=str)
        print(f"\nSaved overhead benchmark to {overhead_json_path}")


if __name__ == "__main__":
    main()
