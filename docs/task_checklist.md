# MedalGuard — Task Tracking

## GATE 1 (Cuối Week 4)
- [x] Git repo có README
- [x] DuckDB + TPC-H data (source schema)
- [x] dbt pipeline: bronze -> silver -> gold chạy end-to-end
- [x] Query Gold tables ra kết quả đúng

## GATE 2 (Cuối Week 8)
- [x] Config C1 (dbt contracts) hoạt động
- [x] Config C2 (Great Expectations) hoạt động
- [x] MedalGuard framework (gate.py + 3 validators) hoạt động
- [x] Test thử với 1-2 mutations -> detect đúng

## GATE 3 (Cuối Week 11)
- [x] 5 loại Mutation implement xong (mở rộng lên 36 kịch bản v2)
- [x] 20+ experiments chạy xong (180 runs E1 + 168 runs E2 + 64 runs E3)
- [x] 4 metrics thu thập xong (DR, FPR, Blast Radius, DDI + DE SLA metrics)
- [x] Summary table hoàn chỉnh (Core 19 & Expanded 36)

## PHASE 2 — GVHD IMPROVEMENTS (HOÀN TẤT 100%)
- [x] CT1: Ngôn ngữ hợp đồng YAML đa tầng & Bộ 36 kịch bản đột biến (24 Harmful + 12 Benign)
- [x] CT2: In-line Dual-Boundary Gate (Pre-transform Gate 1 & Post-transform Gate 2) + Staged In-place Quarantine
- [x] CT3: Multi-hop Data Lineage, Root-Cause Diff, LKG Gold Rollback (51.9ms), Replay/Backfill Engine, Alerting & Web Console
- [x] E1: Ma trận so sánh chính (Core 19 & Expanded 36) với 95% Wilson & Bootstrap CI, McNemar exact tests
- [x] E2: Nghiên cứu triệt tiêu 2 trục (Validator Ablation A1..A6 & Boundary Placement B1, B2, C3_DUAL)
- [x] E3: Đánh giá chi phí & năng lực co giãn (SF=0.1 vs SF=1.0, Stress test ~7.65M records, mô hình $T(SF)$)
- [x] E4: Báo cáo phân tích lỗi & Đánh đổi chất lượng - chi phí - độ trễ
- [x] E5: Hồ sơ tái lập thực nghiệm chuẩn khoa học
- [x] 6 Biểu đồ khoa học 300 DPI (`fig1` đến `fig6`)
- [x] Tích hợp Automated Pytest Suite & Pre-flight Contract Validator CLI

## FINAL (Week 15)
- [ ] Báo cáo Seminar (~15-25 trang)
- [ ] Slide thuyết trình (15-20 slides)
- [x] Code repo clean, có README hướng dẫn reproduce
- [x] Results + charts trong thư mục results/

---

## Chi tiết theo tuần

### Week 1 (14/09 – 20/09): Research Lock
- [x] Đọc Paper 1: Jain et al. (CIDR 2023)
- [x] Đọc Paper 2: Goedegebuure et al. (ACM 2024)
- [x] Đọc Paper 3: Wasser et al. (BMSD 2025)
- [x] Đọc Paper 4: Tagliabue et al. (arXiv 2026)
- [x] Viết 1-page proposal

### Week 2 (21/09 – 27/09): Thiết kế
- [x] Nghiên cứu TPC-H schema, vẽ ER diagram
- [x] Thiết kế 5 loại mutation
- [x] Viết contract YAML Gate 1 (bronze -> silver)
- [x] Viết contract YAML Gate 2 (silver -> gold)

### Week 3 (28/09 – 04/10): Setup Environment
- [x] Tạo repo Git + cấu trúc thư mục
- [x] Cài Python venv + dependencies
- [x] Setup dbt_project.yml + profiles.yml
- [x] Viết script sinh TPC-H data
- [x] Viết dbt Bronze models
- [x] Chạy dbt run lần đầu

### Week 4 (05/10 – 11/10): Pipeline end-to-end
- [x] Viết dbt Silver models
- [x] Viết dbt Gold models
- [x] Chạy full pipeline bronze -> silver -> gold
- [x] Verify Gold data
- [x] **GATE 1 CHECKPOINT**

### Week 5 (12/10 – 18/10): Config C1 — dbt contracts
- [x] Thêm contract definitions vào _silver_models.yml
- [x] Test với dữ liệu sạch
- [x] Test với 1 lỗi thủ công (xóa cột)
- [x] Test với 1 lỗi type mismatch
- [x] Ghi chú: dbt bắt/bỏ sót loại nào

### Week 6 (19/10 – 25/10): Config C2 — Great Expectations
- [x] Setup GX context + DuckDB connection
- [x] Viết expectation suite cho silver_orders
- [x] Viết expectation suite cho silver_lineitem
- [x] Test với dữ liệu sạch
- [x] Test với 1 lỗi thủ công
- [x] So sánh sơ bộ dbt vs GX

### Week 7 (26/10 – 01/11): MedalGuard core (phần 1)
- [x] config.py: load contract YAML
- [x] schema_validator.py: schema drift detection
- [x] constraint_validator.py: NOT NULL, type, range, allowed values

### Week 8 (02/11 – 08/11): MedalGuard core (phần 2)
- [x] semantic_validator.py: distribution / mean drift
- [x] reporter.py: violation log + blast radius
- [x] gate.py: ContractGate class tích hợp
- [x] Test end-to-end với clean + dirty data
- [x] **GATE 2 CHECKPOINT**

### Week 9 (09/11 – 15/11): Mutation Suite
- [x] base.py: BaseMutation class
- [x] m1_additive.py
- [x] m2_destructive.py
- [x] m3_type_change.py
- [x] m4_constraint_breach.py
- [x] m5_semantic_drift.py
- [x] experiments/runner.py

### Week 10 (16/11 – 22/11): Experiments (phần 1)
- [x] matrix_runner.py & run_phase2_experiments.py
- [x] M1 x 4 configs (E01–E04)
- [x] M2 x 4 configs (E05–E08)
- [x] M3 x 4 configs (E09–E12)

### Week 11 (23/11 – 29/11): Experiments (phần 2)
- [x] M4 x 4 configs (E13–E16)
- [x] M5 x 4 configs (E17–E20)
- [x] Mở rộng 36 kịch bản v2
- [x] Tổng hợp summary table E1, E2, E3
- [x] **GATE 3 CHECKPOINT**

### Week 12 (30/11 – 06/12): Phân tích & Hình ảnh Hóa
- [x] visualize_phase2.py xuất 6 biểu đồ 300 DPI
- [x] Phân tích E4 Error Analysis & Quality-Latency-Cost trade-offs
- [x] Hồ sơ tái lập E5 Reproducibility

### Week 13 (07/12 – 13/12): Viết báo cáo
- [ ] Soạn thảo bản thảo báo cáo Seminar theo cấu trúc 7 chương
- [ ] Gửi draft cho GV review

### Week 14 (14/12 – 20/12): Chỉnh sửa & Đánh bóng
- [x] Nhận feedback cải tiến GVHD & hoàn tất Phase 2
- [x] Clean up code repo, tích hợp Automated Pytest suite

### Week 15 (21/12 – 28/12): Thuyết trình
- [ ] Làm slide (15-20 slides)
- [ ] Tập thuyết trình
- [ ] Bảo vệ Seminar
