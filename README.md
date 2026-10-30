# MedalGuard

> **MedalGuard: Early Data Failure Detection Framework for Medallion Lakehouse via Automated Contract Validation at Layer Boundaries under Schema Evolution**

**Author:** Lương Lê Công Hạnh (MSSV: 23280057)  
**Program:** Master of Science in Data Science, University of Science, VNU-HCM (HCMUS)  
**Advisor:** Course Faculty & Research Committee  
**Course:** Data Science Seminar & Master Thesis Preparation (2026)  
**Git Repository:** `D:\Study\Seminar\medalguard-seminar`

---

## 1. Executive Summary & Core Research Contributions

In modern **Medallion Lakehouse architectures** (Bronze raw ingestion $\rightarrow$ Silver cleaned models $\rightarrow$ Gold analytics aggregates), operational sources continuously evolve (schema drift, type changes, constraint violations, and distribution shifts). Traditional validation either fails catastrophically (*All-or-Nothing pipeline crash in dbt contracts*) or detects faults too late (*post-hoc Great Expectations at Gold layer after Silver is contaminated*).

**MedalGuard** introduces an in-process, dual-boundary, contract-driven validation framework with staged in-place quarantine and automated self-healing.

### The Three Core Contributions:
1. **CT1 (Data Engineering Architecture & Design - DE-A/D):** Multi-layer YAML Data Contracts specification language and a 36-scenario Mutation Suite v2 (24 Harmful + 12 Benign) parameterized by `severity` (CRITICAL, HIGH, MEDIUM) and `schema_version`.
2. **CT2 (Data Engineering Algorithm & Boundary Enforcement - DE-A/B):** In-process Dual-Boundary In-line Gate (`Gate 1` at Bronze $\rightarrow$ Silver and `Gate 2` at Silver $\rightarrow$ Gold) with DuckDB pushdown vector validation and In-place Row Quarantine (`quarantine.<table_name>_rejected`).
3. **CT3 (Data Engineering Operations, Lineage & Self-Healing - DE-B/C):** Multi-hop Data Lineage graph, automated Root-Cause Diff classification, sub-second LKG Gold Rollback (**51.9 ms**), Automated Quarantine Repair & Backfill, multi-channel alerting (Email/Webhook), and an interactive Web Console.

---

## 2. Definitive Experimental Evaluation (E1, E2, E3, E4, E5)

All experiments were executed on TPC-H Benchmark across 5 configurations:
- **C0:** Unmonitored Baseline (No checks).
- **C1:** dbt Model Contracts (Compile-time DDL enforcement).
- **C2:** Great Expectations Post-transform Suite (Silver layer).
- **C3_standalone:** MedalGuard Standalone In-line Gate.
- **C3:** MedalGuard Full In-line Dual-Gate Architecture.

### 2.1 E1: Main Comparative Matrix (SF=0.1, 150,000 lineitem rows)

#### Table 1: Core 19 Benchmark (14 Harmful + 5 Benign Scenarios = 95 Runs)
| Configuration | Detection Rate (95% Wilson CI) | FPR (95% Wilson CI) | Mean Blast Radius (95% Bootstrap CI) | $\Delta$BR vs C3 (95% CI) | McNemar *p* (vs C3) | Core Execution (ms) | Ingest Correctness | SLA Attainment |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0 (Baseline)** | **0.0%** [0.0%, 21.5%] | 0.0% [0.0%, 43.5%] | **14.8%** [1.1%, 33.8%] | +14.8% [1.1%, 33.8%] | **$p < 0.001$** | 1,403.2 ms | 52.6% | 26.3% |
| **C1 (dbt Contracts)** | **42.9%** [21.4%, 67.4%] | 0.0% [0.0%, 43.5%] | **13.6%** [0.0%, 32.9%] | +13.6% [0.0%, 32.9%] | **$p = 0.0078$** | 1,754.1 ms | 84.2% | 26.3% |
| **C2 (Great Exp.)** | **35.7%** [16.3%, 61.2%] | 0.0% [0.0%, 43.5%] | **6.6%** [0.0%, 19.7%] | +6.6% [0.0%, 19.7%] | **$p = 0.0039$** | 1,363.2 ms | 79.0% | 26.3% |
| **C3_standalone** | **100.0%** [78.5%, 100.0%] | 0.0% [0.0%, 43.5%] | **0.0%** [0.0%, 0.0%] | +0.0% [0.0%, 0.0%] | $p = 1.0000$ | 1,272.9 ms | **100.0%** | **100.0%** |
| **C3 (MedalGuard)** | **100.0%** [78.5%, 100.0%] | 0.0% [0.0%, 43.5%] | **0.0%** [0.0%, 0.0%] | — *(Ref)* | — | 1,308.8 ms | **100.0%** | **100.0%** |

#### Table 2: Expanded 36 Benchmark (24 Harmful + 12 Benign Scenarios = 180 Runs)
| Configuration | Detection Rate (95% Wilson CI) | FPR (95% Wilson CI) | Mean Blast Radius (95% Bootstrap CI) | $\Delta$BR vs C3 (95% CI) | McNemar *p* (vs C3) | Core Execution (ms) | Ingest Correctness | SLA Attainment |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0 (Baseline)** | **0.0%** [0.0%, 13.8%] | 0.0% [0.0%, 24.2%] | **9.6%** [1.1%, 21.0%] | +9.6% [1.1%, 21.0%] | **$p < 0.001$** | 1,400.8 ms | 66.7% | 33.3% |
| **C1 (dbt Contracts)** | **41.7%** [24.5%, 61.2%] | 0.0% [0.0%, 24.2%] | **7.9%** [0.0%, 19.4%] | +7.9% [0.0%, 19.4%] | **$p < 0.001$** | 1,726.4 ms | 91.7% | 33.3% |
| **C2 (Great Exp.)** | **37.5%** [21.2%, 57.3%] | 0.0% [0.0%, 24.2%] | **3.8%** [0.0%, 11.5%] | +3.8% [0.0%, 11.5%] | **$p < 0.001$** | 1,347.9 ms | 83.3% | 33.3% |
| **C3_standalone** | **100.0%** [86.2%, 100.0%] | 0.0% [0.0%, 24.2%] | **0.0%** [0.0%, 0.0%] | +0.0% [0.0%, 0.0%] | $p = 1.0000$ | 1,312.9 ms | **100.0%** | **100.0%** |
| **C3 (MedalGuard)** | **100.0%** [86.2%, 100.0%] | 0.0% [0.0%, 24.2%] | **0.0%** [0.0%, 0.0%] | — *(Ref)* | — | 1,357.3 ms | **100.0%** | **100.0%** |

---

### 2.2 E2: Dual-Axis Ablation Study (24 Harmful Scenarios)

#### Table 3: Axis 1 - Validator Modules Ablation
| Ablation Configuration | Active Validators | Detection Rate (%) | Missed Count | Failure Modes Observed | Blast Radius | Validation (ms) |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: |
| **C3_standalone (Full)** | Schema + Constraint + Semantic | **100.0% (24/24)** | **0** | `None (100% Interception)` | **0.0%** | 234.2 ms |
| **A1_NO_SCHEMA** | Constraint + Semantic | **41.7% (10/24)** | 14 | Misses all structural DDL & type drift faults (M1, M2, M3) | **0.0%** | 289.9 ms |
| **A2_NO_CONSTRAINT** | Schema + Semantic | **66.7% (16/24)** | 8 | Misses row-level nulls, range breaches, and duplicate keys (M4) | **1.9%** | 108.0 ms |
| **A3_NO_SEMANTIC** | Schema + Constraint | **95.8% (23/24)** | 1 | Misses intra-domain distribution drift (`M5b_MULTIPLY_1_5`) | **3.8%** | 235.3 ms |
| **A4_SCHEMA_ONLY** | Schema Only | **58.3% (14/24)** | 10 | Misses all M4 constraints & M5 semantic drifts | **9.6%** | 106.9 ms |
| **A5_CONSTRAINT_ONLY**| Constraint Only | **37.5% (9/24)** | 15 | Misses all M1, M2, M3 structural changes | **3.8%** | 280.1 ms |
| **A6_SEMANTIC_ONLY** | Semantic Only | **8.3% (2/24)** | 22 | Misses almost all schema & constraint corruptions | **1.9%** | 149.5 ms |

#### Table 4: Axis 2 - Architectural Boundary Placement Ablation
| Boundary Configuration | Enforcement Location | Detection Rate (%) | Mean Blast Radius | Mean Detection Depth (DDI) | Residual Gold Leakage | Mean Wall Clock (ms) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **B1_GATE1_ONLY** | Gate 1 Only (Bronze $\rightarrow$ Silver) | **100.0% (24/24)** | **0.0%** | **DDI = 0.0** | **1.7%** | 3,763.9 ms |
| **B2_GATE2_ONLY** | Gate 2 Only (Silver $\rightarrow$ Gold) | **12.5% (3/24)** | **9.6%** | **DDI = 2.0** *(Crashes in Silver)* | **7.9%** | 9,586.6 ms |
| **C3_DUAL_GATE** | **Dual Gate (Gate 1 + Gate 2)** | **100.0% (24/24)** | **0.0%** | **DDI = 0.0** | **1.7%** | 3,810.7 ms |

---

### 2.3 E3: Pipeline Overhead & Scale Benchmark

#### Table 5: Overhead Decomposition across Scales (SF=0.1 vs SF=1.0)
| Configuration | SF=0.1 Median Wall (ms) | SF=0.1 Overhead vs C0 | SF=1.0 Median Wall (ms) | SF=1.0 Overhead vs C0 | SF=1.0 Gate Val Time | SF=1.0 Throughput (rows/sec) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0 (Baseline)** | 14,885.1 ms | 0.0% (Ref) | 18,826.7 ms | 0.0% (Ref) | 0.0 ms | 7,967 |
| **C1 (dbt Contracts)**| 14,951.5 ms | +0.5% | 19,831.4 ms | +5.3% | 0.0 ms | 7,564 |
| **C2 (Great Exp.)** | 14,963.3 ms | +0.5% | 19,306.3 ms | +2.5% | 134.0 ms | 7,769 |
| **C3 (MedalGuard)** | 15,269.4 ms | **+2.6%** | 20,434.0 ms | **+8.5%** | **506.1 ms** *(9.4% dbt time)* | 7,341 |

#### Table 6: Stress Test on 6 Representative Mutations at SF=1.0 (1.5 Million Records)
| Mutation Scenario | Category | Severity | Pipeline Status | Detected? | DDI | Quarantined Rows | QE (%) | Blast Radius % | Wall Time (ms) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `M1a_AddSingleCol` | ADDITIVE | MEDIUM | `BLOCKED` | **True** | DDI=0 | 0 | N/A | **0.0%** | 7,581.7 |
| `M2a_DropNonKey` | DESTRUCTIVE | CRITICAL | `BLOCKED` | **True** | DDI=0 | 0 | N/A | **0.0%** | 7,778.7 |
| `M3a_DoubleToVarchar` | TYPE_CHANGE | HIGH | `BLOCKED` | **True** | DDI=0 | 0 | N/A | **0.0%** | 7,974.0 |
| `M4a_NullAndNegative` | CONSTRAINT | HIGH | `SUCCESS` | **True** | DDI=0 | **300** | **100%** | **0.0%** | 21,912.4 |
| `M5a_MULTIPLY_100` | SEMANTIC | CRITICAL | `BLOCKED` | **True** | DDI=0 | 0 | N/A | **0.0%** | 7,943.4 |
| `B1_AddColumn` | BENIGN | BENIGN | `SUCCESS` | **False** | DDI=-1 | 0 | N/A | **0.0%** | 21,573.5 |

---

## 3. Publication-Grade Visual Figures (300 DPI)

The 6 academic figures are generated directly from experimental data via `python scripts/visualize_phase2.py`:

| Figure & Caption | File Artifact |
| :--- | :--- |
| **Figure 1:** Detection Rate, Ingest Correctness, SLA Attainment & FPR across Core 19 and Expanded 36 with 95% Wilson CI | [`results/charts/fig1_detection_and_fpr_comparison.png`](results/charts/fig1_detection_and_fpr_comparison.png) |
| **Figure 2:** Blast Radius & Failure Outcome Heatmap across 24 Harmful Scenarios × 5 Configurations | [`results/charts/fig2_blast_radius_heatmap.png`](results/charts/fig2_blast_radius_heatmap.png) |
| **Figure 3:** Failure Interception Depth Distribution (DDI) & Architectural Boundary Placement Ablation | [`results/charts/fig3_detection_depth_and_boundary_ablation.png`](results/charts/fig3_detection_depth_and_boundary_ablation.png) |
| **Figure 4:** Validator Module Ablation Study across Mutation Taxonomies (M1 to M5) | [`results/charts/fig4_validator_ablation_study.png`](results/charts/fig4_validator_ablation_study.png) |
| **Figure 5:** Execution Time Decomposition (dbt DAG vs Validation Gate) & Empirical Scaling Curve $T(SF)$ | [`results/charts/fig5_overhead_and_scale_stress_test.png`](results/charts/fig5_overhead_and_scale_stress_test.png) |
| **Figure 6:** CT3 Task-Based Pilot Verification: MTTD vs MTTR Latency and Blast Radius Recovery Before/After | [`results/charts/fig6_ct3_pilot_mttd_mttr_recovery.png`](results/charts/fig6_ct3_pilot_mttd_mttr_recovery.png) |

---

## 4. CT3 Pilot Use Cases & Quarantine Console

MedalGuard includes a comprehensive self-healing operations suite verified on 3 real-world incidents:
- **UC1 (Unregistered Schema Evolution):** Upstream service adds `l_promo_code` without updating contract. Gate 1 intercepts at DDI=0 in **101.1 ms**. Data Engineer reviews and approves schema evolution via Console; contract updates v1 $\rightarrow$ v2; pipeline resumes with **0% data loss**.
- **UC2 (Row-level Corruption & Replay):** Ingestion receives 35 corrupted records (null foreign keys, negative price, duplicate order keys). Gate 1 isolates 35 records to quarantine. Bronze/Silver pipeline proceeds cleanly with **0.0% Blast Radius**. Automated Replay Engine repairs 30 records, deduplicates 5 keys, and backfills in **8.3s** to reach **100.0% Completeness**.
- **UC3 (Catastrophic Business Drift & Instant Rollback):** Upstream logic error multiplies discount by 100. Gate 1 detects global drift in **115.8 ms**. Circuit Breaker trips and executes sub-second LKG Gold Rollback in **51.9 ms**, maintaining **100% Gold Availability** and **0.0% Blast Radius**.
- **Interactive UI Console:** Access [`results/console/quarantine_replay_console.html`](results/console/quarantine_replay_console.html) to inspect quarantined records, lineage graph, audit trails, and 1-click replay actions.

---

## 5. Quickstart & 1-Click Reproduction Guide

```powershell
# 1. Navigate to project root
cd D:\Study\Seminar\medalguard-seminar

# 2. Run all Phase 2 experiments (E1 Comparative Matrix + E2 Ablation + E3 Benchmark)
python scripts/run_phase2_experiments.py --all

# 3. Generate all 6 publication-grade figures (300 DPI)
python scripts/visualize_phase2.py

# 4. Launch CT3 Pilot Verification & Console Generator
python -m medalguard.console
```
