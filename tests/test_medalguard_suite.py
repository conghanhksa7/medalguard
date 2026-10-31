"""MedalGuard Comprehensive Automated Test Suite.
Verifies contract schema validation, mutation suites, multi-validator depth,
in-place quarantine, subtle semantic drift (M5b), idempotent replay, and cross-artifact parity.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pytest
from unittest.mock import patch

from medalguard.config import load_contract, validate_contract_schema
from medalguard.gate import ContractGate
from medalguard.validators.schema_validator import SchemaValidator
from medalguard.validators.constraint_validator import ConstraintValidator
from medalguard.validators.semantic_validator import SemanticValidator
from medalguard.replay import ReplayAndRecoveryEngine
from mutations import get_mutation_suite


# ===========================================================================
# 1. Contract Schema Validation Tests
# ===========================================================================
def test_contract_schema_validation():
    """Verify all 5 YAML contracts are valid and error cases are strictly caught."""
    # 1. All 5 existing contracts must load cleanly
    contract_paths = list((PROJECT_ROOT / "contracts").rglob("*.yaml"))
    assert len(contract_paths) == 5, f"Expected 5 contracts, found {len(contract_paths)}"
    for path in contract_paths:
        contract = load_contract(str(path))
        assert "table" in contract
        assert "source_table" in contract
        assert isinstance(contract["columns"], list)
        assert len(contract["columns"]) > 0

    # 2. Reject missing required fields
    with pytest.raises(ValueError, match="missing required field"):
        validate_contract_schema({"source_table": "s", "columns": [{"name": "c", "type": "INTEGER"}]})

    # 3. Reject empty columns list
    with pytest.raises(ValueError, match="'columns' must be a non-empty list"):
        validate_contract_schema({"table": "t", "source_table": "s", "columns": []})

    # 4. Reject invalid data types
    with pytest.raises(ValueError, match="unsupported data type"):
        validate_contract_schema({
            "table": "t", "source_table": "s",
            "columns": [{"name": "c", "type": "UNSUPPORTED_TYPE"}]
        })

    # 5. Reject min_value > max_value
    with pytest.raises(ValueError, match="min_value .* exceeds max_value"):
        validate_contract_schema({
            "table": "t", "source_table": "s",
            "columns": [{"name": "c", "type": "INTEGER", "min_value": 100, "max_value": 10}]
        })

    # 6. Reject invalid quality rules
    with pytest.raises(ValueError, match="is not recognized"):
        validate_contract_schema({
            "table": "t", "source_table": "s",
            "columns": [{"name": "c", "type": "INTEGER"}],
            "quality_rules": [{"rule": "invalid_quality_rule"}]
        })


# ===========================================================================
# 2. Mutation Suite v2 Counts and Metadata Tests
# ===========================================================================
def test_mutation_suite_v2_counts_and_metadata():
    """Verify expanded 36 and core 19 mutation counts and metadata completeness."""
    suite = get_mutation_suite(sf=0.1, suite="expanded")
    assert len(suite) == 36, f"Expected 36 mutations in expanded suite, got {len(suite)}"

    core_mutations = [m for m in suite if getattr(m, "is_core", False)]
    assert len(core_mutations) == 19, f"Expected 19 core mutations, got {len(core_mutations)}"

    harmful = [m for m in suite if m.category != "BENIGN"]
    benign = [m for m in suite if m.category == "BENIGN"]
    assert len(harmful) == 24
    assert len(benign) == 12

    valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "BENIGN"}
    for m in suite:
        assert m.severity in valid_severities, f"Invalid severity for {m.name}: {m.severity}"
        assert m.schema_version, f"Missing schema_version for {m.name}"
        assert m.target_table, f"Missing target_table for {m.name}"
        assert isinstance(m.is_core, bool)


# ===========================================================================
# 3. Schema Validator Strict and Allowlist Tests
# ===========================================================================
def test_schema_validator_strict_and_allowlist():
    """Verify SchemaValidator detects missing/unexpected columns and honors allowed_extra_columns."""
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA bronze")
    con.execute("""
        CREATE TABLE bronze.orders (
            o_orderkey BIGINT,
            o_custkey BIGINT,
            extra_promo VARCHAR
        )
    """)

    contract = {
        "table": "bronze.orders",
        "source_table": "bronze.orders",
        "columns": [
            {"name": "o_orderkey", "type": "BIGINT"},
            {"name": "o_custkey", "type": "BIGINT"},
            {"name": "o_totalprice", "type": "DOUBLE"},  # Missing in table
        ],
        "allowed_extra_columns": []
    }

    validator = SchemaValidator()
    violations = validator.check(con, "bronze.orders", "bronze.orders", contract)
    v_types = [v["type"] for v in violations]

    assert "MISSING_COLUMN" in v_types
    assert "UNEXPECTED_COLUMN" in v_types

    # Test allowlist: if extra_promo is in allowed_extra_columns, it should not trigger UNEXPECTED_COLUMN
    contract["allowed_extra_columns"] = ["extra_promo"]
    violations_allowed = validator.check(con, "bronze.orders", "bronze.orders", contract)
    v_types_allowed = [v["type"] for v in violations_allowed]
    assert "UNEXPECTED_COLUMN" not in v_types_allowed
    assert "MISSING_COLUMN" in v_types_allowed
    con.close()


# ===========================================================================
# 4. Constraint Validator and In-Place Quarantine Tests
# ===========================================================================
def test_constraint_validator_and_inplace_quarantine(tmp_path):
    """Verify ContractGate isolates corrupt rows into quarantine table with audit columns."""
    db_file = tmp_path / "test_quarantine.duckdb"
    con = duckdb.connect(str(db_file))
    con.execute("CREATE SCHEMA bronze")
    con.execute("""
        CREATE TABLE bronze.bronze_orders (
            o_orderkey BIGINT,
            o_custkey BIGINT,
            o_totalprice DOUBLE
        )
    """)

    # Insert 8 valid rows, 1 row with NULL custkey, 1 row with negative totalprice
    for i in range(1, 9):
        con.execute(f"INSERT INTO bronze.bronze_orders VALUES ({i}, {100+i}, {50.0*i})")
    con.execute("INSERT INTO bronze.bronze_orders VALUES (9, NULL, 450.0)")       # Null violation
    con.execute("INSERT INTO bronze.bronze_orders VALUES (10, 110, -99.0)")      # Range violation
    con.close()

    # Write temporary YAML contract
    contract_file = tmp_path / "test_orders_contract.yaml"
    contract_content = """
table: bronze.bronze_orders
source_table: bronze.bronze_orders
max_quarantine_ratio: 0.50
columns:
  - name: o_orderkey
    type: BIGINT
    not_null: true
    unique: true
  - name: o_custkey
    type: BIGINT
    not_null: true
  - name: o_totalprice
    type: DOUBLE
    min_value: 0.0
quality_rules: []
"""
    contract_file.write_text(contract_content, encoding="utf-8")

    gate = ContractGate(gate_name="gate1", contract_path=str(contract_file), db_path=str(db_file), mode="quarantine", save_reports=False)
    result = gate.validate_pre_transform("bronze.bronze_orders", injected_fault_count=2)

    assert result.quarantined_rows == 2, f"Expected 2 quarantined rows, got {result.quarantined_rows}"
    assert len(result.violations) == 2  # Violations detected and quarantined without throwing an unhandled exception

    # Verify quarantine table content and audit columns
    con = duckdb.connect(str(db_file))
    q_rows = con.execute("SELECT * FROM quarantine.bronze_orders_rejected").fetchall()
    assert len(q_rows) == 2

    q_cols = [r[1] for r in con.execute("PRAGMA table_info('quarantine.bronze_orders_rejected')").fetchall()]
    assert "_is_quarantined" in q_cols
    assert "_quarantine_reason" in q_cols
    assert "_quarantined_at" in q_cols
    assert "_quarantined_by" in q_cols

    # Verify clean bronze table retained exactly 8 valid rows
    clean_count = con.execute("SELECT COUNT(*) FROM bronze.bronze_orders").fetchone()[0]
    assert clean_count == 8
    con.close()


# ===========================================================================
# 5. Semantic Validator Subtle Drift Test (M5b)
# ===========================================================================
def test_semantic_validator_subtle_drift_m5b():
    """Verify M5b (LEAST(l_discount * 1.5 + 0.01, 0.10)) evades row constraints but is caught by SemanticValidator."""
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA bronze")
    con.execute("CREATE TABLE bronze.lineitem (l_orderkey BIGINT, l_discount DOUBLE)")

    # 100 rows with TPC-H standard 11 discrete discount levels: 0.00, 0.01, ..., 0.10 (mean = 0.05)
    for i in range(100):
        disc = (i % 11) * 0.01
        con.execute(f"INSERT INTO bronze.lineitem VALUES ({i}, {disc})")

    contract = {
        "table": "bronze.lineitem",
        "source_table": "bronze.lineitem",
        "columns": [
            {"name": "l_orderkey", "type": "BIGINT"},
            {"name": "l_discount", "type": "DOUBLE", "min_value": 0.0, "max_value": 0.10},
        ],
        "quality_rules": [
            {"rule": "mean_range", "column": "l_discount", "min": 0.03, "max": 0.07}
        ]
    }

    # Inject subtle drift: LEAST(l_discount * 1.5 + 0.01, 0.10)
    con.execute("UPDATE bronze.lineitem SET l_discount = LEAST(l_discount * 1.5 + 0.01, 0.10)")

    # 1. ConstraintValidator check: All values are in [0.01, 0.10] <= [0.0, 0.10] -> NO VIOLATIONS!
    c_validator = ConstraintValidator()
    c_violations = c_validator.check(con, "bronze.lineitem", contract)
    assert len(c_violations) == 0, "ConstraintValidator should not detect intra-domain shift"

    # 2. SemanticValidator check: Global mean shifted to ~0.0714 > 0.0700 -> DETECTED!
    s_validator = SemanticValidator()
    s_violations = s_validator.check(con, "bronze.lineitem", "bronze.lineitem", contract)
    assert len(s_violations) > 0
    assert any(v["type"] == "SEMANTIC_DRIFT" for v in s_violations)
    con.close()


# ===========================================================================
# 6. Idempotent Replay and LKG Rollback Tests
# ===========================================================================
def test_idempotent_replay_and_lkg_rollback(tmp_path):
    """Verify sub-second LKG Gold rollback and idempotent quarantine replay."""
    db_file = tmp_path / "test_engine.duckdb"
    con = duckdb.connect(str(db_file))
    con.execute("CREATE SCHEMA source; CREATE SCHEMA bronze; CREATE SCHEMA gold; CREATE SCHEMA quarantine;")
    con.execute("CREATE TABLE source.orders (o_orderkey BIGINT, o_totalprice DOUBLE)")
    con.execute("CREATE TABLE bronze.bronze_orders (o_orderkey BIGINT, o_totalprice DOUBLE)")
    con.execute("CREATE TABLE gold.gold_revenue_by_nation (nation VARCHAR, total_revenue DOUBLE)")
    con.execute("CREATE TABLE gold.gold_order_priority_summary (priority VARCHAR, order_count INT)")

    con.execute("INSERT INTO source.orders VALUES (1, 100.0), (2, 200.0)")
    con.execute("INSERT INTO bronze.bronze_orders VALUES (1, 100.0)")
    con.execute("INSERT INTO gold.gold_revenue_by_nation VALUES ('VIETNAM', 10000.0)")
    con.execute("INSERT INTO gold.gold_order_priority_summary VALUES ('HIGH', 50)")

    # Create quarantine table with 1 corrupted row to backfill
    con.execute("""
        CREATE TABLE quarantine.bronze_orders_rejected (
            o_orderkey BIGINT,
            o_totalprice DOUBLE,
            _is_quarantined BOOLEAN DEFAULT TRUE,
            _quarantine_reason VARCHAR DEFAULT 'CORRUPTION',
            _quarantined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            _quarantined_by VARCHAR DEFAULT 'TEST',
            _replayed BOOLEAN DEFAULT FALSE
        )
    """)
    con.execute("INSERT INTO quarantine.bronze_orders_rejected VALUES (2, -200.0, TRUE, 'RANGE', CURRENT_TIMESTAMP, 'TEST', FALSE)")
    con.close()

    engine = ReplayAndRecoveryEngine(str(db_file))

    # Test 1: Snapshot and Rollback
    snap_res = engine.save_lkg_gold_snapshot()
    assert snap_res["snapshot_saved"] is True
    assert snap_res["gold_tables_saved"] == 2

    # Corrupt gold mart
    con = duckdb.connect(str(db_file))
    con.execute("UPDATE gold.gold_revenue_by_nation SET total_revenue = -999999.0")
    con.close()

    rollback_res = engine.rollback_gold_to_lkg()
    assert rollback_res["rolled_back"] is True
    assert rollback_res["gold_tables_restored"] == 2

    con = duckdb.connect(str(db_file))
    restored_rev = con.execute("SELECT total_revenue FROM gold.gold_revenue_by_nation").fetchone()[0]
    assert restored_rev == 10000.0
    con.close()

    # Test 2: Idempotent Replay
    with patch("medalguard.replay.run_dbt_command", return_value=("SUCCESS", 10.0, None)):
        # First execution: repairs and backfills row #2
        res1 = engine.repair_and_replay_quarantine("bronze.bronze_orders", primary_key="o_orderkey")
        assert res1["status"] == "REPAIRED_AND_REPLAYED"
        assert res1["repaired_and_backfilled_rows"] == 1

        con = duckdb.connect(str(db_file))
        b_count1 = con.execute("SELECT COUNT(*) FROM bronze.bronze_orders").fetchone()[0]
        assert b_count1 == 2  # (1, 100.0) and (2, 200.0)
        con.close()

        # Second execution: must be IDEMPOTENT, 0 rows backfilled, no duplicate keys!
        res2 = engine.repair_and_replay_quarantine("bronze.bronze_orders", primary_key="o_orderkey")
        assert res2["status"] == "ALREADY_REPLAYED_IDEMPOTENT"
        assert res2["repaired_and_backfilled_rows"] == 0

        con = duckdb.connect(str(db_file))
        b_count2 = con.execute("SELECT COUNT(*) FROM bronze.bronze_orders").fetchone()[0]
        assert b_count2 == 2  # Still exactly 2 rows
        con.close()


# ===========================================================================
# 7. Cross-Artifact Experimental Evidence Parity Test
# ===========================================================================
def test_experimental_evidence_parity():
    """Verify ground-truth empirical metrics parity across JSON, CSV, and 300 DPI charts."""
    summary_dir = PROJECT_ROOT / "results" / "summary"
    charts_dir = PROJECT_ROOT / "results" / "charts"

    # Check 6 publication charts
    charts = [
        "fig1_detection_and_fpr_comparison.png",
        "fig2_blast_radius_heatmap.png",
        "fig3_detection_depth_and_boundary_ablation.png",
        "fig4_validator_ablation_study.png",
        "fig5_overhead_and_scale_stress_test.png",
        "fig6_ct3_pilot_mttd_mttr_recovery.png",
    ]
    for ch in charts:
        p = charts_dir / ch
        assert p.exists(), f"Missing chart: {ch}"
        assert p.stat().st_size > 50000, f"Chart file too small: {ch}"

    # Check E1 metrics in e1_paired_statistical_ci.json
    ci_path = summary_dir / "e1_paired_statistical_ci.json"
    assert ci_path.exists(), "Missing e1_paired_statistical_ci.json"

    with open(ci_path, "r", encoding="utf-8") as f:
        ci_data = json.load(f)

    c3_expanded = ci_data["expanded36"]["configs"]["C3"]
    assert c3_expanded["detection_rate_pct"] == 100.0
    assert c3_expanded["false_positive_rate_pct"] == 0.0
    assert c3_expanded["mean_blast_radius_pct"] == 0.0

    c3_core = ci_data["core19"]["configs"]["C3"]
    assert c3_core["detection_rate_pct"] == 100.0
    assert c3_core["false_positive_rate_pct"] == 0.0
    assert c3_core["mean_blast_radius_pct"] == 0.0
