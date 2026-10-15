# Phân tích tài liệu GVHD: Metrics Measurement

## Tài liệu GVHD cung cấp gì?

### 1. Infographic DE Metrics (DE Metrics.png)

GVHD cung cấp **6 bước tiến hành đánh giá** chuẩn cho tất cả đề tài DE:

```
B1. Xác định Property cần chứng minh
B2. Chuẩn bị dữ liệu đánh giá
B3. Chọn baseline
B4. Chạy ablation
B5. Stress test
B6. Báo cáo trade-off
```

**5 Property** mà GV yêu cầu đo cho DE:

| Property | Metrics | "Tốt khi nào?" |
|:---|:---|:---|
| **Reliability** | Pipeline success rate, SLA attainment, MTBF | SLA cao, ít lỗi lặp lại |
| **Data Quality** | Completeness, accuracy, validity, duplication rate | Tỷ lệ lỗi thấp |
| **Scalability / Throughput** | Rows/s, job duration, resource utilization | Thông lượng cao, thời gian job hợp lý |
| **Freshness / Timeliness** | Data latency, end-to-end delay | Độ trễ thấp |
| **Observability / Recoverability** | MTTD, MTTR, lineage coverage, alert precision | MTTD/MTTR thấp, cảnh báo đúng |

**Mốc tham khảo cho bài nghiên cứu tốt (DE):**
1. Pipeline success rate / SLA cao hơn baseline khoảng **3-10%**
2. MTTD / MTTR giảm rõ, phục hồi nhanh hơn baseline
3. Data latency thấp hơn và freshness ổn định hơn
4. Tỷ lệ lỗi, thiếu hoặc trùng lặp ở mức rất thấp
5. Thông lượng giữ tốt khi tăng volume hoặc stream rate
6. **Phải có error analysis và ví dụ failure / recovery đi kèm**

**Khung báo cáo kết quả 5 phần:**
```
1. Mục tiêu & property
2. Pipeline / data & baseline
3. Metric chính + metric phụ
4. Ablation / failure injection / error analysis
5. Kết luận contribution & trade-off
```

### 2. File Docx — Phần riêng cho MedalGuard (#12)

GVHD đã viết **chi tiết riêng cho đề tài MedalGuard** (mục 12 trong 16 đề tài):

#### A. Thứ tự thực hiện (GV yêu cầu):
1. Dựng TPC-H Bronze→Silver→Gold baseline không contract
2. Định nghĩa contract per boundary: schema, type, nullability, ranges, **key/reference, semantic checks**
3. Xây mutation suite 5 loại + **ground-truth expected behavior**
4. Implement dbt contracts và Great Expectations làm baselines
5. Xây MedalGuard multi-tier gate với **quarantine + error report + lineage**
6. Chạy ma trận 5 mutation × 4 configs × **nhiều seed/volume**
7. Đo **detection stage, time-to-detect, blast radius** và overhead
8. **Ablation rule types/placement**; phân tích mutation nào khó nhất; **đóng gói framework tái lập**

#### B. Đề xuất nghiên cứu mạnh hơn (GV gợi ý):
> - **Blast Radius** là metric rất mạnh, nên định nghĩa bằng **record/partition bị nhiễm TRƯỚC khi chặn**
> - Thêm **Time-to-Detect** để phản ánh "early" trong title
> - Tạo **contract versioning** để xử lý additive schema evolution hợp lệ (KHÔNG coi mọi thay đổi là lỗi)
> - Chạy dataset scale **> SF1** nếu tài nguyên cho phép để test overhead
> - Báo cáo **precision (false positive rate)** của gate để tránh contract quá chặt gây false alarm

#### C. Metrics cần đo (TABLE 13):

| Metric | Đo điều gì | Target gợi ý | Vai trò |
|:---|:---|:---|:---|
| **Detection Rate** | % mutation nguy hiểm bị phát hiện | **≥ 95%; stretch 100%** trên known mutations | **Metric chính** |
| **Blast Radius** | % bad records đến Gold | **≤ 1-5%**; baseline cao hơn rõ rệt | |
| **Detection Stage** | Tỷ lệ bắt ở gate sớm nhất | **≥ 90%** tại Bronze→Silver khi có thể | |
| **False Positive Rate** | Thay đổi hợp lệ bị chặn | **≤ 2-5%** | |
| **Time-to-Detect** | Từ mutation đến alert/block | Gần 1 pipeline stage; càng thấp càng tốt | |
| **Pipeline Overhead** | Runtime tăng thêm | **< 10-15%** | |
| **Recovery Success** | Quarantine/fix rồi resume | **≥ 95%** test incidents | |

#### D. Thiết kế thực nghiệm tối thiểu:
- Baseline tái lập được và lưu cấu hình/seed/version
- Proposed method chạy trên cùng split/hardware/protocol với baseline
- **Ít nhất 1 ablation** chứng minh thành phần mới có đóng góp
- **Ít nhất 1 stress/robustness test** đúng "Challenge" trong title
- Báo cáo **mean ± std** hoặc confidence interval; kèm **error/failure analysis**

---

## Đối chiếu với plan hiện tại

| Yêu cầu GV | Plan hiện tại | Trạng thái |
|:---|:---|:---:|
| Detection Rate ≥ 95% | Có (4 metrics) | ✅ |
| Blast Radius ≤ 1-5% | Có | ✅ |
| Detection Stage ≥ 90% B→S | Có | ✅ |
| Pipeline Overhead < 10-15% | Có | ✅ |
| **False Positive Rate ≤ 2-5%** | **THIẾU** | ❌ |
| **Time-to-Detect** | **THIẾU** | ❌ |
| **Recovery Success ≥ 95%** | **THIẾU** | ❌ |
| **Quarantine mechanism** | **THIẾU** (chỉ có log_only/block) | ❌ |
| **Contract versioning** | **THIẾU** | ❌ |
| **Ablation study** | **THIẾU** | ❌ |
| **Stress test (SF > 1)** | Nhắc sơ ở risk table | ⚠️ |
| **Ground-truth expected behavior** | Có dự đoán nhưng chưa formalize | ⚠️ |
| **Error/failure analysis** | Chưa có | ❌ |
| **mean ± std / CI** | Chỉ nói median, chưa nói std | ⚠️ |
| Nhiều seed/volume | Chỉ nói repeat_count=3 | ⚠️ |
| Khung báo cáo 5 phần | Chưa khớp 100% | ⚠️ |

---

## Đề xuất bổ sung vào plan

### Bổ sung #1: Thêm 3 Metrics mới

**False Positive Rate (FPR)**
```
FPR = (Số lần thay đổi HỢP LỆ bị gate chặn) / (Tổng thay đổi hợp lệ) × 100%
```
Cần tạo thêm **2-3 "benign mutations"** (thay đổi hợp lệ) để test:
- B1: Thêm cột comment mới (additive, hợp lệ) — gate nên KHÔNG chặn
- B2: Thay đổi giá trị trong phạm vi cho phép (discount 0.05 → 0.08) — gate nên KHÔNG chặn
- B3: Thêm record mới (insert thêm orders) — gate nên KHÔNG chặn

Target: FPR ≤ 2-5%

**Time-to-Detect (TTD)**
```
TTD = timestamp(first_violation_detected) - timestamp(mutation_applied)
```
Đo bằng đơn vị "pipeline stages" (0 = ngay lập tức, 1 = sau Bronze, 2 = sau Silver)
- Target: TTD gần 1 stage (B→S) cho hầu hết mutations

**Recovery Success Rate**
```
Recovery = (Số incidents pipeline recover thành công sau quarantine) / (Tổng incidents) × 100%
```
Target: ≥ 95%

### Bổ sung #2: Quarantine Mechanism

GV yêu cầu MedalGuard có **quarantine** (cách ly data lỗi), không chỉ log hoặc block.

Cần thêm vào MedalGuard:
```python
# medalguard/gate.py - thêm mode "quarantine"
class ContractGate:
    def __init__(self, ..., mode="log_only"):
        # mode: "log_only" | "block" | "quarantine"
        ...
    
    def validate(self, source_table, target_table):
        ...
        if self.mode == "quarantine" and not result.passed:
            # Tách data lỗi ra bảng riêng, cho phần tốt đi tiếp
            self._quarantine_bad_records(violations, target_table)
```

Flow:
```
Mutation → Bronze → MedalGuard Gate 1:
  ├── Records tốt → Silver → Gold (pipeline tiếp tục)
  └── Records lỗi → quarantine.silver_orders_rejected (cách ly)
```

### Bổ sung #3: Contract Versioning

GV nhấn mạnh: additive schema evolution (thêm cột mới) có thể **hợp lệ**, không nên coi là lỗi.

Cần thêm:
```yaml
# contracts/bronze_to_silver/orders.yaml
version: 2  # Contract version
strict_columns: false  # false = cho phép thêm cột mới (additive ok)
                        # true = chặn mọi thay đổi schema
```

Khi `strict_columns: false`:
- Thêm cột mới → **PASS** (không phải violation)
- Xóa cột có trong contract → **FAIL** (destructive)
- Đổi type → **FAIL**

### Bổ sung #4: Ablation Study (BẮT BUỘC theo GV)

Thêm ma trận ablation: bỏ từng loại validator để xem đóng góp:

| Ablation | Schema Validator | Constraint Validator | Semantic Validator |
|:---|:---:|:---:|:---:|
| Full MedalGuard (C3) | ✅ | ✅ | ✅ |
| A1: No Schema | ❌ | ✅ | ✅ |
| A2: No Constraint | ✅ | ❌ | ✅ |
| A3: No Semantic | ✅ | ✅ | ❌ |
| A4: Schema Only | ✅ | ❌ | ❌ |

Mỗi ablation chạy 5 mutations → 5×5 = 25 experiments thêm.
Tổng: 20 (ma trận chính) + 25 (ablation) = **45 experiments**.

> [!IMPORTANT]
> GV nói rõ: "Ít nhất 1 ablation chứng minh thành phần mới có đóng góp." Đây là **bắt buộc**.

### Bổ sung #5: Stress Test

Thêm stress test chạy ở **nhiều scale factor**:

| Scale Factor | Dữ liệu | Mục đích |
|:---|:---|:---|
| SF=0.1 | ~100MB | Development & debug |
| SF=1 | ~1GB | Main experiments |
| SF=10 | ~10GB | Stress test overhead (nếu tài nguyên cho phép) |

Báo cáo overhead scaling: overhead có tăng tuyến tính, sublinear, hay superlinear theo data size?

### Bổ sung #6: Ground-truth Expected Behavior

Tạo file `mutations/ground_truth.yaml` ghi rõ kết quả kỳ vọng cho mỗi mutation × config:

```yaml
# mutations/ground_truth.yaml
M1_ADDITIVE:
  expected:
    C0: {detected: false, blast_radius: 0.0, detection_stage: "NOT_DETECTED"}
    C1: {detected: true, blast_radius: 0.0, detection_stage: "B->S"}
    C2: {detected: false, blast_radius: 0.0, detection_stage: "NOT_DETECTED"}
    C3: {detected: true, blast_radius: 0.0, detection_stage: "B->S"}
  note: "Additive mutation chỉ bị bắt bởi schema validator (strict mode)"
```

Experiment runner sẽ so sánh actual vs expected → tự động flag bất ngờ.

### Bổ sung #7: Error/Failure Analysis

GV yêu cầu: "kèm error/failure analysis". Thêm phần này vào report:

- Liệt kê mutations mà MedalGuard **KHÔNG bắt được** (nếu có)
- Phân tích **tại sao** không bắt (gap analysis)
- Liệt kê **false positives** (benign mutations bị chặn nhầm)
- Phân tích root cause của false positives

### Bổ sung #8: Cấu trúc báo cáo theo khung GV

Chỉnh cấu trúc báo cáo cho khớp khung 5 phần của GV:

```
1. Mục tiêu & Property (1.5 trang)
   - Problem statement
   - Properties cần chứng minh: Data Quality, Reliability, Observability
   - Research Questions (RQ1, RQ2, RQ3)

2. Pipeline / Data & Baseline (2 trang)
   - TPC-H dataset
   - Medallion pipeline architecture
   - Baseline: C0 (no check), C1 (dbt), C2 (GX)

3. Metric chính + Metric phụ (1 trang)
   - Chính: Detection Rate, Blast Radius
   - Phụ: Detection Stage, FPR, TTD, Pipeline Overhead, Recovery

4. Ablation / Failure Injection / Error Analysis (4-5 trang)
   - 4.1 Main Results: 5×4 matrix
   - 4.2 Ablation: bỏ từng validator
   - 4.3 Stress test: SF scaling
   - 4.4 Error Analysis: false positives, undetected mutations

5. Kết luận Contribution & Trade-off (1.5 trang)
   - Contribution: multi-tier tốt hơn single-tier bao nhiêu %
   - Trade-off: overhead vs detection
   - Future work: CDC, self-healing, lineage
```

---

## Tóm tắt

| Hạng mục | Plan cũ | Plan mới (sau bổ sung) |
|:---|:---:|:---:|
| Metrics | 4 | **7** (+FPR, TTD, Recovery) |
| Experiments (main) | 20 | 20 |
| Experiments (ablation) | 0 | **25** |
| Experiments (benign) | 0 | **~12** (3 benign × 4 configs) |
| Stress test | Nhắc sơ | **SF=0.1, 1, 10** |
| Quarantine | Không | **Có** |
| Contract versioning | Không | **Có** |
| Ground truth file | Không | **Có** |
| Error analysis | Không | **Có** |
| Tổng experiments | 20 | **~57** |
