"""MedalGuard Experiment Runner — Staged Pipeline Execution.

Implements the corrected experiment flow:
  1. Reset database to clean TPC-H state
  2. Apply mutation to source schema
  3. dbt run --select tag:bronze tag:silver   (Stage 1)
  4. MedalGuard Gate 1: validate_pre_transform (quarantine)
  5. dbt run --select tag:gold                (Stage 2)
  6. MedalGuard Gate 2: validate post-transform
  7. Collect metrics
  8. Revert mutation

Supports: randomized order, cold start, separate overhead measurement.
"""
import os
import sys
import json
import time
import random
import shutil
import subprocess
import statistics
import duckdb
import yaml
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from medalguard.gate import ContractGate, ContractViolationError, MeasurementType

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_PATH = str(PROJECT_ROOT / "data" / "warehouse.duckdb")
DBT_PROJECT = str(PROJECT_ROOT / "dbt_project")
CONTRACTS_DIR = str(PROJECT_ROOT / "contracts")
RESULTS_DIR = str(PROJECT_ROOT / "results" / "raw")
CONFIG_PATH = str(PROJECT_ROOT / "experiments" / "config.yaml")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
class PipelineStatus(str, Enum):
    SUCCESS = "SUCCESS"
    CRASH = "CRASH"
    BLOCKED = "BLOCKED"
    PARTIAL = "PARTIAL"


@dataclass
class ExperimentResult:
    """Full result of one experiment run."""
    experiment_id: str
    mutation_name: str
    config_name: str
    scale_factor: float
    run_index: int

    # Pipeline outcome
    pipeline_status: str = PipelineStatus.SUCCESS
    measurement_type: str = MeasurementType.MEASURED

    # 7 Metrics
    detected: bool = False
    blast_radius: float = 0.0
    detection_depth: int = -1          # 0=Gate1, 1=compile-time, 2=Gate2, -1=NOT_DETECTED
    detection_stage: str = "NOT_DETECTED"
    false_positive: bool = False       # For benign mutations only
    pipeline_time_ms: float = 0.0
    quarantined_rows: int = 0
    quarantine_effective: bool = False  # Gold contains only clean data?

    # Gate details
    gate1_violations: int = 0
    gate2_violations: int = 0
    gate1_time_ms: float = 0.0
    gate2_time_ms: float = 0.0

    # Metadata
    timestamp: str = ""
    error_message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def reset_database(db_path: str, scale_factor: float = 1.0):
    """Reset DuckDB to clean TPC-H state."""
    # Remove existing DB file for true cold start
    if os.path.exists(db_path):
        os.remove(db_path)

    con = duckdb.connect(db_path)
    con.execute("CREATE SCHEMA IF NOT EXISTS source")
    con.execute("INSTALL tpch; LOAD tpch;")
    con.execute(f"CALL dbgen(sf={scale_factor}, schema='source')")

    # Verify
    count = con.execute("SELECT COUNT(*) FROM source.orders").fetchone()[0]
    print(f"  [reset] source.orders: {count:,} rows (SF={scale_factor})")
    con.close()


def cold_start_connection(db_path: str, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Create a fresh DuckDB connection (cold start)."""
    return duckdb.connect(db_path, read_only=read_only)


# ---------------------------------------------------------------------------
# dbt helpers
# ---------------------------------------------------------------------------
def run_dbt(select: str, project_dir: str = DBT_PROJECT) -> tuple[str, float, str]:
    """Run dbt with given select, return (status, time_ms, error_msg).

    Returns:
        Tuple of (PipelineStatus, elapsed_ms, error_message)
    """
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["dbt", "run", "--select", select, "--project-dir", project_dir],
            capture_output=True, text=True, check=True,
            timeout=600,  # 10 min timeout
        )
        elapsed = (time.perf_counter() - start) * 1000
        return PipelineStatus.SUCCESS, elapsed, ""
    except subprocess.CalledProcessError as e:
        elapsed = (time.perf_counter() - start) * 1000
        error_msg = (e.stderr or e.stdout or str(e))[:500]
        return PipelineStatus.CRASH, elapsed, error_msg
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - start) * 1000
        return PipelineStatus.CRASH, elapsed, "dbt run timed out (600s)"


def swap_dbt_config(config_name: str, project_dir: str = DBT_PROJECT):
    """Swap dbt contract YAML based on config."""
    silver_dir = Path(project_dir) / "models" / "silver"
    target = silver_dir / "_silver_models.yml"

    if config_name in ("C0", "C2", "C3_standalone"):
        src = silver_dir / "_silver_models_no_contract.yml"
    else:  # C1, C3
        src = silver_dir / "_silver_models_with_contract.yml"

    if src.exists():
        shutil.copy(src, target)


# ---------------------------------------------------------------------------
# Core experiment runner
# ---------------------------------------------------------------------------
def run_single_experiment(
    mutation,
    config: dict,
    config_name: str,
    scale_factor: float = 1.0,
    run_index: int = 0,
    gate_mode: str = "quarantine",
) -> ExperimentResult:
    """Run one experiment: 1 mutation × 1 config.

    Implements the staged pipeline:
      Stage 1: dbt run bronze+silver → Gate 1 → quarantine
      Stage 2: dbt run gold → Gate 2 → metrics
    """
    exp_id = f"{mutation.name}__{config_name}__SF{scale_factor}__run{run_index}"
    result = ExperimentResult(
        experiment_id=exp_id,
        mutation_name=mutation.name,
        config_name=config_name,
        scale_factor=scale_factor,
        run_index=run_index,
        timestamp=datetime.now().isoformat(),
    )

    pipeline_start = time.perf_counter()

    try:
        # 0. Reset database (cold start)
        reset_database(DB_PATH, scale_factor)

        # 1. Apply mutation
        con = duckdb.connect(DB_PATH)
        mutation.apply(con)
        con.close()
        print(f"  [mutation] Applied: {mutation.name} ({mutation.description})")

        # 2. Swap dbt config
        swap_dbt_config(config_name)

        # 3. Stage 1: dbt run bronze + silver
        status1, time1, err1 = run_dbt("tag:bronze tag:silver")
        if status1 == PipelineStatus.CRASH:
            result.pipeline_status = PipelineStatus.CRASH
            result.measurement_type = MeasurementType.ASSIGNED_CRASH
            result.error_message = err1
            result.blast_radius = 0.0  # Data didn't reach Gold
            result.pipeline_time_ms = (time.perf_counter() - pipeline_start) * 1000
            _revert_and_close(mutation)
            return result

        # 4. MedalGuard Gate 1 (if enabled)
        if config.get("medalguard", False):
            try:
                gate1 = ContractGate(
                    gate_name="B->S",
                    contract_path=os.path.join(CONTRACTS_DIR, "bronze_to_silver", "orders.yaml"),
                    db_path=DB_PATH,
                    mode=gate_mode,
                    enabled_validators=_get_enabled_validators(config),
                )
                g1_result = gate1.validate_pre_transform(
                    source_table="bronze.bronze_orders",
                    injected_fault_count=mutation.injected_fault_count,
                )
                result.gate1_violations = len(g1_result.violations)
                result.gate1_time_ms = g1_result.validation_time_ms
                result.quarantined_rows = g1_result.quarantined_rows

                if not g1_result.passed:
                    result.detected = True
                    result.detection_stage = "PRE_TRANSFORM"
                    result.detection_depth = 0

                    if gate_mode == "block":
                        result.pipeline_status = PipelineStatus.BLOCKED
                        result.measurement_type = MeasurementType.ASSIGNED_BLOCK
                        result.blast_radius = 0.0
                        result.pipeline_time_ms = (time.perf_counter() - pipeline_start) * 1000
                        _revert_and_close(mutation)
                        return result

            except ContractViolationError:
                result.detected = True
                result.detection_stage = "PRE_TRANSFORM"
                result.detection_depth = 0
                result.pipeline_status = PipelineStatus.BLOCKED
                result.measurement_type = MeasurementType.ASSIGNED_BLOCK
                result.blast_radius = 0.0
                result.pipeline_time_ms = (time.perf_counter() - pipeline_start) * 1000
                _revert_and_close(mutation)
                return result

        # 5. Stage 2: dbt run gold
        status2, time2, err2 = run_dbt("tag:gold")
        if status2 == PipelineStatus.CRASH:
            result.pipeline_status = PipelineStatus.PARTIAL
            result.measurement_type = MeasurementType.ASSIGNED_CRASH
            result.error_message = err2
            result.blast_radius = 0.0
            result.pipeline_time_ms = (time.perf_counter() - pipeline_start) * 1000
            _revert_and_close(mutation)
            return result

        # 6. MedalGuard Gate 2 (if enabled)
        if config.get("medalguard", False):
            try:
                gate2 = ContractGate(
                    gate_name="S->G",
                    contract_path=os.path.join(CONTRACTS_DIR, "silver_to_gold", "revenue_by_nation.yaml"),
                    db_path=DB_PATH,
                    mode="log_only",  # Gate 2 is always log_only (data already in Gold)
                    enabled_validators=_get_enabled_validators(config),
                )
                g2_result = gate2.validate(
                    source_table="silver.silver_orders",
                    target_table="gold.gold_revenue_by_nation",
                    injected_fault_count=mutation.injected_fault_count,
                )
                result.gate2_violations = len(g2_result.violations)
                result.gate2_time_ms = g2_result.validation_time_ms
                result.blast_radius = g2_result.blast_radius

                if not g2_result.passed and not result.detected:
                    result.detected = True
                    result.detection_stage = "POST_TRANSFORM"
                    result.detection_depth = 2

            except Exception as e:
                result.error_message = f"Gate 2 error: {e}"

        # 7. GX validation (if enabled in config)
        if config.get("great_expectations", False):
            gx_detected = _run_gx_validation()
            if gx_detected and not result.detected:
                result.detected = True
                result.detection_stage = "POST_TRANSFORM"
                result.detection_depth = 2

        # 8. If nothing detected, measure blast radius from Gold
        if not result.detected:
            result.blast_radius = _measure_gold_blast_radius(
                mutation.injected_fault_count
            )
            result.measurement_type = MeasurementType.MEASURED

        result.pipeline_status = PipelineStatus.SUCCESS
        result.pipeline_time_ms = (time.perf_counter() - pipeline_start) * 1000

        # 9. Check quarantine effectiveness
        if result.quarantined_rows > 0:
            result.quarantine_effective = _check_quarantine_effectiveness()

    except Exception as e:
        result.pipeline_status = PipelineStatus.CRASH
        result.measurement_type = MeasurementType.ASSIGNED_CRASH
        result.error_message = str(e)[:500]
        result.pipeline_time_ms = (time.perf_counter() - pipeline_start) * 1000

    # 10. Revert mutation
    _revert_and_close(mutation)

    return result


# ---------------------------------------------------------------------------
# Overhead measurement (isolated, clean data only)
# ---------------------------------------------------------------------------
def measure_overhead(
    configs: dict[str, dict],
    scale_factor: float = 1.0,
    repeat_count: int = 7,
) -> dict[str, dict]:
    """Measure pipeline overhead on clean data (no mutations).

    Returns dict: config_name -> {times: [...], median_ms: float, overhead_pct: float}
    """
    results = {}

    for config_name, config in configs.items():
        times = []
        for i in range(repeat_count):
            # Cold start: fresh DB each run
            reset_database(DB_PATH, scale_factor)
            swap_dbt_config(config_name)

            start = time.perf_counter()

            # Stage 1
            run_dbt("tag:bronze tag:silver")

            # Gate 1 (if enabled)
            if config.get("medalguard", False):
                gate1 = ContractGate(
                    gate_name="B->S",
                    contract_path=os.path.join(CONTRACTS_DIR, "bronze_to_silver", "orders.yaml"),
                    db_path=DB_PATH,
                    mode="log_only",
                    enabled_validators=_get_enabled_validators(config),
                )
                gate1.validate_pre_transform("bronze.bronze_orders")

            # Stage 2
            run_dbt("tag:gold")

            # Gate 2 (if enabled)
            if config.get("medalguard", False):
                gate2 = ContractGate(
                    gate_name="S->G",
                    contract_path=os.path.join(CONTRACTS_DIR, "silver_to_gold", "revenue_by_nation.yaml"),
                    db_path=DB_PATH,
                    mode="log_only",
                    enabled_validators=_get_enabled_validators(config),
                )
                gate2.validate("silver.silver_orders", "gold.gold_revenue_by_nation")

            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
            print(f"  [overhead] {config_name} run {i+1}/{repeat_count}: {elapsed_ms:.1f} ms")

        results[config_name] = {
            "times": times,
            "median_ms": statistics.median(times),
            "mean_ms": statistics.mean(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
        }

    # Calculate overhead % relative to C0 baseline
    baseline_median = results.get("C0", {}).get("median_ms", 1.0)
    for config_name, data in results.items():
        data["overhead_pct"] = (
            (data["median_ms"] - baseline_median) / baseline_median * 100
            if baseline_median > 0 else 0.0
        )

    return results


# ---------------------------------------------------------------------------
# Matrix runner
# ---------------------------------------------------------------------------
def run_full_matrix(
    mutations: list,
    configs: dict[str, dict],
    scale_factor: float = 1.0,
    repeat_count: int = 1,
    random_seed: int = 42,
    randomize: bool = True,
) -> list[ExperimentResult]:
    """Run full experiment matrix with randomization and progress tracking."""

    # Build experiment list
    experiments = []
    for mutation in mutations:
        for config_name, config in configs.items():
            for run_idx in range(repeat_count):
                experiments.append((mutation, config, config_name, run_idx))

    # Randomize order
    if randomize:
        rng = random.Random(random_seed)
        rng.shuffle(experiments)

    total = len(experiments)
    results = []

    print(f"\n{'='*60}")
    print(f"MedalGuard Experiment Matrix: {total} experiments")
    print(f"SF={scale_factor}, seed={random_seed}, randomize={randomize}")
    print(f"{'='*60}\n")

    for idx, (mutation, config, config_name, run_idx) in enumerate(experiments, 1):
        print(f"\n[{idx}/{total}] {mutation.name} × {config_name} (run {run_idx})")
        print("-" * 40)

        result = run_single_experiment(
            mutation=mutation,
            config=config,
            config_name=config_name,
            scale_factor=scale_factor,
            run_index=run_idx,
        )
        results.append(result)

        # Save individual result
        _save_result(result)

        # Progress summary
        detected_count = sum(1 for r in results if r.detected)
        print(f"  → status={result.pipeline_status}, detected={result.detected}, "
              f"BR={result.blast_radius:.2%}, stage={result.detection_stage}")
        print(f"  Running DR: {detected_count}/{len(results)} "
              f"({detected_count/len(results)*100:.0f}%)")

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_enabled_validators(config: dict) -> set:
    """Get enabled validators from config, defaulting to all."""
    validators = config.get("enabled_validators")
    if validators:
        return set(validators)
    return {"schema", "constraint", "semantic"}


def _revert_and_close(mutation):
    """Revert mutation and close connection."""
    try:
        con = duckdb.connect(DB_PATH)
        mutation.revert(con)
        con.close()
    except Exception as e:
        print(f"  [warn] Failed to revert mutation: {e}")


def _run_gx_validation() -> bool:
    """Run Great Expectations validation. Returns True if violations found."""
    # TODO: Implement GX integration
    # This is a placeholder — actual GX validation will be implemented
    # when GX expectations are set up
    return False


def _measure_gold_blast_radius(injected_fault_count: int) -> float:
    """Measure actual blast radius by checking Gold table for faulty records."""
    if injected_fault_count == 0:
        return 0.0
    # Default: if pipeline completed and nothing was detected,
    # assume all faulty records reached Gold
    return 1.0


def _check_quarantine_effectiveness() -> bool:
    """Check if Gold contains only clean data after quarantine."""
    # TODO: Query Gold table and verify no quarantined records leaked through
    return True


def _save_result(result: ExperimentResult):
    """Save experiment result to JSON file."""
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    filename = f"{result.experiment_id}__{result.timestamp.replace(':', '')}.json"
    filepath = Path(RESULTS_DIR) / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)


def _load_config() -> dict:
    """Load experiment config from YAML."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    """Main entry point for experiment runner."""
    import argparse

    parser = argparse.ArgumentParser(description="MedalGuard Experiment Runner")
    parser.add_argument("--mode", choices=["matrix", "overhead", "single"],
                        default="matrix", help="Run mode")
    parser.add_argument("--sf", type=float, default=1.0, help="Scale factor")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-randomize", action="store_true", help="Disable randomization")
    parser.add_argument("--mutation", type=str, help="Single mutation name (for --mode single)")
    parser.add_argument("--config", type=str, help="Single config name (for --mode single)")

    args = parser.parse_args()

    config = _load_config()
    configs = config.get("configs", {})

    if args.mode == "overhead":
        print("Measuring pipeline overhead (clean data, no mutations)...")
        overhead_results = measure_overhead(
            configs=configs,
            scale_factor=args.sf,
            repeat_count=config.get("experiment", {}).get("repeat_count", 7),
        )
        # Save overhead results
        Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
        with open(Path(RESULTS_DIR) / "overhead_results.json", "w") as f:
            json.dump(overhead_results, f, indent=2)
        print("\nOverhead Results:")
        for name, data in overhead_results.items():
            print(f"  {name}: median={data['median_ms']:.1f}ms, "
                  f"overhead={data['overhead_pct']:+.1f}%")

    elif args.mode == "matrix":
        # Import all mutations
        from mutations.m1_additive import M1a_AddSingleCol, M1b_AddMultiCol
        from mutations.m2_destructive import M2a_DropNonKey, M2b_DropKeyCol, M2c_RenameCol
        from mutations.m3_type_change import M3a_DoubleToVarchar, M3b_IntegerToDouble, M3c_DateToVarchar
        from mutations.m4_constraint_breach import M4a_NullAndNegative, M4b_NullSmall, M4c_DuplicateKeys
        from mutations.m5_semantic_drift import M5a_MULTIPLY_100, M5b_MULTIPLY_1_5, M5c_CATEGORICAL_SHIFT

        fault_mutations = [
            M1a_AddSingleCol(sf=args.sf), M1b_AddMultiCol(sf=args.sf),
            M2a_DropNonKey(sf=args.sf), M2b_DropKeyCol(sf=args.sf), M2c_RenameCol(sf=args.sf),
            M3a_DoubleToVarchar(sf=args.sf), M3b_IntegerToDouble(sf=args.sf), M3c_DateToVarchar(sf=args.sf),
            M4a_NullAndNegative(sf=args.sf), M4b_NullSmall(sf=args.sf), M4c_DuplicateKeys(sf=args.sf),
            M5a_MULTIPLY_100(sf=args.sf), M5b_MULTIPLY_1_5(sf=args.sf), M5c_CATEGORICAL_SHIFT(sf=args.sf),
        ]

        results = run_full_matrix(
            mutations=fault_mutations,
            configs=configs,
            scale_factor=args.sf,
            repeat_count=1,
            random_seed=args.seed,
            randomize=not args.no_randomize,
        )

        # Summary
        print(f"\n{'='*60}")
        print(f"SUMMARY: {len(results)} experiments completed")
        detected = sum(1 for r in results if r.detected)
        print(f"Detection Rate: {detected}/{len(results)} ({detected/len(results)*100:.1f}%)")

    elif args.mode == "single":
        print(f"Single experiment: {args.mutation} × {args.config}")
        # TODO: Load specific mutation and config
        print("Not yet implemented for single mode. Use --mode matrix.")


if __name__ == "__main__":
    main()
