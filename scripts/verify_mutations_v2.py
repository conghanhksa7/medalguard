"""Verification script for MedalGuard Mutation Suite v2 (36 scenarios).

Verifies:
1. get_mutation_suite(sf=0.1, suite="core") returns exactly 19 scenarios (14 harmful + 5 benign).
2. get_mutation_suite(sf=0.1, suite="expanded") returns exactly 36 scenarios (24 harmful + 12 benign).
3. Prints complete 36-mutation catalog.
4. Executes Gate 1 test on all 17 expanded mutations:
   - 10 Harmful: all detected (7 BLOCKED, 3 QUARANTINED).
   - 7 Benign: all pass (detected = False, FPR = 0%).
5. Outputs results to results/summary/mutation_suite_v2_catalog.json and .md.
"""
import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from medalguard.gate import ContractGate, ContractViolationError
from experiments.runner import reset_database, run_dbt, DB_PATH, CONTRACTS_DIR, swap_dbt_config
from mutations import get_mutation_suite


def main():
    sf = 0.1
    print("=" * 100)
    print("  MEDALGUARD MUTATION SUITE V2 VERIFICATION")
    print("=" * 100)

    # 1. Verify suite counts
    core_mutations = get_mutation_suite(sf=sf, suite="core")
    exp_mutations = get_mutation_suite(sf=sf, suite="expanded")

    core_faults = [m for m in core_mutations if m.category != "BENIGN"]
    core_benigns = [m for m in core_mutations if m.category == "BENIGN"]
    exp_faults = [m for m in exp_mutations if m.category != "BENIGN"]
    exp_benigns = [m for m in exp_mutations if m.category == "BENIGN"]

    n_core_f, n_core_b = len(core_faults), len(core_benigns)
    n_exp_f, n_exp_b = len(exp_faults), len(exp_benigns)

    print(f"\n[1] SUITE COUNT VERIFICATION:")
    print(f"  • Core Suite:     {n_core_f} Harmful + {n_core_b} Benign = {len(core_mutations)} scenarios")
    print(f"  • Expanded Suite: {n_exp_f} Harmful + {n_exp_b} Benign = {len(exp_mutations)} scenarios")

    assert len(core_mutations) == 19, f"Core suite count mismatch: expected 19, got {len(core_mutations)}"
    assert len(exp_mutations) == 36, f"Expanded suite count mismatch: expected 36, got {len(exp_mutations)}"
    assert (n_core_f, n_core_b) == (14, 5), f"Core suite mismatch: expected (14, 5), got ({n_core_f}, {n_core_b})"
    assert (n_exp_f, n_exp_b) == (24, 12), f"Expanded suite mismatch: expected (24, 12), got ({n_exp_f}, {n_exp_b})"
    print("  --> OK: Suite counts match specifications 100%!")

    # 2. Build 36-scenario Catalog
    all_36 = exp_mutations
    catalog = []
    print("\n[2] COMPLETE 36-SCENARIO CATALOG:")
    print(f"{'Idx':<4} {'Name':<28} {'Suite':<7} {'Category':<18} {'Target Table':<13} {'Severity':<9} {'Schema Ver':<22} {'Faults':<8}")
    print("-" * 120)

    for idx, m in enumerate(all_36, 1):
        suite_type = "Core" if m.is_core else "Expanded"
        cat_info = {
            "index": idx,
            "name": m.name,
            "suite": suite_type,
            "is_core": m.is_core,
            "category": m.category,
            "target_table": m.target_table,
            "severity": m.severity,
            "schema_version": m.schema_version,
            "injected_fault_count": m.injected_fault_count,
            "description": m.description,
        }
        catalog.append(cat_info)
        print(f"{idx:<4} {m.name:<28} {suite_type:<7} {m.category:<18} {m.target_table:<13} {m.severity:<9} {m.schema_version:<22} {m.injected_fault_count:<8}")
    print("-" * 120)

    # 3. Test Gate 1 on 17 New Expanded Mutations
    expanded_17 = [m for m in all_36 if not m.is_core]
    print(f"\n[3] TESTING GATE 1 ON {len(expanded_17)} NEW EXPANDED MUTATIONS...")
    print(f"{'Name':<28} {'Type':<7} {'Status':<9} {'Det':<6} {'DDI':<5} {'Stage':<15} {'Q_Rows':<7} {'Violations':<11} {'Result'}")
    print("-" * 105)

    contracts = [
        ("orders", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "orders.yaml"), "bronze.bronze_orders"),
        ("lineitem", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "lineitem.yaml"), "bronze.bronze_lineitem"),
        ("customer", os.path.join(CONTRACTS_DIR, "bronze_to_silver", "customer.yaml"), "bronze.bronze_customer"),
    ]

    test_results = []
    swap_dbt_config(False)

    for m in expanded_17:
        is_benign = (m.category == "BENIGN")
        reset_database(DB_PATH, sf)
        con = duckdb.connect(DB_PATH)
        m.apply(con)
        con.close()

        # Run bronze ingestion
        st_b, _, _, _ = run_dbt("tag:bronze")

        g1_blocked = False
        detected = False
        quarantined_total = 0
        violations_total = 0
        stage = "NOT_DETECTED"
        ddi = -1

        for name, cpath, tbl in contracts:
            gate = ContractGate(
                gate_name=f"B->S:{name}",
                contract_path=cpath,
                db_path=DB_PATH,
                mode="quarantine",
                enabled_validators={"schema", "constraint", "semantic"},
                save_reports=False
            )
            try:
                res = gate.validate_pre_transform(tbl, injected_fault_count=m.injected_fault_count)
                violations_total += len(res.violations)
                quarantined_total += res.quarantined_rows
                if not res.passed and not detected:
                    detected = True
                    stage = "PRE_TRANSFORM"
                    ddi = 0
            except ContractViolationError as e:
                g1_blocked = True
                detected = True
                stage = "PRE_TRANSFORM"
                ddi = 0
                violations_total += len(e.violations)
                break

        status = "BLOCKED" if g1_blocked else "SUCCESS"

        # Revert mutation
        con = duckdb.connect(DB_PATH)
        m.revert(con)
        con.close()

        # Check correctness
        if is_benign:
            is_valid = (not detected)
            res_tag = "PASS (Zero FP)" if is_valid else "FAIL (False Positive)"
        else:
            is_valid = detected
            if status == "BLOCKED":
                res_tag = "PASS (Blocked)"
            elif quarantined_total > 0:
                res_tag = "PASS (Quarantined)"
            else:
                res_tag = "PASS (Detected)" if is_valid else "FAIL (Undetected)"

        m_type = "Benign" if is_benign else "Harmful"
        print(f"{m.name:<28} {m_type:<7} {status:<9} {detected!s:<6} {ddi:<5} {stage:<15} {quarantined_total:<7} {violations_total:<11} {res_tag}")

        test_results.append({
            "name": m.name,
            "category": m.category,
            "is_benign": is_benign,
            "status": status,
            "detected": detected,
            "ddi": ddi,
            "detection_stage": stage,
            "quarantined_rows": quarantined_total,
            "violations_count": violations_total,
            "verification_status": "PASS" if is_valid else "FAIL"
        })

    print("-" * 105)

    # Summary
    harmful_detected = sum(1 for r in test_results if not r["is_benign"] and r["detected"])
    harmful_total = sum(1 for r in test_results if not r["is_benign"])
    benign_passed = sum(1 for r in test_results if r["is_benign"] and not r["detected"])
    benign_total = sum(1 for r in test_results if r["is_benign"])

    print(f"\n[4] VERIFICATION RESULTS SUMMARY:")
    print(f"  • Harmful Mutations Detected: {harmful_detected}/{harmful_total} ({harmful_detected/harmful_total*100:.1f}%)")
    print(f"  • Benign False Positive Rate: {benign_total - benign_passed}/{benign_total} (FPR = {(benign_total - benign_passed)/benign_total*100:.1f}%)")

    assert harmful_detected == harmful_total, f"Not all harmful mutations detected: {harmful_detected}/{harmful_total}"
    assert benign_passed == benign_total, f"Some benign mutations triggered false positives: {benign_passed}/{benign_total}"

    # Specific assertion checks requested by GVHD:
    # 7 Blocked harmful: M1c, M1d, M2d, M2e, M3d, M3e, M5d
    for blocked_name in ["M1c_AddCustomerPiiCol", "M1d_AddOrdersShadowCol", "M2d_DropCustomerNationKey",
                         "M2e_RenameOrdersPriority", "M3d_CustomerAcctbalToVarchar",
                         "M3e_OrdersCustkeyToVarchar", "M5d_LineitemTaxSpike"]:
        r = next(item for item in test_results if item["name"] == blocked_name)
        assert r["status"] == "BLOCKED" and r["detected"] is True, f"{blocked_name} should be BLOCKED at Gate 1"

    # 3 Quarantined harmful: M4d (25 rows), M4e (10 rows), M5e (15 rows)
    r_m4d = next(item for item in test_results if item["name"] == "M4d_LineitemNegativeQty")
    assert r_m4d["quarantined_rows"] == 25 and r_m4d["status"] == "SUCCESS", f"M4d quarantined rows expected 25, got {r_m4d['quarantined_rows']}"

    r_m4e = next(item for item in test_results if item["name"] == "M4e_CustomerDuplicateKeys")
    assert r_m4e["quarantined_rows"] == 10 and r_m4e["status"] == "SUCCESS", f"M4e quarantined rows expected 10, got {r_m4e['quarantined_rows']}"

    r_m5e = next(item for item in test_results if item["name"] == "M5e_ShipmodeInvalidCode")
    assert r_m5e["quarantined_rows"] == 15 and r_m5e["status"] == "SUCCESS", f"M5e quarantined rows expected 15, got {r_m5e['quarantined_rows']}"

    # 7 Benign: all detected == False
    for b_item in test_results:
        if b_item["is_benign"]:
            assert b_item["detected"] is False and b_item["violations_count"] == 0, f"Benign {b_item['name']} triggered violation"

    print("  --> ALL 17 EXPANDED SCENARIOS PASSED VERIFICATION 100%!")

    # 5. Save Catalog and Verification Outputs
    summary_dir = Path(PROJECT_ROOT) / "results" / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    json_path = summary_dir / "mutation_suite_v2_catalog.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_scenarios": len(catalog),
            "core_scenarios": len(core_mutations),
            "expanded_scenarios": len(exp_mutations),
            "harmful_count": n_exp_f,
            "benign_count": n_exp_b,
            "catalog": catalog,
            "verification_test_expanded_17": test_results
        }, f, indent=2)
    print(f"\nSaved JSON catalog & verification to: {json_path}")

    md_path = summary_dir / "mutation_suite_v2_catalog.md"
    md_lines = [
        "# MedalGuard Mutation Suite v2 Catalog (36 Scenarios)\n",
        f"**Tổng số:** 36 kịch bản (24 Harmful Faults + 12 Benign Schema Evolution).\n",
        "## 1. Bảng Danh Mục Toàn Bộ 36 Kịch Bản\n",
        "| STT | Tên Kịch Bản | Nhóm Suite | Danh Mục | Bảng Đích | Mức Độ (Severity) | Phiên Bản Schema | Số Bản Ghi Lỗi |",
        "|:---:|:---|:---:|:---|:---:|:---:|:---:|:---:|",
    ]
    for c in catalog:
        md_lines.append(
            f"| {c['index']} | `{c['name']}` | **{c['suite']}** | `{c['category']}` | "
            f"`{c['target_table']}` | `{c['severity']}` | `{c['schema_version']}` | {c['injected_fault_count']:,} |"
        )

    md_lines.extend([
        "\n## 2. Kết Quả Kiểm Chứng Gate 1 Trên 17 Kịch Bản Mở Rộng Mới\n",
        "| Kịch Bản | Loại | Trạng Thái Gate 1 | Phát Hiện | DDI | Tầng Phát Hiện | Số Dòng Cách Ly | Vi Phạm | Kết Quả |",
        "|:---|:---:|:---:|:---:|:---:|:---|:---:|:---:|:---:|",
    ])
    for r in test_results:
        m_t = "Benign" if r["is_benign"] else "Harmful"
        md_lines.append(
            f"| `{r['name']}` | {m_t} | `{r['status']}` | **{r['detected']}** | "
            f"{r['ddi']} | `{r['detection_stage']}` | {r['quarantined_rows']} | {r['violations_count']} | **{r['verification_status']}** |"
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
    print(f"Saved Markdown catalog to: {md_path}")


if __name__ == "__main__":
    main()
