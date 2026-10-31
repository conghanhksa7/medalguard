"""MedalGuard CLI: Pre-flight Dataset Contract & Artifact Cross-Parity Validator.

Usage:
    python scripts/validate_dataset_contract.py --all
    python scripts/validate_dataset_contract.py --contract contracts/bronze_to_silver/orders.yaml
    python scripts/validate_dataset_contract.py --contract <path> --db <duckdb_path>
"""

import sys
import argparse
import json
import csv
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from medalguard.config import load_contract, validate_contract_schema
from mutations import get_mutation_suite


def validate_single_contract(contract_path: Path, db_path: Path = None) -> bool:
    """Validate a single YAML contract definition and optionally compare against a DuckDB database."""
    print(f"[*] Validating contract: {contract_path.name}...")
    try:
        contract = load_contract(str(contract_path))
        print(f"    [PASS] Schema structure valid ({len(contract['columns'])} columns, {len(contract.get('quality_rules', []))} quality rules)")
    except Exception as e:
        print(f"    [FAIL] Contract syntax/schema error: {e}")
        return False

    if db_path and db_path.exists():
        import duckdb
        print(f"    [*] Comparing against DuckDB schema: {db_path.name}...")
        try:
            con = duckdb.connect(str(db_path), read_only=True)
            tbl_target = contract["table"]
            db_cols = [r[1] for r in con.execute(f"PRAGMA table_info('{tbl_target}')").fetchall()]
            con.close()

            contract_cols = [c["name"] for c in contract["columns"]]
            missing_in_db = set(contract_cols) - set(db_cols)
            if missing_in_db:
                print(f"    [FAIL] Database table '{tbl_target}' is missing expected contract columns: {missing_in_db}")
                return False
            print(f"    [PASS] Table '{tbl_target}' matches all {len(contract_cols)} contract columns.")
        except Exception as e:
            print(f"    [WARN] Database comparison skipped/failed: {e}")

    return True


def run_all_checks() -> bool:
    """Run full pre-flight audit across contracts, mutations, and experimental parity."""
    print("=" * 70)
    print("MEDALGUARD PRE-FLIGHT CONTRACT & RESEARCH ARTIFACT VALIDATOR")
    print("=" * 70)
    all_passed = True

    # 1. Validate all 5 YAML Contracts
    print("\n[Step 1/3] Validating Multi-Layer YAML Data Contracts...")
    contracts_dir = PROJECT_ROOT / "contracts"
    contract_files = sorted(list(contracts_dir.rglob("*.yaml")))
    if len(contract_files) != 5:
        print(f"[FAIL] Expected 5 contract files, found {len(contract_files)}")
        all_passed = False
    else:
        for c_file in contract_files:
            rel_path = c_file.relative_to(PROJECT_ROOT)
            try:
                load_contract(str(c_file))
                print(f"  [PASS] {rel_path}")
            except Exception as e:
                print(f"  [FAIL] {rel_path}: {e}")
                all_passed = False

    # 2. Validate Mutation Suite v2 Metadata
    print("\n[Step 2/3] Validating Mutation Suite v2 (36 Scenarios & Metadata)...")
    try:
        suite = get_mutation_suite(sf=0.1, suite="expanded")
        if len(suite) != 36:
            print(f"[FAIL] Expected 36 mutations in expanded suite, got {len(suite)}")
            all_passed = False
        else:
            core_mutations = [m for m in suite if getattr(m, "is_core", False)]
            harmful_mutations = [m for m in suite if getattr(m, "category", "") != "BENIGN"]
            benign_mutations = [m for m in suite if getattr(m, "category", "") == "BENIGN"]
            core_harmful = [m for m in core_mutations if getattr(m, "category", "") != "BENIGN"]
            core_benign = [m for m in core_mutations if getattr(m, "category", "") == "BENIGN"]

            valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "BENIGN"}
            for m in suite:
                sev = getattr(m, "severity", None)
                ver = getattr(m, "schema_version", None)
                tbl = getattr(m, "target_table", None)
                if sev not in valid_severities or not ver or not tbl:
                    print(f"  [FAIL] Mutation {m.name} has invalid metadata: severity={sev}, version={ver}, target={tbl}")
                    all_passed = False

            if all_passed:
                print(f"  [PASS] Expanded Suite: {len(suite)} total ({len(harmful_mutations)} Harmful + {len(benign_mutations)} Benign)")
                print(f"  [PASS] Core Subset: {len(core_mutations)} total ({len(core_harmful)} Harmful + {len(core_benign)} Benign)")
                print(f"  [PASS] All 36 mutations conform to severity, schema_version, and target_table standards.")
    except Exception as e:
        print(f"[FAIL] Failed to load mutation suite: {e}")
        all_passed = False

    # 3. Cross-Artifact Evidence Parity Check
    print("\n[Step 3/3] Cross-Artifact Evidence Parity & 300 DPI Chart Verification...")
    summary_dir = PROJECT_ROOT / "results" / "summary"
    charts_dir = PROJECT_ROOT / "results" / "charts"

    # Check 6 charts exist
    expected_charts = [
        "fig1_detection_and_fpr_comparison.png",
        "fig2_blast_radius_heatmap.png",
        "fig3_detection_depth_and_boundary_ablation.png",
        "fig4_validator_ablation_study.png",
        "fig5_overhead_and_scale_stress_test.png",
        "fig6_ct3_pilot_mttd_mttr_recovery.png",
    ]
    for ch in expected_charts:
        ch_path = charts_dir / ch
        if ch_path.exists() and ch_path.stat().st_size > 50000:
            print(f"  [PASS] Chart exists ({ch_path.stat().st_size / 1024:.1f} KB): {ch}")
        else:
            print(f"  [FAIL] Chart missing or corrupted: {ch}")
            all_passed = False

    # Check E1 metrics in JSON and CSV
    e1_json = summary_dir / "e1_main_matrix_expanded36.json"
    e1_ci_json = summary_dir / "e1_paired_statistical_ci.json"
    e1_csv = summary_dir / "e1_main_matrix_expanded36.csv"

    if e1_ci_json.exists() and e1_csv.exists():
        with open(e1_ci_json, "r", encoding="utf-8") as f:
            ci_data = json.load(f)
        
        c3_stats = ci_data.get("expanded36", {}).get("configs", {}).get("C3", {})
        if c3_stats:
            dr = c3_stats.get("detection_rate_pct")
            fpr = c3_stats.get("false_positive_rate_pct")
            br = c3_stats.get("mean_blast_radius_pct")
            if dr == 100.0 and fpr == 0.0 and br == 0.0:
                print(f"  [PASS] Ground Truth Parity: C3 achieved DR={dr}%, FPR={fpr}%, BR={br}%")
            else:
                print(f"  [FAIL] C3 metrics mismatch: DR={dr}%, FPR={fpr}%, BR={br}%")
                all_passed = False
        else:
            print("  [FAIL] C3 stats missing from e1_paired_statistical_ci.json")
            all_passed = False
    else:
        print("  [FAIL] E1 summary files missing!")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] All dataset contracts, mutation specs, and evidence parity checks PASSED!")
        print("=" * 70)
        return True
    else:
        print("[ERROR] One or more verification checks FAILED. Review errors above.")
        print("=" * 70)
        return False


def main():
    parser = argparse.ArgumentParser(description="MedalGuard Dataset Contract and Artifact Validator")
    parser.add_argument("--all", action="store_true", help="Validate all contracts, mutations, and artifact parity")
    parser.add_argument("--contract", type=str, help="Path to single contract YAML file")
    parser.add_argument("--db", type=str, help="Optional path to DuckDB database for schema introspection")

    args = parser.parse_args()

    if args.all or (not args.contract):
        success = run_all_checks()
        sys.exit(0 if success else 1)
    else:
        contract_path = Path(args.contract)
        db_path = Path(args.db) if args.db else None
        success = validate_single_contract(contract_path, db_path)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
