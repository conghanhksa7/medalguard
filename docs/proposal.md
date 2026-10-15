# ĐỀ XUẤT ĐỀ TÀI CUỐI CÙNG

---

## Tại sao đổi đề tài?

Đề tài cũ (benchmark Data Contracts) có 2 vấn đề:
- **Dễ quá nếu chỉ benchmark:** Cấu hình dbt + Delta rồi đo → thiếu contribution kỹ thuật
- **Khó quá nếu thêm DataHub:** Docker hell, 8-12GB RAM, mất 3-4 tuần setup

**Giải pháp:** Đổi sang đề tài mà bạn **TỰ XÂY DỰNG** một framework nhỏ — vừa có chiều sâu kỹ thuật, vừa không phụ thuộc tool nặng.

---

## Phân tích từ hướng dẫn GVHD

### Công thức đặt tên (từ ảnh hướng dẫn):
> **MethodName** : Distinctive Property + Architecture **for** Problem **via** Mechanism **under** Challenge

### Ví dụ mẫu GVHD cho Data Engineering:
> *"ContractGuard: Contract-Aware Data Observability Framework for Pipeline Failure Detection via Lineage-Guided Diagnosis under Schema Evolution"*

### Từ "Bản đồ DE 2026" — giao 3 hướng phù hợp nhất:
| Topic | Tag | Vai trò trong đề tài |
|:---|:---|:---|
| **#3 CDC / Incremental** | Ứng dụng thực tế | Source: lấy data thay đổi từ PostgreSQL |
| **#5 Data Contracts** | Lai / Chuyển tiếp | Contract rules: định nghĩa schema + quality |
| **#6 Data Observability** | Ứng dụng thực tế | Monitoring: phát hiện lỗi tự động tại mỗi layer |

### Từ "Lộ trình 3 Paper" cho DE:
- **Paper 1 (Seminar):** Benchmark / Empirical Study → "What is wrong?"
- **Paper 2 (Khóa luận):** Novel Method / Architecture → "How to improve?"
- **Paper 3 (nếu có):** Robustness / Real-world System

### Từ biểu đồ "Nên chọn đề tài nào?":
- **Data Observability** nằm ở vùng **medium difficulty + medium-high research value** = sweet spot cho 8.5+
- Student "muốn sát doanh nghiệp" → chọn **Data Contracts, Observability**

---

## ĐỀ TÀI MỚI — FORM HOÀN CHỈNH

---

# FORM ĐIỀN NHANH THÔNG TIN ĐỀ TÀI

---

**Tên đề tài (VI):**
MedalGuard: Framework phát hiện lỗi dữ liệu sớm trong Medallion Lakehouse thông qua kiểm tra Data Contracts tự động tại ranh giới các tầng dưới thách thức Schema Evolution

---

**Topic title (EN):**
MedalGuard: Early Data Failure Detection Framework for Medallion Lakehouse via Automated Contract Validation at Layer Boundaries under Schema Evolution

---

**Hướng nghiên cứu:** ☑ Data Engineering

**Loại hình:** ☑ Seminar

---

**Nhóm sinh viên:** *(tự điền tên + MSSV)*

---

**Problem:**
Trong Medallion Lakehouse (Bronze → Silver → Gold), khi dữ liệu nguồn từ PostgreSQL thay đổi schema (thêm/xoá cột, đổi kiểu, thay constraint), lỗi có thể lan qua các tầng mà không bị chặn — gọi là **Silent Failures**. Nguyên nhân: không có cơ chế kiểm tra tự động tại ranh giới mỗi tầng (layer boundaries). Hậu quả: dữ liệu lỗi đến Gold layer → báo cáo sai → quyết định sai.

---

**Research Gap:**
Các công cụ hiện tại xử lý data quality ở các tầng riêng lẻ: Delta Lake chặn ở tầng storage, dbt contracts chặn ở tầng transformation, Great Expectations validate ở tầng data quality. Tuy nhiên, **chưa có framework nào tích hợp kiểm tra tự động tại mỗi ranh giới tầng** (Bronze→Silver, Silver→Gold) trong Medallion Lakehouse và đánh giá định lượng mức độ hiệu quả phát hiện lỗi khi schema evolution xảy ra (Wasser et al. 2025, Tagliabue et al. 2026).

---

**Expected Contributions:**

**(1) MedalGuard Framework** (contribution chính):
Xây dựng một Python framework (~300-500 dòng) đặt tại ranh giới mỗi tầng Medallion, tự động:
- Phát hiện schema drift giữa upstream và downstream
- Validate data quality rules (null checks, value ranges, uniqueness)
- Detect semantic anomalies (giá trị thay đổi phân phối bất thường)
- Ghi log violations + tính toán Blast Radius tự động

**(2) Schema Evolution Mutation Suite:**
Thiết kế bộ test 5 loại schema mutation có kiểm soát trên TPC-H:
- Additive (thêm cột mới)
- Destructive (xoá/rename cột)
- Type change (đổi kiểu dữ liệu)
- Constraint breach (vi phạm NOT NULL, CHECK)
- Semantic drift (giá trị đúng kiểu nhưng sai ngữ nghĩa)

**(3) Đánh giá thực nghiệm so sánh 4 cấu hình:**
- Config 0: Không kiểm tra gì (Baseline)
- Config 1: Chỉ dbt contracts (Transform-tier)
- Config 2: Chỉ Great Expectations (Validation-tier)
- Config 3: **MedalGuard** = dbt contracts + GE + schema drift detection (Multi-tier)

**(4) Phân tích định lượng** loại mutation nào gây Silent Failures ở từng config, và MedalGuard cải thiện bao nhiêu %.

---

**Keywords (3–5 từ):**
Medallion Lakehouse, Data Observability, Data Contracts, Schema Evolution, Data Quality

---

**Dataset:**
TPC-H benchmark (public domain, SF=1 ~1GB) + Synthetic Schema Evolution Mutation Suite tự thiết kế

- TPC-H: https://github.com/eyalroz/tpch-dbgen
- Mutation Suite: Python scripts inject 5 loại schema change có kiểm soát

---

**Paper tham khảo:**
1. Jain et al. — *Analyzing and Comparing Lakehouse Storage Systems* (CIDR 2023)
2. Goedegebuure et al. — *Data Mesh: A Systematic Gray Literature Review* (ACM Computing Surveys 2024)
3. Wasser et al. — *Data Contracts in Data Mesh: A Systematic Gray Literature Review* (BMSD 2025)
4. Tagliabue et al. — *Building a Correct-by-Design Lakehouse: Data Contracts, Versioning, and Transactional Pipelines* (arXiv 2026)

---

**GitHub / Baseline:**
- **Pipeline:** dbt-core (github.com/dbt-labs/dbt-core) + dbt-duckdb adapter
- **Database nguồn:** PostgreSQL + TPC-H data
- **Lakehouse:** DuckDB + Delta Lake (delta-rs) — lightweight, local, không cần Spark
- **Data Quality engine:** Great Expectations (github.com/great-expectations/great_expectations) — `pip install` only
- **MedalGuard:** tự xây dựng bằng Python, wrap dbt contracts + Great Expectations + custom schema drift detector

---

**Metric (đánh giá):**

| # | Metric | Mô tả | Cách đo |
|:--|:-------|:------|:--------|
| 1 | **Detection Rate** | % mutations bị phát hiện trước khi dữ liệu lỗi đến Gold layer | Mutations detected / Total mutations injected × 100% |
| 2 | **Blast Radius** | % records lỗi đã lan đến Gold trước khi bị phát hiện | Faulty Gold records / Total injected faulty records × 100% |
| 3 | **Detection Stage** | Lỗi bị bắt ở tầng nào (Bronze→Silver gate hay Silver→Gold gate) | Categorical: B→S / S→G / Not detected |
| 4 | **Pipeline Overhead** | Thời gian chạy pipeline tăng bao nhiêu khi bật MedalGuard | (Time with MedalGuard − Baseline time) / Baseline time × 100% |

---

**Timeline (dự kiến — 15 tuần):**

| Tuần | Giai đoạn | Mục tiêu chính |
|:-----|:----------|:---------------|
| W1–W2 | Research Lock | Lock problem + literature review + thiết kế Mutation Suite + 1-page proposal |
| W3–W4 | Setup & Baseline | PostgreSQL + DuckDB + dbt pipeline Bronze→Silver→Gold chạy end-to-end → **GATE 1** |
| W5–W6 | Config 1 & 2 | Implement dbt contracts + Great Expectations riêng lẻ, chạy thử với vài mutations |
| W7–W9 | **Build MedalGuard** | Xây dựng framework: schema drift detector + contract validator + violation logger |
| W10–W11 | Full Experiments | Chạy full matrix: 5 mutation types × 4 configs, thu thập 4 metrics |
| W12–W13 | Phân tích + Viết báo cáo | Phân tích kết quả, vẽ charts, viết draft report |
| W14 | Review + Chỉnh sửa | Chỉnh sửa theo feedback GV |
| W15 | Thuyết trình | Slide + bảo vệ |

**Fallback Plan:**
- Nếu Great Expectations phức tạp → thay bằng Soda Core (nhẹ hơn, cùng chức năng)
- Nếu thiếu thời gian → giảm configs từ 4 xuống 3 (bỏ Config 2), giảm mutations từ 5 xuống 3

---

**Hướng mở rộng cho Khóa luận (kỳ sau):**
- Thêm CDC real-time từ PostgreSQL (dùng logical replication hoặc Debezium)
- MedalGuard tự động suggest sửa lỗi (self-healing: auto-cast type, fill NULL defaults)
- Thêm lineage tracking: khi lỗi bị phát hiện → trace ngược lại source table + column
- Tích hợp alerting (Slack/Email notification khi contract bị vi phạm)

---

## TẠI SAO ĐỀ TÀI NÀY TỐT NHẤT CHO BẠN?

### ✅ Đối chiếu với Checklist GV (10 điểm):

| Tiêu chí | Điểm tối đa | Đánh giá | Lý do |
|:---|:---:|:---:|:---|
| **Problem** | 2đ | ✅ 2đ | Silent Failures trong Lakehouse — rõ, thực tế, ai cũng hiểu |
| **Contribution** | 2đ | ✅ 2đ | **Tự xây MedalGuard** (không chỉ chạy tool) + Mutation Suite + 4 configs so sánh |
| **Method** | 2đ | ✅ 1.5–2đ | Multi-tier validation framework + controlled experiment |
| **Setting** | 1đ | ✅ 1đ | TPC-H public domain + PostgreSQL + DuckDB + dbt |
| **Quality** | 1đ | ✅ 1đ | 4 metrics định lượng rõ ràng, 5×4 experiment matrix |
| **Memorable** | 1đ | ✅ 1đ | "MedalGuard" — có tên riêng, theo đúng công thức GV |
| **No Overclaim** | 1đ | ✅ 1đ | Framework nhỏ ~300-500 LOC, không claim là "revolutionary" |
| **TỔNG** | **10đ** | **~8.5–9.5đ** | |

### ✅ Đối chiếu với yêu cầu của bạn:

| Yêu cầu | Đáp ứng? | Chi tiết |
|:---|:---:|:---|
| Muốn làm database | ✅ | PostgreSQL là source chính, xây enforcement logic = kỹ năng DB engineer |
| Điểm ≥ 8.5 | ✅ | Có MethodName + tự build + metrics rõ → GV đánh giá cao |
| 1 mình làm được | ✅ | Python + SQL + dbt + `pip install`, không Docker nặng, không GPU |
| Không quá dễ | ✅ | Tự xây framework ~300-500 dòng, thiết kế experiment, phân tích kết quả |
| Không quá khó | ✅ | Không ML/DL, không Kafka, không Spark, không Docker phức tạp |
| Seminar → Khóa luận | ✅ | Seminar = benchmark + build MedalGuard v1; Khóa luận = thêm CDC + self-healing |

### ✅ Khớp với ví dụ mẫu DE của GVHD:

| Thành phần công thức | Ví dụ mẫu GVHD | Đề tài của bạn |
|:---|:---|:---|
| **MethodName** | ContractGuard | **MedalGuard** |
| **Property** | Contract-Aware | Contract-Aware |
| **Architecture** | Data Observability Framework | **Medallion Lakehouse Framework** |
| **Problem** | Pipeline Failure Detection | **Early Data Failure Detection** |
| **Mechanism** | Lineage-Guided Diagnosis | **Automated Contract Validation at Layer Boundaries** |
| **Challenge** | Schema Evolution | **Schema Evolution** |

→ Cấu trúc hoàn toàn khớp với kỳ vọng GVHD, nhưng tên khác nên không bị trùng.

### ✅ Lộ trình Paper 1 → 2 → 3:

```
Paper 1 (Seminar): Benchmark — "MedalGuard phát hiện được bao nhiêu % lỗi?"
    ↓
Paper 2 (Khóa luận): Novel Method — "MedalGuard + CDC real-time + Self-Healing"
    ↓  
Paper 3 (nếu muốn): Real-world — "MedalGuard trên production data thật"
```

---

## MedalGuard TRÔNG NHƯ THẾ NÀO?

```
PostgreSQL (TPC-H)
    │
    ▼
┌─────────────────────────┐
│     BRONZE LAYER        │  ← Raw data ingested
│   (DuckDB / Delta)      │
└─────────┬───────────────┘
          │
    ┌─────▼─────┐
    │ MedalGuard │  ← Gate 1: Schema drift check + null/type validation
    │  B → S     │
    └─────┬─────┘
          │ PASS ✅ / BLOCK ❌
          ▼
┌─────────────────────────┐
│     SILVER LAYER        │  ← Cleaned, conformed data (dbt models)
│   (dbt contracts)       │
└─────────┬───────────────┘
          │
    ┌─────▼─────┐
    │ MedalGuard │  ← Gate 2: Business rules + semantic checks + anomaly detection
    │  S → G     │
    └─────┬─────┘
          │ PASS ✅ / BLOCK ❌
          ▼
┌─────────────────────────┐
│      GOLD LAYER         │  ← Business-ready aggregates
│   (dbt models)          │
└─────────────────────────┘
          │
          ▼
    📊 Violation Report
    - Mutation type detected
    - Layer where caught
    - Blast Radius
    - Records affected
```

### Code MedalGuard (sketch — ~300-500 dòng Python):

```python
# medalguard/gate.py
class MedalGuard:
    def __init__(self, contract_path: str):
        self.contract = load_yaml(contract_path)  # Schema + rules
    
    def validate(self, upstream_df, downstream_df) -> ValidationReport:
        violations = []
        
        # 1. Schema Drift Detection
        violations += self.check_schema_drift(upstream_df, downstream_df)
        
        # 2. Data Type Validation
        violations += self.check_data_types(downstream_df)
        
        # 3. Constraint Checks (NOT NULL, ranges, allowed values)
        violations += self.check_constraints(downstream_df)
        
        # 4. Semantic Anomaly Detection (distribution shift)
        violations += self.check_semantic_drift(upstream_df, downstream_df)
        
        # 5. Calculate Blast Radius
        blast_radius = self.calculate_blast_radius(violations, downstream_df)
        
        return ValidationReport(
            passed=len(violations) == 0,
            violations=violations,
            blast_radius=blast_radius,
            detection_stage=self.layer_name
        )
```

```yaml
# contracts/silver_orders.yaml
table: silver_orders
source: bronze_orders
columns:
  - name: o_orderkey
    type: INTEGER
    not_null: true
    unique: true
  - name: o_totalprice
    type: DECIMAL(15,2)
    constraints:
      - "value >= 0"
  - name: o_orderstatus
    type: VARCHAR(1)
    allowed_values: ["O", "F", "P"]
quality_rules:
  - "null_rate(o_custkey) < 0.01"
  - "row_count > 0"
  - "mean(o_totalprice) BETWEEN 100 AND 500000"
```

→ Bạn viết code Python thật, validate data thật, ra kết quả thật. GV thấy **bạn hiểu và tự xây** chứ không chỉ cấu hình tool.
