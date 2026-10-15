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
    """Raised when MedalGuard gate is in 'block' mode and violations are found."""
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


class ContractGate:
    """Validates data at a layer boundary using contract definitions."""

    ALL_VALIDATORS = {"schema", "constraint", "semantic"}

    def __init__(self, gate_name: str, contract_path: str,
                 db_path: str, mode: str = "log_only",
                 enabled_validators: set | None = None):
        self.gate_name = gate_name
        self.contract = load_contract(contract_path)
        self.db_path = db_path
        self.mode = mode
        self.enabled_validators = enabled_validators or self.ALL_VALIDATORS
        self.schema_validator = SchemaValidator()
        self.constraint_validator = ConstraintValidator()
        self.semantic_validator = SemanticValidator()
        self.reporter = ViolationReporter()

    def validate_pre_transform(self, source_table: str, injected_fault_count: int = 0) -> ValidationResult:
        """Run Gate 1: pre-transform validation on source (Bronze).
        
        Args:
            source_table: Upstream table (e.g., 'bronze.orders')
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

        if self.mode == "quarantine" and violations:
            quarantined_rows = self._quarantine_bad_records(con, violations, source_table)
        elif self.mode == "quarantine":
            # If no violations, just create clean view as select *
            schema_name, table_name = parse_table_ref(source_table)
            q_schema = quote_identifier(schema_name)
            q_table = quote_identifier(table_name)
            q_clean = quote_identifier(f"{table_name}_clean")
            con.execute(f"CREATE OR REPLACE VIEW {q_schema}.{q_clean} AS SELECT * FROM {q_schema}.{q_table}")
            
        con.close()

        measurement_type = MeasurementType.MEASURED
        blast_radius = 0.0

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
            quarantined_rows=quarantined_rows
        )

        self.reporter.save_report(
            self.gate_name, violations, blast_radius
        )

        if self.mode == "block" and not passed:
            raise ContractViolationError(violations)

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

        Creates a table like 'quarantine.{table_name}_rejected' and
        a clean view '{schema}.{table_name}_clean' excluding them.
        """
        con.execute("CREATE SCHEMA IF NOT EXISTS quarantine")

        schema_name, table_name = parse_table_ref(source_table)
        q_schema = quote_identifier(schema_name)
        q_table = quote_identifier(table_name)
        q_clean = quote_identifier(f"{table_name}_clean")
        q_quarantine = quote_identifier(f"{table_name}_rejected")

        # Build WHERE clause from constraint violations
        conditions = []
        for v in violations:
            col = v.get("column")
            if not col:
                continue

            q_col = quote_identifier(col)

            if v["type"] == "NULL_VIOLATION":
                conditions.append(f"{q_col} IS NULL")
            elif v["type"] == "RANGE_VIOLATION":
                constraint = v.get("constraint", "")
                if ">=" in constraint:
                    min_val = constraint.replace(">=", "").strip()
                    conditions.append(f"{q_col} < {min_val}")
                elif "<=" in constraint:
                    max_val = constraint.replace("<=", "").strip()
                    conditions.append(f"{q_col} > {max_val}")
            elif v["type"] == "ALLOWED_VALUES_VIOLATION":
                allowed = v.get("allowed", [])
                values_str = ", ".join(f"'{val}'" for val in allowed)
                conditions.append(
                    f"({q_col} IS NOT NULL AND {q_col} NOT IN ({values_str}))"
                )

        if not conditions:
            con.execute(f"CREATE OR REPLACE VIEW {q_schema}.{q_clean} AS SELECT * FROM {q_schema}.{q_table}")
            return 0

        where_bad = " OR ".join(f"({c})" for c in conditions)

        # Move bad records to quarantine
        con.execute(f"""
            CREATE OR REPLACE TABLE quarantine.{q_quarantine} AS
            SELECT *, CURRENT_TIMESTAMP AS _quarantined_at,
                   '{self.gate_name}' AS _quarantined_by
            FROM {q_schema}.{q_table}
            WHERE {where_bad}
        """)

        quarantined = con.execute(
            f"SELECT COUNT(*) FROM quarantine.{q_quarantine}"
        ).fetchone()[0]

        # Create clean view
        con.execute(f"""
            CREATE OR REPLACE VIEW {q_schema}.{q_clean} AS
            SELECT *
            FROM {q_schema}.{q_table}
            WHERE NOT ({where_bad})
        """)

        return quarantined


if __name__ == "__main__":
    import argparse
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

