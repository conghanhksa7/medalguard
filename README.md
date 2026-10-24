# MedalGuard

> **MedalGuard: Early Data Failure Detection Framework for Medallion Lakehouse via Automated Contract Validation at Layer Boundaries under Schema Evolution**

**Author:** Lương Lê Công Hạnh (MSSV: 23280057)  
**Program:** K23 Data Science, University of Science, VNU-HCM (HCMUS)  
**Course:** Data Science Seminar (Fall 2026)

---

## Overview

In Medallion Lakehouse architectures (Bronze → Silver → Gold), data faults originating at the ingestion layer (schema drift, constraint breaches, semantic shifts) frequently propagate silently to business analytics tables (Gold layer). **MedalGuard** is a contract-driven data failure detection and staged quarantine framework designed to intercept and isolate data corruptions at layer boundaries before they impact downstream decisions.

---

## Milestone 2: Baseline C0 Experimental Results

Baseline C0 represents an unmonitored Lakehouse pipeline (Bronze → Silver → Gold without contract enforcement). Experiments were executed on TPC-H Benchmark (SF=0.1, 866,602 rows) across **14 fault mutations** (M1a–M5c) and **5 benign mutations** (B1, B2, B3, B5, B7).

### 1. Summary Metrics

| Metric | Baseline C0 Value | Target C3 (MedalGuard) | Research Assessment |
|:---|:---:|:---:|:---|
| **Detection Rate (DR)** | **0%** (0/14) | $\ge 95\%$ | Baseline has no validation gates; misses all faults |
| **False Positive Rate (FPR)** | **0%** (0/5) | $\le 5\%$ | No false alarms on benign business schema changes |
| **Fault Outcomes** | — | — | 6 Silent Propagation (42.9%), 5 Neutralised (35.7%), 3 Accidental Crash (21.4%) |
| **Blast Radius (Overall)** | **14.8%** | $\le 5\%$ | Row-level deviation measured via `FULL OUTER JOIN` against clean Gold reference |
| **Blast Radius (Silent)** | **34.6%** | $\le 0\%$ | M5a/M5b corrupts 92.1% of national revenue summary |
| **Detection Depth Index** | $\infty$ | $0$ (Gate 1) | No pre-transform detection; faults reach Gold dashboard |
| **dbt Execution Latency** | **1,411 ms** | $< 1,600\text{ ms}$ | Median of 7 clean runs ($\sigma = 109\text{ ms}$) |
| **Wall-clock Pipeline Time**| **6,796 ms** | — | Includes ~79% dbt CLI/Python startup overhead |

### 2. Visual Evidence & Analysis

| Blast Radius per Mutation | Fault Outcome by Category |
|:---:|:---:|
| ![Blast Radius](results/baseline/blast_radius_by_mutation.png) | ![Outcome by Category](results/baseline/outcome_by_category.png) |

| Pipeline Latency Overhead (7 Runs on Clean Data) |
|:---:|
| ![Pipeline Overhead](results/baseline/pipeline_overhead.png) |

---

## Milestone 3: Staged Validation & Smoke Test Verification (C1, C2, C3)

To validate the multi-configuration experiment architecture prior to the full 95-run matrix execution, a 12-scenario Smoke Test was executed on TPC-H Benchmark ($SF=0.1$) across 4 representative mutations (`M2a_DropNonKey`, `M4a_NullAndNegative`, `M5a_MULTIPLY_100`, `B1_AddColumn`) across 3 configurations:
- **C1 (dbt contracts only):** Compile-time schema and basic constraint enforcement.
- **C2 (Great Expectations only):** Post-transformation 10-rule suite on Silver tables.
- **C3_standalone (MedalGuard only):** Pre-transformation Gate 1 with in-place quarantine at Bronze ingestion + Gate 2 post-transform.

### Smoke Test Empirical Results

| Config | Mutation | Pipeline Status | Detected | DDI | Detection Stage | Quarantined Rows | QE (%) | Blast Radius | Wall-clock (ms) | dbt (ms) | Validation (ms) |
|:---|:---|:---:|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **C1** | `M2a_DropNonKey` | `BLOCKED` | **True** | 1 | `SILVER_CONTRACT` | 0 | N/A | **0.0%** | 13,031 | 2,102 | 0 |
| **C1** | `M4a_NullAndNegative` | `BLOCKED` | **True** | 1 | `SILVER_CONTRACT` | 0 | N/A | **0.0%** | 10,812 | 1,684 | 0 |
| **C1** | `M5a_MULTIPLY_100` | **`SUCCESS`** | **`False`** | -1 | `NOT_DETECTED` | 0 | N/A | **`92.1%`** | 11,575 | 1,980 | 0 |
| **C1** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 11,827 | 1,934 | 0 |
| **C2** | `M2a_DropNonKey` | **`CRASH`** | **`False`** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 12,619 | 1,347 | 0 |
| **C2** | `M4a_NullAndNegative` | `BLOCKED` | **True** | 2 | `POST_TRANSFORM` | 0 | N/A | **0.0%** | 11,249 | 1,714 | 55 |
| **C2** | `M5a_MULTIPLY_100` | `BLOCKED` | **True** | 2 | `POST_TRANSFORM` | 0 | N/A | **0.0%** | 15,746 | 2,219 | 54 |
| **C2** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 16,931 | 2,077 | 31 |
| **C3_standalone** | `M2a_DropNonKey` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 5,218 | 686 | 105 |
| **C3_standalone** | `M4a_NullAndNegative` | **`SUCCESS`** | **`True`** | 0 | `PRE_TRANSFORM` | **30** | **`100%`** | **`0.0%`** | 13,555 | 2,091 | 204 |
| **C3_standalone** | `M5a_MULTIPLY_100` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 5,130 | 718 | 125 |
| **C3_standalone** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 13,319 | 2,341 | 290 |

### Key Theoretical & Empirical Insights

1. **Star Result (dbt contracts blind spot):** Configuration C1 misses semantic value drift (`M5a_MULTIPLY_100`) because structural contracts cannot evaluate distribution properties, leading to a catastrophic **92.1% Blast Radius** on downstream Gold aggregates.
2. **Post-Transform Bottleneck (Great Expectations limitation):** Configuration C2 only inspects data after model transformation. Structural breaks (`M2a_DropNonKey`) crash the dbt execution engine before GX expectations can ever execute (`CRASH, det=False`).
3. **MedalGuard In-Place Quarantine & Early Interception (C3_standalone):**
   - Intercepts faults at **`DDI=0` (PRE_TRANSFORM)** before computation resources are spent on dbt transformations, reducing pipeline execution latency by ~60% on blocked mutations (~5.1s vs ~12–15s).
   - For row-level breaches (`M4a_NullAndNegative`), MedalGuard isolates exactly 30 bad rows into quarantine at Bronze layer, allowing 149,970 clean rows to flow through to Gold with **Quarantine Effectiveness = 100%** and **Blast Radius = 0.0%**.
   - **Zero False Positives:** Benign additive changes (`B1_AddColumn`) pass cleanly (`det=False`) without disruption.

---

## Project Structure

```
medalguard-seminar/
├── dbt_project/          # dbt models (Bronze -> Silver -> Gold)
│   ├── macros/           # Schema name resolution macro
│   ├── models/           # bronze/, silver/, gold/ SQL models & contracts
│   └── profiles.yml      # Local DuckDB connection profile
├── medalguard/           # MedalGuard framework core
│   ├── gate.py           # ContractGate orchestrator & staged in-place quarantine
│   ├── reporter.py       # Metrics & Blast Radius calculator
│   ├── gx_runner.py      # Great Expectations 10-rule suite runner for C2
│   ├── validators/       # Schema, Constraint, and Semantic validators
│   └── utils.py          # Secure SQL identifier quote utility
├── contracts/            # YAML data contract definitions
│   ├── bronze_to_silver/ # Gate 1 contracts (orders, lineitem, customer)
│   └── silver_to_gold/   # Gate 2 contracts (revenue_by_nation, priority)
├── mutations/            # 14 fault mutations + 5 benign mutations
├── experiments/          # Multi-configuration experiment suite
│   ├── runner.py         # Staged pipeline runner (--mode smoke / matrix)
│   └── config.yaml       # Configuration & ablation study definitions
├── results/              # Experimental results & evidence
│   ├── baseline/         # Milestone 2 baseline logs & PNG charts
│   └── raw/              # Raw experiment JSON results & gate reports
├── scripts/              # Reproduction & measurement scripts
│   ├── generate_tpch.py  # Clean TPC-H data generator
│   ├── run_baseline.py   # Baseline C0 matrix runner
│   ├── measure_overhead.py # Clean pipeline latency benchmark
│   └── visualize_baseline.py # Chart generation script
└── requirements.txt      # Python dependencies
```

---

## Quick Start & Reproducibility

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/conghanhksa7/medalguard.git
cd medalguard

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate Benchmark Data & Verify Pipeline
```bash
# Generate clean TPC-H SF=0.1 data (~100MB into DuckDB)
python scripts/generate_tpch.py 0.1

# Run dbt transformations (Bronze -> Silver -> Gold)
cd dbt_project
dbt run --profiles-dir . --project-dir .

# Run dbt data tests (Verifies 5/5 tests PASS)
dbt test --profiles-dir . --project-dir .
cd ..
```

### 3. Run Multi-Configuration Smoke Test (Milestone 3)
```bash
# Run 12-scenario smoke test across C1, C2, and C3_standalone
python experiments/runner.py --mode smoke --sf 0.1
```
Results and gate reports are automatically recorded to `results/raw/` and `results/raw/gate_reports/`.

### 4. Run Milestone 2 Baseline Experiments (C0)
```bash
# Run all 19 baseline C0 experiments (14 faults + 5 benign)
python scripts/run_baseline.py

# Measure clean pipeline latency (7 repetitions)
python scripts/measure_overhead.py

# Generate visualization charts & summary JSON
python scripts/visualize_baseline.py
```
All Milestone 2 baseline results and figures are located in `results/baseline/`.
