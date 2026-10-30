# BẢNG KẾT QUẢ THỰC NGHIỆM E1: MA TRẬN SO SÁNH ĐA CẤU HÌNH
**Quy mô thực nghiệm:** TPC-H SF=0.1 (150,000 dòng `lineitem`), 5 cấu hình (`C0, C1, C2, C3_standalone, C3`).
**Phương pháp thống kê:** Khoảng tin cậy 95% Wilson Score (Tỷ lệ phát hiện & Dương tính giả), 95% Non-parametric Bootstrap CI (2,000 resamples cho Blast Radius & Paired Diff), và McNemar's Exact Binomial Test đối chiếu cặp từng kịch bản đột biến.

## 1. Kết Quả Thực Nghiệm Tập Core 19 (14 Harmful + 5 Benign = 95 Runs)
| Cấu hình | Mô tả cơ chế | DR % (95% CI) | FPR % (95% CI) | Mean Blast Radius % (95% CI) | ΔBR vs C3 (95% CI) | McNemar *p* (vs C3) | Core Exec (ms) | Ingest Correctness | SLA Attainment |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0** | C0 | **0.0%** [0.0%, 21.5%] | 0.0% [0.0%, 43.5%] | **14.8%** [1.1%, 33.8%] | +8.3% [0.6%, 22.1%] | < 0.001 | 1376.4 | 52.6% | 26.3% |
| **C1** | C1 | **42.9%** [21.4%, 67.4%] | 0.0% [0.0%, 43.5%] | **13.6%** [0.0%, 32.9%] | +7.0% [0.0%, 20.6%] | 0.0156 | 1778.4 | 84.2% | 26.3% |
| **C2** | C2 | **35.7%** [16.3%, 61.2%] | 0.0% [0.0%, 43.5%] | **6.6%** [0.0%, 19.7%] | +0.0% [0.0%, 0.0%] | 0.0078 | 1286.6 | 79.0% | 26.3% |
| **C3_standalone** | C3_standalone | **92.9%** [68.5%, 98.7%] | 0.0% [0.0%, 43.5%] | **6.6%** [0.0%, 19.7%] | +0.0% [0.0%, 0.0%] | 1.0000 | 1305.0 | 94.7% | 94.7% |
| **C3** | C3 | **92.9%** [68.5%, 98.7%] | 0.0% [0.0%, 43.5%] | **6.6%** [0.0%, 19.7%] | — (Baseline Ref) | — | 1343.3 | 94.7% | 94.7% |

## 2. Kết Quả Thực Nghiệm Tập Mở Rộng Expanded 36 (24 Harmful + 12 Benign = 180 Runs)
| Cấu hình | Mô tả cơ chế | DR % (95% CI) | FPR % (95% CI) | Mean Blast Radius % (95% CI) | ΔBR vs C3 (95% CI) | McNemar *p* (vs C3) | Core Exec (ms) | Ingest Correctness | SLA Attainment |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0** | C0 | **0.0%** [0.0%, 13.8%] | 0.0% [0.0%, 24.2%] | **9.6%** [1.1%, 21.0%] | +5.8% [0.5%, 14.4%] | < 0.001 | 1386.7 | 66.7% | 33.3% |
| **C1** | C1 | **41.7%** [24.5%, 61.2%] | 0.0% [0.0%, 24.2%] | **7.9%** [0.0%, 19.4%] | +4.1% [0.0%, 12.0%] | < 0.001 | 1739.3 | 91.7% | 33.3% |
| **C2** | C2 | **37.5%** [21.2%, 57.3%] | 0.0% [0.0%, 24.2%] | **3.8%** [0.0%, 11.5%] | +0.0% [0.0%, 0.0%] | < 0.001 | 1307.5 | 83.3% | 33.3% |
| **C3_standalone** | C3_standalone | **95.8%** [79.8%, 99.3%] | 0.0% [0.0%, 24.2%] | **3.8%** [0.0%, 11.5%] | +0.0% [0.0%, 0.0%] | 1.0000 | 1329.8 | 97.2% | 97.2% |
| **C3** | C3 | **95.8%** [79.8%, 99.3%] | 0.0% [0.0%, 24.2%] | **3.8%** [0.0%, 11.5%] | — (Baseline Ref) | — | 1375.6 | 97.2% | 97.2% |

## 3. Phân Tích Tỷ Lệ Phát Hiện Theo Mức Độ Nghiêm Trọng (Severity Breakdown - 24 Harmful Scenarios)
| Mức độ Nghiêm trọng | Số kịch bản | C0 (Baseline) | C1 (dbt Contracts) | C2 (Great Expectations) | C3_standalone (MedalGuard Standalone) | C3 (MedalGuard In-line) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CRITICAL** | 8 | 0.0% (0/8) | 75.0% (6/8) | 25.0% (2/8) | 100.0% (8/8) | **100.0% (8/8)** |
| **HIGH** | 10 | 0.0% (0/10) | 30.0% (3/10) | 50.0% (5/10) | 90.0% (9/10) | **90.0% (9/10)** |
| **MEDIUM** | 6 | 0.0% (0/6) | 16.7% (1/6) | 33.3% (2/6) | 100.0% (6/6) | **100.0% (6/6)** |

## 4. Bộ Chỉ Số Chất Lượng Kỹ Thuật Dữ Liệu (Data Engineering SLA & Quality Indices)
| Cấu hình | Độ hoàn thiện (Completeness %) | Độ hợp lệ (Validity %) | Tỷ lệ trùng lặp (Duplication %) | Ingest Correctness | SLA Attainment Rate | Hiệu quả cách ly (QE %) | Recall cách ly (QR %) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0** | 86.11% | 79.70% | 0.00% | **66.7%** | **33.3%** | **N/A** | **N/A** |
| **C1** | 72.22% | 94.71% | 0.00% | **91.7%** | **33.3%** | **N/A** | **N/A** |
| **C2** | 86.11% | 83.55% | 0.00% | **83.3%** | **33.3%** | **N/A** | **N/A** |
| **C3_standalone** | 99.98% | 97.44% | 0.00% | **97.2%** | **97.2%** | **100.0%** | **100.0%** |
| **C3** | 99.98% | 97.44% | 0.00% | **97.2%** | **97.2%** | **100.0%** | **100.0%** |
