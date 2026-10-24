"""MedalGuard ContractGate: Core validation orchestrator.

Supports staged pipeline execution:
  Stage 1: validate_pre_transform() on Bronze -> quarantine bad rows -> create clean view
  Stage 2: dbt run --select silver (references clean view)
  Stage 3: validate() on Silver -> check post-transform quality
  Stage 4: dbt run --select gold
"""
import duckdb
import time
from dataclasses import dataclass, field
from enum import Enum

from .config import load_contract
from .validators.schema_validator import SchemaValidator
from .validators.constraint_validator import ConstraintValidator
from .validators.semantic_validator import SemanticValidator
from .reporter import ViolationReporter
from .utils import quote_identifier, quote_table, parse_table_ref


class ContractViolationError(Exception):
    """Raised when MedalGuard gate blocks a pipeline due to contract violations."""
    def __init__(self, violations: list[dict]):
        self.violations = violations
        super().__init__(f"Contract violated: {len(violations)} violations found")


class MeasurementType(str, Enum):
    MEASURED = "MEASURED"
    ASSIGNED_BLOCK = "ASSIGNED_BLOCK"
    ASSIGNED_CRASH = "ASSIGNED_CRASH"


@dataclass
class ValidationResult:
    """Result of a gate validation run."""
    gate_name: str
    passed: bool
    violations: list = field(default_factory=list)
    blast_radius: float = 0.0
    measurement_type: str = MeasurementType.MEASURED
    detection_stage: str = ""
    validation_time_ms: float = 0.0
    quarantined_rows: int = 0


BLOCKING_TYPES = {
    "MISSING_COLUMN", "TYPE_MISMATCH", "UNEXPECTED_COLUMN",
    "TABLE_NOT_FOUND", "SEMANTIC_DRIFT", "ROW_COUNT_LOW", "NULL_RATE_EXCEEDED"
}
QUARANTINABLE_TYPES = {
    "NULL_VIOLATION", "RANGE_VIOLATION", "ALLOWED_VALUES_VIOLATION", "UNIQUE_VIOLATION"
}


class ContractGate:
    """Validates data at a layer boundary using contract definitions."""

    ALL_VALIDATORS = {"schema", "constraint", "semantic"}
    BLOCKING_TYPES = BLOCKING_TYPES
    QUARANTINABLE_TYPES = QUARANTINABLE_TYPES

    def __init__(self, gate_name: str, contract_path: str,
                 db_path: str, mode: str = "log_only",
                 enabled_validators: set | None = None):
        self.gate_name = gate_name
        self.contract = load_contract(contract_path)
        self.db_path = db_path
        self.mode = mode
        self.enabled_validators = set(enabled_validators) if enabled_validators is not None else self.ALL_VALIDATORS
        self.schema_validator = SchemaValidator()
        self.constraint_validator = ConstraintValidator()
        self.semantic_validator = SemanticValidator()
        self.reporter = ViolationReporter()

    def validate_pre_transform(self, source_table: str, injected_fault_count: int = 0) -> ValidationResult:
        """Run Gate 1: pre-transform validation on source (Bronze).
        
        Args:
            source_table: Upstream table (e.g., 'bronze.bronze_orders')
            injected_fault_count: For blast radius calculation
        """
        start = time.perf_counter()
        violations = []
        con = duckdb.connect(self.db_path, read_only=False)

        if "schema" in self.enabled_validators:
            violations += self.schema_validator.check(
                con, source_table, source_table, self.contract
            )

        if "constraint" in self.enabled_validators:
            violations += self.constraint_validator.check(
                con, source_table, self.contract
            )

        if "semantic" in self.enabled_validators:
            violations += self.semantic_validator.check(
                con, source_table, source_table, self.contract
            )

        elapsed_ms = (time.perf_counter() - start) * 1000

        quarantined_rows = 0
        passed = len(violations) == 0

        has_blocking_violation = any(v.get("type") in self.BLOCKING_TYPES for v in violations)

        if violations and not has_blocking_violation:
            q_table_full = quote_table(source_table)
            total_rows = con.execute(f"SELECT COUNT(*) FROM {q_table_full}").fetchone()[0]
            affected_sum = sum(v.get("affected_rows", 0) for v in violations)
            max_ratio = float(self.contract.get("max_quarantine_ratio", 0.05))
            if total_rows > 0 and (affected_sum / total_rows) > max_ratio:
                has_blocking_violation = True

        measurement_type = MeasurementType.MEASURED
        blast_radius = 0.0

        if not passed:
            if self.mode == "block" or (self.mode == "quarantine" and has_blocking_violation):
                measurement_type = MeasurementType.ASSIGNED_BLOCK
                blast_radius = 0.0
                con.close()
                self.reporter.save_report(self.gate_name, violations, blast_radius)
                raise ContractViolationError(violations)
            elif self.mode == "quarantine" and not has_blocking_violation:
                quarantined_rows = self._quarantine_bad_records(con, violations, source_table)
        else:
            if self.mode == "quarantine":
                schema_name, table_name = parse_table_ref(source_table)
                q_schema = quote_identifier(schema_name)
                q_table = quote_identifier(table_name)
                q_clean = quote_identifier(f"{table_name}_clean")
                con.execute(f"CREATE OR REPLACE VIEW {q_schema}.{q_clean} AS SELECT * FROM {q_schema}.{q_table}")

        con.close()

        result = ValidationResult(
            gate_name=self.gate_name,
            passed=passed,
            violations=violations,
            blast_radius=blast_radius,
            measurement_type=measurement_type,
            detection_stage=self.gate_name if violations else "",
            validation_time_ms=elapsed_ms,
            quarantined_rows=quarantined_rows
        )

        self.reporter.save_report(
            self.gate_name, violations, blast_radius
        )

        return result

    def validate(self, source_table: str, target_table: str, injected_fault_count: int = 0) -> ValidationResult:
        """Run Gate 2: post-transform validation.
        
        Args:
            source_table: Upstream table
            target_table: Downstream table (e.g., 'silver.orders')
            injected_fault_count: For blast radius calculation
        """
        start = time.perf_counter()
        violations = []
        con = duckdb.connect(self.db_path, read_only=True)

        if "schema" in self.enabled_validators:
            violations += self.schema_validator.check(
                con, source_table, target_table, self.contract
            )

        if "constraint" in self.enabled_validators:
            violations += self.constraint_validator.check(
                con, target_table, self.contract
            )

        if "semantic" in self.enabled_validators:
            violations += self.semantic_validator.check(
                con, source_table, target_table, self.contract
            )

        con.close()
        elapsed_ms = (time.perf_counter() - start) * 1000

        blast_radius = self.reporter.calculate_blast_radius(
            injected_fault_count, self.db_path, target_table, violations
        )
        measurement_type = MeasurementType.MEASURED

        passed = len(violations) == 0

        if self.mode == "block" and not passed:
            measurement_type = MeasurementType.ASSIGNED_BLOCK
            blast_radius = 0.0

        result = ValidationResult(
            gate_name=self.gate_name,
            passed=passed,
            violations=violations,
            blast_radius=blast_radius,
            measurement_type=measurement_type,
            detection_stage=self.gate_name if violations else "",
            validation_time_ms=elapsed_ms,
            quarantined_rows=0
        )

        self.reporter.save_report(
            self.gate_name, violations, blast_radius
        )

        if self.mode == "block" and not passed:
            raise ContractViolationError(violations)

        return result

    def _quarantine_bad_records(self, con: duckdb.DuckDBPyConnection, violations: list[dict],
                                 source_table: str) -> int:
        """Move bad records to quarantine table, create clean view/table.

        Creates table 'quarantine.{table_name}_rejected',
        overwrites '{schema}.{table_name}' with clean rows,
        and creates view '{schema}.{table_name}_clean'.
        """
        con.execute("CREATE SCHEMA IF NOT EXISTS quarantine")

        schema_name, table_name = parse_table_ref(source_table)
        q_schema = quote_identifier(schema_name)
        q_table = quote_identifier(table_name)
        q_clean = quote_identifier(f"{table_name}_clean")
        q_quarantine = quote_identifier(f"{table_name}_rejected")

        conditions = []
        for v in violations:
            col = v.get("column")
            if not col:
                continue

            q_col = quote_identifier(col)
            v_type = v.get("type")

            if v_type == "NULL_VIOLATION":
                conditions.append(f"({q_col} IS NULL)")
            elif v_type == "RANGE_VIOLATION":
                constraint = v.get("constraint", "")
                if ">=" in constraint:
                    min_val = constraint.replace(">=", "").strip()
                    conditions.append(f"({q_col} IS NOT NULL AND {q_col} < {min_val})")
                elif "<=" in constraint:
                    max_val = constraint.replace("<=", "").strip()
                    conditions.append(f"({q_col} IS NOT NULL AND {q_col} > {max_val})")
            elif v_type == "ALLOWED_VALUES_VIOLATION":
                allowed = v.get("allowed", [])
                values_str = ", ".join(f"'{val}'" for val in allowed)
                conditions.append(
                    f"({q_col} IS NOT NULL AND {q_col} NOT IN ({values_str}))"
                )
            elif v_type == "UNIQUE_VIOLATION":
                conditions.append(
                    f"(ROW_NUMBER() OVER (PARTITION BY {q_col} ORDER BY {q_col}) > 1)"
                )

        if not conditions:
            con.execute(f"CREATE OR REPLACE VIEW {q_schema}.{q_clean} AS SELECT * FROM {q_schema}.{q_table}")
            return 0

        where_bad = " OR ".join(conditions)
        gate_name_escaped = self.gate_name.replace("'", "''")

        # 1. Tag bad records into temp table
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE _mg_tagged AS
            SELECT *,
                   COALESCE({where_bad}, FALSE) AS _mg_is_bad
            FROM {q_schema}.{q_table}
        """)

        # 2. Write bad records to quarantine table
        con.execute(f"""
            CREATE OR REPLACE TABLE quarantine.{q_quarantine} AS
            SELECT * EXCLUDE (_mg_is_bad),
                   CURRENT_TIMESTAMP AS _quarantined_at,
                   '{gate_name_escaped}' AS _quarantined_by
            FROM _mg_tagged
            WHERE _mg_is_bad
        """)

        quarantined = con.execute(
            f"SELECT COUNT(*) FROM quarantine.{q_quarantine}"
        ).fetchone()[0]

        # 3. Overwrite source table with clean records directly
        con.execute(f"""
            CREATE OR REPLACE TABLE {q_schema}.{q_table} AS
            SELECT * EXCLUDE (_mg_is_bad)
            FROM _mg_tagged
            WHERE NOT _mg_is_bad
        """)

        # 4. Create clean view pointing to clean table
        con.execute(f"""
            CREATE OR REPLACE VIEW {q_schema}.{q_clean} AS
            SELECT * FROM {q_schema}.{q_table}
        """)

        # 5. Clean up temp table
        con.execute("DROP TABLE IF EXISTS _mg_tagged")

        return quarantined


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="MedalGuard ContractGate CLI")
    parser.add_argument(
        "--contract",
        default="contracts/bronze_to_silver/orders.yaml",
        help="Path to contract YAML file",
    )
    parser.add_argument(
        "--db",
        default="data/warehouse.duckdb",
        help="Path to DuckDB database",
    )
    parser.add_argument(
        "--mode",
        choices=["log_only", "block", "quarantine"],
        default="log_only",
        help="Validation mode",
    )
    parser.add_argument(
        "--pre-transform",
        action="store_true",
        help="Run pre-transform gate (Gate 1 on bronze/source)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    db_path = str(project_root / args.db) if not Path(args.db).is_absolute() else args.db
    contract_path = str(project_root / args.contract) if not Path(args.contract).is_absolute() else args.contract

    print(f"=== MedalGuard ContractGate ===")
    print(f"Contract: {contract_path}")
    print(f"Database: {db_path}")
    print(f"Mode:     {args.mode}")

    if not Path(db_path).exists():
        print(f"Error: Database {db_path} does not exist. Run scripts/generate_tpch.py first.")
        sys.exit(1)

    gate = ContractGate(
        gate_name="CLI-Gate",
        contract_path=contract_path,
        db_path=db_path,
        mode=args.mode,
    )

    src_tbl = gate.contract.get("source_table", "bronze.orders")
    tgt_tbl = gate.contract.get("table", "silver.orders")

    if args.pre_transform:
        res = gate.validate_pre_transform(src_tbl)
    else:
        res = gate.validate(src_tbl, tgt_tbl)

    print("\n--- Validation Result ---")
    print(f"Passed:           {res.passed}")
    print(f"Violations count: {len(res.violations)}")
    print(f"Quarantined rows: {res.quarantined_rows}")
    print(f"Measurement type: {res.measurement_type.value}")
    if res.violations:
        print("\nViolations:")
        for v in res.violations:
            print(f"  - [{v.get('type')}] {v.get('column', '')}: {v.get('rule', '')} (details: {v})")
    print("===============================")
