# IMPLEMENTATION PLAN — MedalGuard Seminar

> **Đề tài:** MedalGuard: Early Data Failure Detection Framework for Medallion Lakehouse via Automated Contract Validation at Layer Boundaries under Schema Evolution
>
> **Sinh viên:** Lương Lê Công Hạnh (K23, Khoa học Dữ liệu, HCMUS)
>
> **Thời gian:** 15 tuần (~14/09/2026 – 28/12/2026)

---

## RESEARCH QUESTIONS

> **RQ1:** Mỗi tầng enforcement (structural / value-level / semantic) phát hiện được loại schema mutation nào, và bỏ sót loại nào?
> - *Metrics:* Detection Rate + Detection Stage, phân tích theo mutation type x config

> **RQ2:** Multi-tier enforcement (MedalGuard) cải thiện Detection Rate và giảm Blast Radius bao nhiêu % so với single-tier (chỉ dbt hoặc chỉ GX)?
> - *Metrics:* So sánh Detection Rate và Blast Radius giữa C3 vs C1 vs C2

> **RQ3:** Chi phí (overhead) của multi-tier enforcement có chấp nhận được cho production pipeline không?
> - *Metrics:* Pipeline Overhead (% thời gian tăng thêm)

---

## PHẦN 1: KIẾN TRÚC HỆ THỐNG

### 1.1 Data Flow tổng quan

```
┌─────────────────────────────────────────────────────────────────┐
│                        DuckDB Engine                            │
│                                                                 │
│  ┌──────────────┐                                               │
│  │  source       │  TPC-H gốc (dbgen SF=1)                     │
│  │  schema       │  8 bảng: orders, lineitem, customer, ...     │
│  └──────┬───────┘                                               │
│         │                                                       │
│         │  mutation_injector.py (inject 1 trong 5 loại lỗi)     │
│         v                                                       │
│  ┌──────────────┐                                               │
│  │  bronze       │  Raw ingested data (có thể đã bị mutation)   │
│  │  schema       │  Materialized bằng dbt (SELECT * FROM src)   │
│  └──────┬───────┘                                               │
│         │                                                       │
│    ┌────▼────┐                                                  │
│    │MedalGuard│  GATE 1: Schema drift + Type check + Null check │
│    │ B -> S  │  So sánh bronze vs silver contract YAML          │
│    └────┬────┘                                                  │
│         │ PASS / BLOCK (ghi log violations)                     │
│         v                                                       │
│  ┌──────────────┐                                               │
│  │  silver       │  Cleaned, typed, constrained                 │
│  │  schema       │  dbt models + (optional) dbt contracts       │
│  └──────┬───────┘                                               │
│         │                                                       │
│    ┌────▼────┐                                                  │
│    │MedalGuard│  GATE 2: Business rules + Semantic checks       │
│    │ S -> G  │  Value ranges, distributions, cross-table logic  │
│    └────┬────┘                                                  │
│         │ PASS / BLOCK (ghi log violations)                     │
│         v                                                       │
│  ┌──────────────┐                                               │
│  │  gold         │  Business aggregates (revenue, priority...)  │
│  │  schema       │  dbt models                                  │
│  └──────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         v
   ┌─────────────┐
   │ Metrics      │  Detection Rate, Blast Radius,
   │ Collector    │  Detection Stage, Pipeline Overhead
   └─────────────┘
```

### 1.2 Tại sao kiến trúc này?

| Quyết định | Lý do |
|:---|:---|
| **PostgreSQL làm source DB** | Khớp với form đã nộp GV, demo kỹ năng làm việc với DB thật, phù hợp career goal |
| **DuckDB làm Lakehouse engine** | Nhẹ (~30MB), không cần Docker, chạy trên laptop, hỗ trợ dbt contracts đầy đủ |
| **Dùng DuckDB schemas để tách layers** | `bronze`, `silver`, `gold` schemas — đơn giản, dbt-duckdb tương thích tốt nhất |
| **Silver model KHÔNG filter data** | Chỉ transform (cast, rename). Enforcement do dbt contracts / GX / MedalGuard đảm nhiệm |
| **MedalGuard là Python module riêng** | Tách biệt khỏi dbt, có thể test độc lập, có mode "log_only" và "block" |

### 1.3 4 Cấu hình thực nghiệm (Configs)

| Config | Tên | MedalGuard | dbt contracts | Great Expectations | Mô tả |
|:---:|:---|:---:|:---:|:---:|:---|
| **C0** | Baseline (No check) | OFF | OFF | OFF | Pipeline chạy không kiểm tra gì |
| **C1** | dbt contracts only | OFF | ON | OFF | Chỉ dbt enforce schema + constraints |
| **C2** | Great Expectations only | OFF | OFF | ON | Chỉ GX validate rules sau khi data đã ghi |
| **C3** | MedalGuard (Multi-tier) | ON | ON | ON | dbt contracts + GX + schema drift detection tại mỗi gate |

### 1.4 Cơ chế chuyển đổi Configs

Dùng **2 bộ YAML files** cho dbt Silver models:

```
dbt_project/models/silver/
├── _silver_models_no_contract.yml    # Dùng cho C0, C2 (không enforce)
└── _silver_models_with_contract.yml  # Dùng cho C1, C3 (enforce)
```

Experiment runner swap file trước mỗi lần chạy:

```python
def setup_config(config_name: str):
    src_dir = "dbt_project/models/silver/"
    target = src_dir + "_silver_models.yml"
    if config_name in ["C0", "C2"]:
        shutil.copy(src_dir + "_silver_models_no_contract.yml", target)
    else:  # C1, C3
        shutil.copy(src_dir + "_silver_models_with_contract.yml", target)
```

### 1.5 MedalGuard Modes: "log_only" / "block" / "quarantine"

| Mode | Hành vi | Khi nào dùng |
|:---|:---|:---|
| `log_only` | Ghi violations nhưng pipeline vẫn chạy tiếp | Đo Blast Radius (cần data ở Gold) |
| `block` | Dừng pipeline khi có violations | Đo Overhead, demo production behavior |
| `quarantine` | Tách data lỗi ra bảng riêng, cho phần tốt đi tiếp | **Chế độ chính** — đo Recovery Success |

```
Quarantine flow:
  Mutation → Bronze → MedalGuard Gate 1:
    ├── Records tốt → Silver → Gold (pipeline tiếp tục)
    └── Records lỗi → quarantine.silver_orders_rejected (cách ly)
```

**Quy ước Blast Radius** (theo GV: đo bằng record bị nhiễm TRƯỚC khi chặn):

| Trường hợp | Blast Radius |
|:---|:---:|
| Pipeline bị chặn hoặc quarantine | **0%** (lỗi không đến Gold) |
| Pipeline chạy xong, lỗi lan đến Gold | **> 0%** (đo % records lỗi thực tế) |
| Pipeline chạy xong, không ai phát hiện | **100%** |

### 1.6 Contract Versioning (theo gợi ý GV)

Contracts hỗ trợ `strict_columns` flag để phân biệt schema evolution hợp lệ vs schema drift:

```yaml
# contracts/bronze_to_silver/orders.yaml
version: 2
strict_columns: false   # false = cho phép thêm cột mới (additive OK)
                         # true = chặn mọi thay đổi schema
```

| strict_columns | Thêm cột mới | Xóa cột | Đổi type |
|:---|:---:|:---:|:---:|
| `false` | ✅ PASS | ❌ FAIL | ❌ FAIL |
| `true` | ❌ FAIL | ❌ FAIL | ❌ FAIL |

## PHẦN 2: CẤU TRÚC THƯ MỤC DỰ ÁN

```
medalguard-seminar/
│
├── README.md                          # Giới thiệu project
├── pyproject.toml                     # Python dependencies
├── Makefile                           # Automation commands
│
├── dbt_project/                       # dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml                   # DuckDB connection config
│   ├── models/
│   │   ├── sources.yml                # Source definitions (source schema)
│   │   ├── bronze/
│   │   │   ├── bronze_orders.sql      # SELECT * FROM source.orders
│   │   │   ├── bronze_lineitem.sql
│   │   │   ├── bronze_customer.sql
│   │   │   └── _bronze_models.yml     # Schema docs (no contracts)
│   │   ├── silver/
│   │   │   ├── silver_orders.sql      # Cleaned + typed orders
│   │   │   ├── silver_lineitem.sql    # Cleaned + typed lineitem
│   │   │   ├── silver_customer.sql
│   │   │   └── _silver_models.yml     # dbt contracts defined HERE
│   │   └── gold/
│   │       ├── gold_revenue_by_nation.sql
│   │       ├── gold_order_priority_summary.sql
│   │       └── _gold_models.yml       # Gold layer contracts
│   └── tests/                         # dbt tests (optional)
│
├── medalguard/                        # MedalGuard Python framework
│   ├── __init__.py
│   ├── gate.py                        # Core: ContractGate class
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── schema_validator.py        # Schema drift detection
│   │   ├── constraint_validator.py    # NOT NULL, type, range checks
│   │   └── semantic_validator.py      # Distribution / anomaly checks
│   ├── reporter.py                    # Violation logging + blast radius calc
│   └── config.py                      # Load YAML contracts
│
├── contracts/                         # MedalGuard YAML contract definitions
│   ├── bronze_to_silver/
│   │   ├── orders.yaml
│   │   ├── lineitem.yaml
│   │   └── customer.yaml
│   └── silver_to_gold/
│       ├── revenue_by_nation.yaml
│       └── order_priority_summary.yaml
│
├── mutations/                         # Schema Mutation Suite
│   ├── __init__.py
│   ├── base.py                        # BaseMutation abstract class
│   ├── m1_additive.py                 # Thêm cột mới
│   ├── m2_destructive.py              # Xóa / rename cột
│   ├── m3_type_change.py              # Đổi kiểu dữ liệu
│   ├── m4_constraint_breach.py        # Inject NULL / giá trị sai
│   └── m5_semantic_drift.py           # Giữ schema, đổi ngữ nghĩa
│
├── experiments/                       # Experiment runner
│   ├── runner.py                      # Chạy 1 experiment (1 mutation × 1 config)
│   ├── matrix_runner.py               # Chạy full matrix 5×4
│   └── config.yaml                    # Experiment configuration
│
├── metrics/                           # Metrics collection & analysis
│   ├── collector.py                   # Thu thập 4 metrics
│   ├── analyzer.py                    # Tính toán + so sánh
│   └── visualizer.py                  # Matplotlib/Plotly charts
│
├── results/                           # Output từ experiments
│   ├── raw/                           # JSON logs từ mỗi experiment run
│   ├── summary/                       # Aggregated results
│   └── charts/                        # Generated charts
│
├── data/                              # Data directory (gitignored)
│   └── warehouse.duckdb              # Main DuckDB database file
│
├── notebooks/                         # Jupyter notebooks (optional)
│   ├── 01_explore_tpch.ipynb
│   ├── 02_test_mutations.ipynb
│   └── 03_analyze_results.ipynb
│
└── docs/                              # Documentation
    ├── proposal.md                    # 1-page proposal
    └── report/                        # Seminar report (LaTeX or Word)
```

---

## PHẦN 3: TECH STACK & CÀI ĐẶT

### 3.1 Python Dependencies

```toml
# pyproject.toml
[project]
name = "medalguard-seminar"
requires-python = ">=3.10"
dependencies = [
    "duckdb>=1.1.0",
    "dbt-core>=1.8.0",
    "dbt-duckdb>=1.8.0",
    "great-expectations>=1.0.0",
    "duckdb-engine",
    "deltalake>=0.18.0",
    "pandas>=2.0",
    "pyarrow>=14.0",
    "pyyaml>=6.0",
    "matplotlib>=3.8",
    "tabulate>=0.9",
]
```

### 3.2 Cài đặt 1 lệnh duy nhất

```bash
# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Cài tất cả dependencies
pip install duckdb dbt-core dbt-duckdb great-expectations duckdb-engine deltalake pandas pyarrow pyyaml matplotlib tabulate
```

### 3.3 dbt profiles.yml

```yaml
# dbt_project/profiles.yml
medalguard:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "../data/warehouse.duckdb"
      schema: bronze
      threads: 4
      extensions:
        - tpch
```

### 3.4 dbt_project.yml

```yaml
# dbt_project/dbt_project.yml
name: "medalguard"
version: "1.0.0"
profile: "medalguard"

model-paths: ["models"]
test-paths: ["tests"]

models:
  medalguard:
    bronze:
      +schema: bronze
      +materialized: table
    silver:
      +schema: silver
      +materialized: table
    gold:
      +schema: gold
      +materialized: table
```

---

## PHẦN 4: WEEK-BY-WEEK PLAN CHI TIẾT

---

### WEEK 1 (14/09 – 20/09): Research Lock + Literature Review

**Mục tiêu:** Hiểu rõ bài toán, đọc papers, viết 1-page proposal.

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Đọc Paper 1: Jain et al. (CIDR 2023) — hiểu Lakehouse architecture, Delta Lake, ACID | Ghi chú 1 trang |
| T4 | Đọc Paper 2: Goedegebuure et al. (ACM 2024) — hiểu Data Mesh, tại sao cần Data Contracts | Ghi chú 1 trang |
| T5 | Đọc Paper 3: Wasser et al. (BMSD 2025) — hiểu Data Contract metamodel, research gap | Ghi chú 1 trang + highlight câu justify gap |
| T6 | Đọc Paper 4: Tagliabue et al. (arXiv 2026) — hiểu Bauplan, contract-by-design | Ghi chú 1 trang |
| T7–CN | Viết 1-page proposal theo template | File `docs/proposal.md` |

**1-page proposal nên có:**
- Problem statement (3-4 dòng)
- Research gap (2-3 dòng, cite Wasser 2025)
- Research questions (RQ1, RQ2, RQ3)
- Proposed method (MedalGuard + Mutation Suite)
- Expected contributions (4 items)

---

### WEEK 2 (21/09 – 27/09): Thiết kế Mutation Suite + Contract Specs

**Mục tiêu:** Thiết kế chi tiết 5 loại mutation và contract YAML cho từng gate.

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Nghiên cứu TPC-H schema chi tiết: đọc docs, hiểu quan hệ giữa 8 bảng | Sơ đồ ER diagram |
| T4 | Thiết kế 5 loại mutation cụ thể (xem Phần 6 bên dưới) | File `mutations/README.md` |
| T5–T6 | Viết contract YAML cho Gate 1 (bronze -> silver): orders, lineitem, customer | Files trong `contracts/bronze_to_silver/` |
| T7 | Viết contract YAML cho Gate 2 (silver -> gold): revenue, priority summary | Files trong `contracts/silver_to_gold/` |
| CN | Review lại thiết kế, chỉnh sửa | Updated docs |

**Contract YAML mẫu** (chi tiết ở Phần 5):

```yaml
# contracts/bronze_to_silver/orders.yaml
table: silver_orders
source_table: bronze_orders
columns:
  - name: o_orderkey
    type: BIGINT
    not_null: true
    unique: true
  - name: o_custkey
    type: BIGINT
    not_null: true
  - name: o_orderstatus
    type: VARCHAR
    not_null: true
    allowed_values: ["O", "F", "P"]
  - name: o_totalprice
    type: DOUBLE
    not_null: true
    min_value: 0
  - name: o_orderdate
    type: DATE
    not_null: true
quality_rules:
  - rule: "row_count"
    min: 1
  - rule: "null_rate"
    column: "o_custkey"
    max: 0.01
```

---

### WEEK 3 (28/09 – 04/10): Setup Environment + Generate TPC-H

**Mục tiêu:** Môi trường dev chạy được, TPC-H data sẵn sàng trong DuckDB.

| Ngày | Task | Output |
|:---|:---|:---|
| T2 | Tạo repo Git, cấu trúc thư mục, cài Python venv + dependencies | Repo trên GitHub/GitLab |
| T3 | Tạo `dbt_project.yml`, `profiles.yml`, test `dbt debug` chạy OK | dbt kết nối DuckDB thành công |
| T4 | Viết script sinh TPC-H data trong DuckDB source schema | `scripts/generate_tpch.py` |
| T5–T6 | Viết dbt Bronze models (SELECT * FROM source) | 3 models: `bronze_orders`, `bronze_lineitem`, `bronze_customer` |
| T7 | Chạy `dbt run` lần đầu, verify data trong bronze schema | Screenshot kết quả |
| CN | Debug nếu có lỗi | Clean run |

**Script sinh TPC-H:**

```python
# scripts/generate_tpch.py
import duckdb

def generate_tpch(db_path: str, scale_factor: float = 1.0):
    """Generate TPC-H data in DuckDB source schema."""
    con = duckdb.connect(db_path)
    con.execute("CREATE SCHEMA IF NOT EXISTS source")
    con.execute("INSTALL tpch; LOAD tpch;")
    con.execute(f"CALL dbgen(sf={scale_factor}, schema='source')")
    
    # Verify
    tables = con.execute(
        "SELECT table_name, estimated_size "
        "FROM duckdb_tables() WHERE schema_name = 'source'"
    ).fetchall()
    for name, size in tables:
        count = con.execute(f"SELECT COUNT(*) FROM source.{name}").fetchone()[0]
        print(f"  source.{name}: {count:,} rows")
    
    con.close()
    print("TPC-H data generated successfully!")

if __name__ == "__main__":
    generate_tpch("data/warehouse.duckdb", scale_factor=1.0)
```

---

### WEEK 4 (05/10 – 11/10): Hoàn thiện Pipeline end-to-end — GATE 1

**Mục tiêu:** Pipeline Bronze -> Silver -> Gold chạy end-to-end. **ĐÂY LÀ CHECKPOINT BẮT BUỘC.**

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Viết dbt Silver models (cleaned, typed, filtered) | 3 models: `silver_orders`, `silver_lineitem`, `silver_customer` |
| T4–T5 | Viết dbt Gold models (aggregated business tables) | 2 models: `gold_revenue_by_nation`, `gold_order_priority_summary` |
| T6 | Chạy full pipeline: `dbt run` từ bronze -> silver -> gold | Screenshot: tất cả models pass |
| T7 | Verify dữ liệu Gold: query thử, spot check kết quả | SQL queries + results |
| CN | Viết README hướng dẫn reproduce | `README.md` updated |

> [!IMPORTANT]
> **GATE 1 CHECKPOINT (cuối W4):**
> - [ ] DuckDB database chạy được, có TPC-H data trong `source` schema
> - [ ] `dbt run` chạy thành công tất cả models (bronze, silver, gold)
> - [ ] Query Gold tables ra kết quả hợp lý
> - [ ] Repo Git có README hướng dẫn reproduce
>
> **Nếu W4 mà chưa pass GATE 1 → dùng Fallback: chuyển sang SF=0.1 (~100MB) cho nhanh, debug trước.**

**Ví dụ Silver model:**

```sql
-- dbt_project/models/silver/silver_orders.sql
-- CHÚ Ý: KHÔNG có WHERE clause lọc dữ liệu.
-- Enforcement do dbt contracts / GX / MedalGuard đảm nhiệm.
-- Silver chỉ làm transform: cast type, select columns.
SELECT
    o_orderkey,
    o_custkey,
    o_orderstatus,
    CAST(o_totalprice AS DOUBLE) AS o_totalprice,
    CAST(o_orderdate AS DATE) AS o_orderdate,
    o_orderpriority,
    o_clerk,
    o_shippriority
FROM {{ ref('bronze_orders') }}
```

**Ví dụ Gold model:**

```sql
-- dbt_project/models/gold/gold_revenue_by_nation.sql
SELECT
    n.n_name AS nation,
    EXTRACT(YEAR FROM o.o_orderdate) AS order_year,
    COUNT(DISTINCT o.o_orderkey) AS total_orders,
    SUM(l.l_extendedprice * (1 - l.l_discount)) AS total_revenue,
    AVG(l.l_discount) AS avg_discount
FROM {{ ref('silver_orders') }} o
JOIN {{ ref('silver_lineitem') }} l ON o.o_orderkey = l.l_orderkey
JOIN {{ ref('silver_customer') }} c ON o.o_custkey = c.c_custkey
JOIN source.nation n ON c.c_nationkey = n.n_nationkey
GROUP BY n.n_name, EXTRACT(YEAR FROM o.o_orderdate)
ORDER BY nation, order_year
```

---

### WEEK 5 (12/10 – 18/10): Implement Config 1 — dbt contracts

**Mục tiêu:** Bật dbt contracts trên Silver models, test với dữ liệu sạch và dữ liệu lỗi.

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Thêm contract definitions vào `_silver_models.yml` | YAML file với `contract: {enforced: true}` |
| T4 | Test với dữ liệu sạch (TPC-H gốc) — pipeline phải PASS | Screenshot: dbt run success |
| T5 | Test thủ công: inject 1 lỗi đơn giản (xóa 1 cột), xem dbt có fail không | Screenshot: dbt contract error message |
| T6 | Test thủ công: inject lỗi type mismatch, xem dbt phản ứng ra sao | Ghi chép kết quả |
| T7–CN | Ghi chú: dbt contracts bắt được loại lỗi nào, bỏ sót loại nào | Document findings |

**dbt contract YAML:**

```yaml
# dbt_project/models/silver/_silver_models.yml
version: 2

models:
  - name: silver_orders
    config:
      contract:
        enforced: true    # <-- BẬT CONTRACT
    columns:
      - name: o_orderkey
        data_type: bigint
        constraints:
          - type: not_null
          - type: primary_key
      - name: o_custkey
        data_type: bigint
        constraints:
          - type: not_null
      - name: o_orderstatus
        data_type: varchar
        constraints:
          - type: not_null
          - type: check
            expression: "o_orderstatus IN ('O', 'F', 'P')"
      - name: o_totalprice
        data_type: double
        constraints:
          - type: not_null
          - type: check
            expression: "o_totalprice >= 0"
      - name: o_orderdate
        data_type: date
        constraints:
          - type: not_null
      - name: o_orderpriority
        data_type: varchar
      - name: o_clerk
        data_type: varchar
      - name: o_shippriority
        data_type: integer
```

---

### WEEK 6 (19/10 – 25/10): Implement Config 2 — Great Expectations

**Mục tiêu:** GX validate suite chạy được trên DuckDB tables.

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Setup Great Expectations: context, data source, connect DuckDB | `scripts/setup_gx.py` |
| T4 | Viết expectation suite cho silver_orders (not_null, value ranges, allowed values) | GX suite JSON/Python |
| T5 | Viết expectation suite cho silver_lineitem | GX suite |
| T6 | Test với dữ liệu sạch — tất cả expectations phải PASS | GX validation result |
| T7 | Test thủ công: inject 1 lỗi, xem GX có bắt không | Ghi chép so sánh với dbt |
| CN | Đánh giá sơ bộ: dbt contracts vs GX — mỗi tool bắt loại gì | Notes |

**Great Expectations setup code:**

```python
# scripts/setup_gx.py
import great_expectations as gx

context = gx.get_context(mode="ephemeral")

# Connect to DuckDB
source = context.data_sources.add_sql(
    name="duckdb_warehouse",
    connection_string="duckdb:///data/warehouse.duckdb"
)

# Silver Orders asset
orders_asset = source.add_table_asset(
    name="silver_orders",
    table_name="silver.silver_orders"
)
orders_batch = orders_asset.add_batch_definition_whole_table("all_orders")

# Create expectation suite
suite = context.suites.add(
    gx.ExpectationSuite(name="silver_orders_suite")
)

suite.add_expectation(
    gx.expectations.ExpectColumnValuesToNotBeNull(column="o_orderkey")
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeUnique(column="o_orderkey")
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeInSet(
        column="o_orderstatus",
        value_set=["O", "F", "P"]
    )
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="o_totalprice",
        min_value=0
    )
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToNotBeNull(column="o_orderdate")
)

# Run validation
validation_def = context.validation_definitions.add(
    gx.ValidationDefinition(
        name="silver_orders_val",
        data=orders_batch,
        suite=suite
    )
)
result = validation_def.run()
print(f"Success: {result.success}")
```

---

### WEEK 7-8 (26/10 – 08/11): Build MedalGuard Framework

**Mục tiêu:** MedalGuard core hoạt động: đọc contract YAML, validate data, output violations.

**WEEK 7:**

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Viết `config.py`: load contract YAML, parse thành Python objects | Tested |
| T4–T5 | Viết `schema_validator.py`: so sánh columns giữa upstream/downstream | Tested |
| T6–T7 | Viết `constraint_validator.py`: NOT NULL, type check, value range, allowed values | Tested |

**WEEK 8:**

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Viết `semantic_validator.py`: distribution check (mean, stddev drift) | Tested |
| T4 | Viết `reporter.py`: ghi log violations, tính blast radius | Tested |
| T5–T6 | Viết `gate.py`: ContractGate class tích hợp tất cả validators | Tested end-to-end |
| T7–CN | Test MedalGuard với dữ liệu sạch (pass) và dữ liệu lỗi (detect) | Unit tests pass |

**MedalGuard core code (gate.py):**

```python
# medalguard/gate.py
import duckdb
import time
from dataclasses import dataclass, field
from .config import load_contract
from .validators.schema_validator import SchemaValidator
from .validators.constraint_validator import ConstraintValidator
from .validators.semantic_validator import SemanticValidator
from .reporter import ViolationReporter

@dataclass
class ValidationResult:
    gate_name: str
    passed: bool
    violations: list = field(default_factory=list)
    blast_radius: float = 0.0        # % faulty records
    detection_stage: str = ""         # "B->S" or "S->G"
    validation_time_ms: float = 0.0   # milliseconds

class ContractGate:
    def __init__(self, gate_name: str, contract_path: str, db_path: str):
        self.gate_name = gate_name
        self.contract = load_contract(contract_path)
        self.db_path = db_path
        self.schema_validator = SchemaValidator()
        self.constraint_validator = ConstraintValidator()
        self.semantic_validator = SemanticValidator()
        self.reporter = ViolationReporter()

    def validate(self, source_table: str, target_table: str) -> ValidationResult:
        """Run all validations and return result."""
        start = time.perf_counter()
        violations = []
        con = duckdb.connect(self.db_path, read_only=True)

        # 1. Schema Drift Detection
        violations += self.schema_validator.check(
            con, source_table, target_table, self.contract
        )

        # 2. Constraint Validation (NOT NULL, types, ranges, allowed values)
        violations += self.constraint_validator.check(
            con, target_table, self.contract
        )

        # 3. Semantic Drift Detection (distribution anomalies)
        violations += self.semantic_validator.check(
            con, source_table, target_table, self.contract
        )

        con.close()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Calculate blast radius
        blast_radius = self.reporter.calculate_blast_radius(
            violations, self.db_path, target_table
        )

        return ValidationResult(
            gate_name=self.gate_name,
            passed=len(violations) == 0,
            violations=violations,
            blast_radius=blast_radius,
            detection_stage=self.gate_name,
            validation_time_ms=elapsed_ms
        )
```

**Schema Validator:**

```python
# medalguard/validators/schema_validator.py

class SchemaValidator:
    def check(self, con, source_table, target_table, contract) -> list:
        violations = []

        # Get actual columns from database
        actual_cols = {
            row[0]: row[1]
            for row in con.execute(
                f"SELECT column_name, data_type "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{target_table.split('.')[-1]}'"
            ).fetchall()
        }

        # Check against contract
        for col_spec in contract["columns"]:
            col_name = col_spec["name"]
            expected_type = col_spec["type"].upper()

            if col_name not in actual_cols:
                violations.append({
                    "type": "MISSING_COLUMN",
                    "column": col_name,
                    "message": f"Column '{col_name}' defined in contract but missing in table"
                })
            elif not self._types_compatible(actual_cols[col_name], expected_type):
                violations.append({
                    "type": "TYPE_MISMATCH",
                    "column": col_name,
                    "expected": expected_type,
                    "actual": actual_cols[col_name],
                    "message": f"Column '{col_name}': expected {expected_type}, got {actual_cols[col_name]}"
                })

        # Check for unexpected columns (drift)
        contract_cols = {c["name"] for c in contract["columns"]}
        for actual_col in actual_cols:
            if actual_col not in contract_cols:
                violations.append({
                    "type": "UNEXPECTED_COLUMN",
                    "column": actual_col,
                    "message": f"Column '{actual_col}' exists in table but not in contract (schema drift)"
                })

        return violations

    def _types_compatible(self, actual: str, expected: str) -> bool:
        """Check if actual DB type is compatible with expected contract type."""
        type_map = {
            "BIGINT": ["BIGINT", "INTEGER", "INT8", "INT64"],
            "INTEGER": ["INTEGER", "INT", "INT4", "INT32"],
            "DOUBLE": ["DOUBLE", "FLOAT8", "DECIMAL", "NUMERIC", "FLOAT"],
            "VARCHAR": ["VARCHAR", "TEXT", "STRING", "CHAR"],
            "DATE": ["DATE"],
            "TIMESTAMP": ["TIMESTAMP", "DATETIME"],
        }
        expected_upper = expected.upper()
        actual_upper = actual.upper()
        for canonical, aliases in type_map.items():
            if expected_upper in aliases or expected_upper == canonical:
                return actual_upper in aliases or actual_upper == canonical
        return actual_upper == expected_upper
```

---

### WEEK 9 (09/11 – 15/11): Implement Mutation Suite

**Mục tiêu:** 5 loại mutation hoạt động, inject được vào source schema.

| Ngày | Task | Output |
|:---|:---|:---|
| T2 | Viết `base.py`: BaseMutation abstract class | Base class |
| T3 | Viết `m1_additive.py` + `m2_destructive.py` | Tested trên source schema |
| T4 | Viết `m3_type_change.py` + `m4_constraint_breach.py` | Tested |
| T5 | Viết `m5_semantic_drift.py` | Tested |
| T6–T7 | Viết `experiments/runner.py`: chạy 1 experiment (1 mutation x 1 config) | Runner hoạt động |
| CN | Test thử 2-3 experiments để verify | Results logged |

**Chi tiết 5 loại Mutation — xem Phần 6 bên dưới.**

---

### WEEK 10-11 (16/11 – 29/11): Chạy Full Experiments

**Mục tiêu:** Chạy full matrix 5 mutations x 4 configs = 20 experiments, thu thập metrics.

**WEEK 10:**

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Viết `matrix_runner.py`: tự động chạy 20 experiments | Script hoàn chỉnh |
| T4–T5 | Chạy experiments cho M1 (Additive) x 4 configs | 4 result files |
| T6–T7 | Chạy experiments cho M2 (Destructive) x 4 configs | 4 result files |
| CN | Chạy experiments cho M3 (Type Change) x 4 configs | 4 result files |

**WEEK 11:**

| Ngày | Task | Output |
|:---|:---|:---|
| T2 | Chạy experiments cho M4 (Constraint Breach) x 4 configs | 4 result files |
| T3 | Chạy experiments cho M5 (Semantic Drift) x 4 configs | 4 result files |
| T4–T5 | Re-run bất kỳ experiment nào bị lỗi hoặc kết quả bất thường | Clean results |
| T6–T7 | Tổng hợp tất cả results vào summary table | `results/summary/` |

---

### WEEK 12-13 (30/11 – 13/12): Phân tích + Viết báo cáo

**WEEK 12:**

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Viết `metrics/analyzer.py` + `visualizer.py`: tính toán và vẽ charts | Charts trong `results/charts/` |
| T4–T5 | Viết phần Introduction + Related Work trong báo cáo | Draft 1 |
| T6–T7 | Viết phần Methodology (MedalGuard design, Mutation Suite, Experiment setup) | Draft 1 |

**WEEK 13:**

| Ngày | Task | Output |
|:---|:---|:---|
| T2–T3 | Viết phần Results + Discussion | Draft 1 |
| T4 | Viết phần Conclusion + Future Work | Draft 1 |
| T5–T7 | Review toàn bộ, chỉnh sửa, format | Draft 2 (gửi GV review) |

---

### WEEK 14 (14/12 – 20/12): Review + Chỉnh sửa

| Task | Output |
|:---|:---|
| Nhận feedback GV, chỉnh sửa báo cáo | Final report |
| Bổ sung experiments nếu GV yêu cầu | Updated results |
| Kiểm tra lại code, clean up repo | Clean repo |

---

### WEEK 15 (21/12 – 28/12): Thuyết trình

| Task | Output |
|:---|:---|
| Làm slide (15-20 slides) | PowerPoint/Google Slides |
| Tập thuyết trình (15-20 phút) | Rehearsal |
| Bảo vệ Seminar | Final presentation |

---

## PHẦN 5: MedalGuard CONTRACT YAML FORMAT

### 5.1 Contract cho Gate Bronze -> Silver

```yaml
# contracts/bronze_to_silver/lineitem.yaml
table: silver_lineitem
source_table: bronze_lineitem

columns:
  - name: l_orderkey
    type: BIGINT
    not_null: true
  - name: l_partkey
    type: BIGINT
    not_null: true
  - name: l_suppkey
    type: BIGINT
    not_null: true
  - name: l_linenumber
    type: INTEGER
    not_null: true
  - name: l_quantity
    type: DOUBLE
    not_null: true
    min_value: 1
    max_value: 50
  - name: l_extendedprice
    type: DOUBLE
    not_null: true
    min_value: 0
  - name: l_discount
    type: DOUBLE
    not_null: true
    min_value: 0.0
    max_value: 0.10
  - name: l_tax
    type: DOUBLE
    not_null: true
    min_value: 0.0
    max_value: 0.08
  - name: l_returnflag
    type: VARCHAR
    allowed_values: ["R", "A", "N"]
  - name: l_linestatus
    type: VARCHAR
    allowed_values: ["O", "F"]
  - name: l_shipdate
    type: DATE
    not_null: true
  - name: l_commitdate
    type: DATE
    not_null: true
  - name: l_receiptdate
    type: DATE
    not_null: true
  - name: l_shipinstruct
    type: VARCHAR
  - name: l_shipmode
    type: VARCHAR
    allowed_values: ["AIR", "REG AIR", "RAIL", "SHIP", "TRUCK", "MAIL", "FOB"]
  - name: l_comment
    type: VARCHAR

quality_rules:
  - rule: row_count
    min: 1
  - rule: null_rate
    column: l_orderkey
    max: 0.0
  - rule: mean_range
    column: l_discount
    min: 0.03
    max: 0.07
  - rule: mean_range
    column: l_quantity
    min: 20
    max: 30
```

---

## PHẦN 6: SCHEMA MUTATION SUITE — CHI TIẾT

### 6.1 Mutation Framework

```python
# mutations/base.py
from abc import ABC, abstractmethod
import duckdb

class BaseMutation(ABC):
    """Base class for all schema mutations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short name, e.g. 'M1_ADDITIVE'."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""

    @property
    @abstractmethod
    def category(self) -> str:
        """One of: additive, destructive, type_change, constraint_breach, semantic_drift."""

    @abstractmethod
    def apply(self, con: duckdb.DuckDBPyConnection) -> None:
        """Apply mutation to source schema tables."""

    @abstractmethod
    def revert(self, con: duckdb.DuckDBPyConnection) -> None:
        """Revert mutation (restore original state)."""
```

### 6.2 Chi tiết 5 loại Mutation

#### M1: Additive (Thêm cột mới)

```python
# mutations/m1_additive.py
class AdditiveMutation(BaseMutation):
    name = "M1_ADDITIVE"
    description = "Add l_promo_code VARCHAR(20) column to lineitem"
    category = "additive"

    def apply(self, con):
        con.execute("""
            ALTER TABLE source.lineitem
            ADD COLUMN l_promo_code VARCHAR(20) DEFAULT 'NONE'
        """)
        # Fill some rows with promo codes
        con.execute("""
            UPDATE source.lineitem
            SET l_promo_code = CASE
                WHEN l_linenumber % 10 = 0 THEN 'PROMO10'
                WHEN l_linenumber % 5 = 0 THEN 'SALE5'
                ELSE 'NONE'
            END
        """)

    def revert(self, con):
        con.execute("ALTER TABLE source.lineitem DROP COLUMN l_promo_code")
```

**Kỳ vọng:** Pipeline nên xử lý gracefully — cột mới không gây crash nhưng có thể không xuất hiện ở Silver/Gold. MedalGuard nên phát hiện "unexpected column" nếu contract không có `l_promo_code`.

#### M2: Destructive (Xóa/Rename cột)

```python
# mutations/m2_destructive.py
class DestructiveMutation(BaseMutation):
    name = "M2_DESTRUCTIVE"
    description = "Drop l_tax column from lineitem (breaking change)"
    category = "destructive"

    def apply(self, con):
        # Save backup first
        con.execute("CREATE TABLE source.lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("ALTER TABLE source.lineitem DROP COLUMN l_tax")

    def revert(self, con):
        con.execute("DROP TABLE IF EXISTS source.lineitem")
        con.execute("ALTER TABLE source.lineitem_backup RENAME TO lineitem")
```

**Kỳ vọng:** dbt contract PHẢI fail vì `l_tax` bị thiếu. Config C0 (no check) sẽ cho lỗi chạy xuống Gold (Silent Failure).

#### M3: Type Change (Đổi kiểu dữ liệu)

```python
# mutations/m3_type_change.py
class TypeChangeMutation(BaseMutation):
    name = "M3_TYPE_CHANGE"
    description = "Change l_quantity from DOUBLE to VARCHAR (incompatible type)"
    category = "type_change"

    def apply(self, con):
        con.execute("CREATE TABLE source.lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("""
            CREATE OR REPLACE TABLE source.lineitem AS
            SELECT
                * EXCLUDE (l_quantity),
                CAST(l_quantity AS VARCHAR) AS l_quantity
            FROM source.lineitem_backup
        """)

    def revert(self, con):
        con.execute("DROP TABLE IF EXISTS source.lineitem")
        con.execute("ALTER TABLE source.lineitem_backup RENAME TO lineitem")
```

**Kỳ vọng:** dbt contract detect type mismatch (VARCHAR vs DOUBLE). MedalGuard schema validator cũng bắt.

#### M4: Constraint Breach (Vi phạm ràng buộc)

```python
# mutations/m4_constraint_breach.py
class ConstraintBreachMutation(BaseMutation):
    name = "M4_CONSTRAINT_BREACH"
    description = "Inject NULL into o_custkey and negative o_totalprice in orders"
    category = "constraint_breach"

    def apply(self, con):
        # Inject 100 rows with NULL o_custkey (FK, not PK - safe to nullify)
        con.execute("""
            UPDATE source.orders
            SET o_custkey = NULL
            WHERE rowid IN (
                SELECT rowid FROM source.orders LIMIT 100
            )
        """)
        # Inject 200 rows with negative totalprice
        con.execute("""
            UPDATE source.orders
            SET o_totalprice = -1 * ABS(o_totalprice)
            WHERE rowid IN (
                SELECT rowid FROM source.orders
                WHERE o_custkey IS NOT NULL
                LIMIT 200
            )
        """)

    def revert(self, con):
        # Reset orders from TPC-H generator
        con.execute("DROP TABLE IF EXISTS source.orders")
        con.execute("LOAD tpch;")
        con.execute("CALL dbgen(sf=1, schema='source', children=['orders'])")
```

**Kỳ vọng:** dbt `not_null` và `check` constraints sẽ bắt được. GX expectation cũng bắt. Nhưng nếu Config C0, tất cả 300 records lỗi sẽ lọt xuống Gold → Blast Radius cao.

#### M5: Semantic Drift (Schema đúng, ngữ nghĩa sai)

```python
# mutations/m5_semantic_drift.py
class SemanticDriftMutation(BaseMutation):
    name = "M5_SEMANTIC_DRIFT"
    description = "Change l_discount from fraction (0.05) to percentage (5.0) - same column type, wrong semantics"
    category = "semantic_drift"

    def apply(self, con):
        # Multiply discount by 100: 0.05 -> 5.0
        # Column type stays DOUBLE, no schema change!
        con.execute("""
            UPDATE source.lineitem
            SET l_discount = l_discount * 100
        """)

    def revert(self, con):
        con.execute("""
            UPDATE source.lineitem
            SET l_discount = l_discount / 100
        """)
```

**Kỳ vọng:** dbt contracts sẽ KHÔNG bắt (schema đúng, type đúng). GX `ExpectColumnValuesToBeBetween(max_value=0.10)` SẼ bắt. MedalGuard `mean_range` check cũng bắt (mean đột ngột tăng từ ~0.05 lên ~5.0). **Đây là mutation quan trọng nhất — chứng minh structural contracts không đủ.**

---

## PHẦN 7: EXPERIMENT MATRIX & METRICS

### 7.1 Ma trận thực nghiệm

Tổng cộng **20 experiments** (5 mutations x 4 configs):

| | C0 (No check) | C1 (dbt) | C2 (GX) | C3 (MedalGuard) |
|:---|:---:|:---:|:---:|:---:|
| **M1 Additive** | E01 | E02 | E03 | E04 |
| **M2 Destructive** | E05 | E06 | E07 | E08 |
| **M3 Type Change** | E09 | E10 | E11 | E12 |
| **M4 Constraint Breach** | E13 | E14 | E15 | E16 |
| **M5 Semantic Drift** | E17 | E18 | E19 | E20 |

### 7.2 Quy trình chạy 1 experiment

```python
# experiments/runner.py (simplified)
def run_experiment(mutation, config, db_path) -> ExperimentResult:
    """Run one experiment: apply mutation, run pipeline, measure metrics."""

    # 0. Reset database to clean TPC-H state
    reset_database(db_path)

    # 1. Apply mutation to source schema
    con = duckdb.connect(db_path)
    mutation.apply(con)
    con.close()

    # 2. Run pipeline based on config
    start_time = time.perf_counter()

    if config.medalguard_enabled:
        # Run MedalGuard Gate 1 (B->S)
        gate1 = ContractGate("B->S", "contracts/bronze_to_silver/...", db_path)
        gate1_result = gate1.validate("bronze.bronze_lineitem", "silver.silver_lineitem")

    if config.dbt_contracts_enabled:
        # dbt run with contracts enforced
        result = subprocess.run(["dbt", "run"], capture_output=True, cwd="dbt_project/")
        dbt_success = result.returncode == 0
    else:
        # dbt run without contracts
        result = subprocess.run(["dbt", "run", "--vars", "{contracts_off: true}"], ...)

    if config.gx_enabled:
        # Run Great Expectations validation
        gx_result = run_gx_validation(db_path)

    if config.medalguard_enabled:
        # Run MedalGuard Gate 2 (S->G)
        gate2 = ContractGate("S->G", "contracts/silver_to_gold/...", db_path)
        gate2_result = gate2.validate("silver.silver_orders", "gold.gold_revenue_by_nation")

    elapsed = time.perf_counter() - start_time

    # 3. Measure metrics
    metrics = collect_metrics(mutation, config, gate1_result, gate2_result,
                              dbt_success, gx_result, elapsed, db_path)

    # 4. Revert mutation
    con = duckdb.connect(db_path)
    mutation.revert(con)
    con.close()

    return metrics
```

### 7.3 Cách đo 7 Metrics chi tiết (theo yêu cầu GV)

#### Metric 1: Detection Rate (METRIC CHÍNH)

```
Detection Rate = (Số mutations bị DETECTED) / (Tổng mutations injected) x 100%
```

Với mỗi experiment, ghi nhận:
- `detected = True/False` — pipeline có phát hiện lỗi không (dbt fail, GX fail, hoặc MedalGuard violations > 0)?
- Sau đó aggregating theo config: `DR(C1) = count(detected=True for C1) / 5 * 100%`
- **Target GV: ≥ 95%; stretch 100% trên known mutations**

#### Metric 2: Blast Radius

```
Blast Radius = (Số records lỗi ở Gold) / (Tổng records lỗi đã inject) x 100%
```

Cách đo (theo GV: đo bằng record/partition bị nhiễm TRƯỚC khi chặn):
- Trước khi chạy pipeline: đếm records bị affect bởi mutation
- Sau khi pipeline chạy xong: query Gold tables, đếm records bị corrupt
- Nếu pipeline bị block/quarantine: Blast Radius = 0% (lỗi bị chặn)
- Nếu pipeline chạy xong mà không detect: Blast Radius = 100% (lỗi lan hết)
- **Target GV: ≤ 1-5%; baseline (C0) cao hơn rõ rệt**

#### Metric 3: Detection Stage

```
Detection Stage = "B->S" | "S->G" | "NOT_DETECTED"
```

Ghi nhận lỗi bị bắt ở đâu:
- `B->S`: MedalGuard Gate 1 hoặc dbt Silver model fail
- `S->G`: MedalGuard Gate 2 hoặc GX validation fail
- `NOT_DETECTED`: Lỗi lọt qua tất cả gates
- **Target GV: ≥ 90% bắt tại Bronze→Silver khi có thể**

#### Metric 4: False Positive Rate (MỚI — theo yêu cầu GV)

```
FPR = (Số benign mutations bị chặn nhầm) / (Tổng benign mutations) x 100%
```

Cần tạo thêm **3 benign mutations** (thay đổi hợp lệ) để test:
- B1: Thêm cột comment mới (additive, hợp lệ)
- B2: Thay đổi giá trị trong phạm vi (discount 0.05 → 0.08)
- B3: Thêm records mới (insert thêm orders)

Mỗi benign × 4 configs = 12 experiments phụ.
- **Target GV: FPR ≤ 2-5%**

#### Metric 5: Time-to-Detect (MỚI — theo yêu cầu GV)

```
TTD = detection_stage_index  (0 = immediate, 1 = after Bronze, 2 = after Silver)
```

Đo bằng đơn vị "pipeline stages":
- 0 = MedalGuard Gate 1 bắt ngay trước khi data vào Silver
- 1 = dbt contracts bắt khi Silver model chạy
- 2 = GX / MedalGuard Gate 2 bắt sau Silver
- ∞ = NOT_DETECTED

GV nhấn mạnh: TTD phản ánh chữ "Early" trong title đề tài.
- **Target GV: gần 1 pipeline stage cho hầu hết mutations**

#### Metric 6: Pipeline Overhead

```
Overhead = (T_config - T_baseline) / T_baseline x 100%
```

- `T_baseline`: thời gian chạy pipeline Config C0 (no check) với clean data
- `T_config`: thời gian chạy pipeline với config đó + clean data (không có mutation)
- Đo riêng với clean data để tách biệt overhead của enforcement vs overhead của lỗi
- Chạy 3 lần, lấy **median** (bền hơn mean)
- **Target GV: < 10-15%**

#### Metric 7: Recovery Success Rate (MỚI — theo yêu cầu GV)

```
Recovery = (Số incidents pipeline resume thành công sau quarantine) / (Tổng incidents) x 100%
```

Quy trình test:
1. Inject mutation → MedalGuard quarantine data lỗi
2. Fix: revert mutation ở source
3. Re-run pipeline → verify Gold data trở lại đúng
4. Ghi nhận: pass/fail

- **Target GV: ≥ 95% test incidents**

### 7.4 Ablation Study (BẮT BUỘC theo GV)

> "Ít nhất 1 ablation chứng minh thành phần mới có đóng góp"

Ma trận ablation: bỏ từng validator của MedalGuard:

| Ablation | Schema Validator | Constraint Validator | Semantic Validator | Mục đích |
|:---|:---:|:---:|:---:|:---|
| C3-Full | ✅ | ✅ | ✅ | Full MedalGuard |
| A1: No Schema | ❌ | ✅ | ✅ | Schema drift detection có quan trọng? |
| A2: No Constraint | ✅ | ❌ | ✅ | NOT NULL/range check có quan trọng? |
| A3: No Semantic | ✅ | ✅ | ❌ | Mean/distribution check có quan trọng? |
| A4: Schema Only | ✅ | ❌ | ❌ | Schema check đơn lẻ đủ mạnh không? |

Mỗi ablation × 5 mutations = 25 experiments.

### 7.5 Stress Test (theo gợi ý GV)

Chạy Pipeline Overhead ở nhiều Scale Factor:

| Scale Factor | Dữ liệu | Mục đích |
|:---|:---|:---|
| SF=0.1 | ~100MB, ~600K rows | Development & debug |
| SF=1 | ~1GB, ~6M rows | Main experiments |
| SF=10 | ~10GB, ~60M rows | Stress test (nếu tài nguyên cho phép) |

Báo cáo: overhead scaling là tuyến tính, sublinear, hay superlinear?

### 7.6 Tổng experiments

| Nhóm | Số experiments |
|:---|:---:|
| Ma trận chính (5 mutations × 4 configs) | 20 |
| Benign mutations (3 benign × 4 configs) | 12 |
| Ablation study (5 mutations × 4 ablations) | 20 |
| Stress test (3 SFs × 1 config overhead) | 3 |
| **Tổng** | **55** |

---

## PHẦN 8: CẤU TRÚC BÁO CÁO SEMINAR (theo khung 5 phần của GV)

```
1. Mục tiêu & Property (2 trang)
   - 1.1 Background: Medallion Lakehouse, Data Contracts, Schema Evolution
   - 1.2 Problem: Silent Failures khi data qua các layer
   - 1.3 Properties cần chứng minh: Data Quality, Reliability, Observability
   - 1.4 Research Questions (RQ1, RQ2, RQ3)
   - 1.5 Related Work (Jain 2023, Goedegebuure 2024, Wasser 2025, Tagliabue 2026)
   - 1.6 Gap analysis: thiếu empirical evaluation

2. Pipeline / Data & Baseline (2 trang)
   - 2.1 TPC-H Dataset (schema, scale factors)
   - 2.2 Medallion Pipeline Architecture (Bronze → Silver → Gold)
   - 2.3 MedalGuard Framework (gate.py, 3 validators, quarantine, contract versioning)
   - 2.4 Contract Specification Format (YAML examples)
   - 2.5 Baseline: C0 (no check), C1 (dbt contracts), C2 (Great Expectations)

3. Metric chính + Metric phụ (2 trang)
   - 3.1 Metrics chính: Detection Rate, Blast Radius
   - 3.2 Metrics phụ: Detection Stage, FPR, TTD, Pipeline Overhead, Recovery
   - 3.3 Schema Mutation Suite (5 loại + 3 benign, bảng tổng hợp)
   - 3.4 Experiment Matrix (5×4 + ablation + benign + stress = 55 experiments)

4. Ablation / Failure Injection / Error Analysis (4-5 trang)
   - 4.1 Main Results: Detection Rate (bar chart 4 configs)
   - 4.2 Blast Radius analysis (heatmap 5×4 + 3 benign)
   - 4.3 Detection Stage + Time-to-Detect (stacked bar chart)
   - 4.4 False Positive Rate (benign mutations analysis)
   - 4.5 Ablation study (bỏ từng validator — 4 ablations)
   - 4.6 Stress test (SF=0.1, 1, 10 — overhead scaling chart)
   - 4.7 Error Analysis: mutations không bắt được + false positives + root causes
   - 4.8 Recovery test results

5. Kết luận Contribution & Trade-off (1.5 trang)
   - 5.1 Contribution: multi-tier tốt hơn single-tier bao nhiêu %
   - 5.2 Trade-off: overhead vs detection quality
   - 5.3 Limitations
   - 5.4 Future work: CDC, self-healing, lineage tracking, real streaming

References (1 trang)

Total: ~13-16 trang (phù hợp Seminar)
```

---

## PHẦN 9: QUẢN LÝ RỦI RO

| Rủi ro | Xác suất | Tác động | Phòng ngừa | Fallback |
|:---|:---:|:---:|:---|:---|
| dbt-duckdb contracts không hoạt động đúng | Thấp | Cao | Test sớm ở W5 | Dùng dbt tests thay cho contracts |
| Great Expectations API thay đổi | Trung bình | Trung bình | Pin version trong `pyproject.toml` | Dùng Soda Core hoặc custom Python validation |
| DuckDB file lock khi chạy đồng thời | Trung bình | Thấp | Chạy tuần tự, đóng connection sau mỗi bước | Dùng read_only=True khi validate |
| Thiếu thời gian cho 20 experiments | Trung bình | Cao | Track progress hàng tuần | Giảm xuống 3 mutations x 3 configs = 9 experiments |
| Kết quả không khác biệt giữa configs | Thấp | Cao | Thiết kế mutation đa dạng (đặc biệt M5) | Focus phân tích qualitative nếu quantitative không rõ |
| Laptop chạy chậm với SF=1 | Thấp | Trung bình | Dùng SF=0.1 để dev, SF=1 chỉ khi chạy final | Báo cáo với SF=0.1 nếu cần |

---

## PHẦN 10: CHECKLIST DELIVERABLES

### GATE 1 (Cuối Week 4)

- [ ] Git repo có README
- [ ] DuckDB + TPC-H data (source schema)
- [ ] dbt pipeline: bronze -> silver -> gold chạy end-to-end
- [ ] Query Gold tables ra kết quả đúng

### GATE 2 (Cuối Week 8)

- [ ] Config C1 (dbt contracts) hoạt động
- [ ] Config C2 (Great Expectations) hoạt động
- [ ] MedalGuard framework (gate.py + 3 validators) hoạt động
- [ ] Test thử với 1-2 mutations -> detect đúng

### GATE 3 (Cuối Week 11)

- [ ] 5 loại Mutation implement xong
- [ ] 20 experiments chạy xong
- [ ] 4 metrics thu thập xong
- [ ] Summary table hoàn chỉnh

### FINAL (Week 15)

- [ ] Báo cáo Seminar (~13-15 trang)
- [ ] Slide thuyết trình (15-20 slides)
- [ ] Code repo clean, có README hướng dẫn reproduce
- [ ] Results + charts trong thư mục `results/`

---

## KẾT QUẢ KỲ VỌNG (DỰ ĐOÁN)

Dựa trên thiết kế, tôi dự đoán kết quả sẽ trông như thế này:

| Mutation | C0 (No check) | C1 (dbt) | C2 (GX) | C3 (MedalGuard) |
|:---|:---|:---|:---|:---|
| **M1 Additive** | Not detected, BR=0% (harmless) | Detect: unexpected column | Not detected (GX chỉ check existing cols) | Detect ở Gate B->S |
| **M2 Destructive** | Pipeline crash hoặc Silent Failure | **Detect**: missing column error | Not detected (column missing -> expectation skip) | **Detect** ở Gate B->S |
| **M3 Type Change** | Silent Failure, data bị cast sai | **Detect**: type mismatch | Có thể detect (type-based expectations) | **Detect** ở Gate B->S |
| **M4 Constraint Breach** | Silent Failure, BR=100% | **Detect**: NOT NULL/CHECK fail | **Detect**: value out of range | **Detect** ở cả 2 Gates |
| **M5 Semantic Drift** | Silent Failure, BR=100% | **NOT detected** (schema OK!) | **Detect**: value out of expected range | **Detect** ở Gate B->S (mean_range check) |
| **Detection Rate** | **0%** | **60%** (3/5) | **40-60%** (2-3/5) | **100%** (5/5) |

> [!TIP]
> **M5 (Semantic Drift) là "star result" của đề tài** — nó chứng minh rằng structural contracts (dbt) KHÔNG ĐỦ và cần thêm semantic/statistical checks (GX + MedalGuard) để bắt loại lỗi nguy hiểm nhất.

---

## PHẦN 11: REPRODUCIBILITY

### 11.1 Experiment Config

```yaml
# experiments/config.yaml
experiment:
  repeat_count: 3              # Mỗi experiment chạy 3 lần cho Pipeline Overhead
  scale_factor: 1.0            # SF=0.1 cho dev, SF=1 cho final
  random_seed: 42              # Fixed seed

hardware:                       # Ghi lại specs máy vào báo cáo
  cpu: "..."
  ram: "..."
  storage: "SSD / HDD"
  os: "Windows 11"
  python_version: "3.11.x"
  duckdb_version: "1.x.x"
  dbt_version: "1.8.x"
```

### 11.2 Quy tắc

- **Detection Rate, Blast Radius, Detection Stage**: Deterministic (chạy 1 lần là đủ)
- **Pipeline Overhead**: Chạy 3 lần, lấy **median** (median bền hơn mean với outliers)
- Mỗi experiment bắt đầu từ **clean TPC-H state** (reset database trước khi inject mutation)
- Kết quả lưu dạng JSON trong `results/raw/` với timestamp + config + mutation name
