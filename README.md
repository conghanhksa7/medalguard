# MedalGuard Seminar

> **MedalGuard: Early Data Failure Detection Framework for Medallion Lakehouse via Automated Contract Validation at Layer Boundaries under Schema Evolution**

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate TPC-H data
python scripts/generate_tpch.py

# 4. Run dbt pipeline
cd dbt_project
dbt run
cd ..

# 5. Run baseline and overhead experiments
python scripts/run_baseline.py
python scripts/measure_overhead.py
```

## Project Structure

```
medalguard-seminar/
├── dbt_project/          # dbt models (Bronze -> Silver -> Gold)
├── medalguard/           # MedalGuard Python framework
├── contracts/            # YAML contract definitions
├── mutations/            # Schema Mutation Suite (5 types)
├── experiments/          # Experiment runner
├── metrics/              # Metrics collection & analysis
├── results/              # Experiment outputs
├── data/                 # DuckDB database (gitignored)
├── scripts/              # Utility scripts
├── notebooks/            # Jupyter notebooks
└── docs/                 # Documentation & report
```

## Tech Stack

- **Python** 3.10+
- **DuckDB** — Embedded analytical database (Lakehouse engine)
- **dbt-core + dbt-duckdb** — Data transformation (Bronze -> Silver -> Gold)
- **TPC-H** — Benchmark dataset (SF=1, ~1GB)

## Baseline Results (C0 — No Enforcement)

Measured on TPC-H (SF=0.1, 866,602 rows):

| Metric | C0 Value | Target C3 | Assessment |
|:---|:---:|:---:|:---|
| **Detection Rate (DR)** | **0%** (0/14) | $\ge 95\%$ | Baseline has no validation gates; misses all faults |
| **False Positive Rate (FPR)** | **0%** (0/5) | $\le 5\%$ | No false alarms on benign schema evolution |
| **Fault Outcomes** | | | 6 Silent (42.9%), 5 Neutralised (35.7%), 3 Crash (21.4%) |
| **Blast Radius (Overall)** | **14.8%** | $\le 5\%$ | Measured via row-level diff against clean Gold reference |
| **Blast Radius (Silent)** | **34.6%** | $\le 0\%$ | M5a/M5b corrupts 92.1% of national revenue summary |
| **Detection Depth Index** | $\infty$ | $0$ (Gate 1) | No pre-transform detection; faults reach Gold |
| **dbt Execution Latency** | **1,411 ms** | $< 1,600\text{ ms}$ | Median of 7 clean runs ($\sigma = 109\text{ ms}$) |
| **Wall-clock Pipeline Time**| **6,796 ms** | — | Includes ~79% dbt CLI/Python startup overhead |

## Author

Luong Le Cong Hanh — K23, Data Science, HCMUS
