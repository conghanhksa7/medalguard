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
- [ ] 5 loại Mutation implement xong
- [ ] 20 experiments chạy xong
- [ ] 4 metrics thu thập xong
- [ ] Summary table hoàn chỉnh

## FINAL (Week 15)
- [ ] Báo cáo Seminar (~13-15 trang)
- [ ] Slide thuyết trình (15-20 slides)
- [ ] Code repo clean, có README hướng dẫn reproduce
- [ ] Results + charts trong thư mục results/

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
- [ ] matrix_runner.py
- [ ] M1 x 4 configs (E01–E04)
- [ ] M2 x 4 configs (E05–E08)
- [ ] M3 x 4 configs (E09–E12)

### Week 11 (23/11 – 29/11): Experiments (phần 2)
- [ ] M4 x 4 configs (E13–E16)
- [ ] M5 x 4 configs (E17–E20)
- [ ] Re-run nếu cần
- [ ] Tổng hợp summary table
- [ ] **GATE 3 CHECKPOINT**

### Week 12 (30/11 – 06/12): Phân tích
- [ ] analyzer.py + visualizer.py
- [ ] Vẽ charts (bar, heatmap, stacked bar)
- [ ] Viết Introduction + Related Work

### Week 13 (07/12 – 13/12): Viết báo cáo
- [ ] Viết Methodology
- [ ] Viết Results + Discussion
- [ ] Viết Conclusion + Future Work
- [ ] Gửi draft cho GV review

### Week 14 (14/12 – 20/12): Chỉnh sửa
- [ ] Nhận feedback GV
- [ ] Chỉnh sửa báo cáo
- [ ] Clean up code repo

### Week 15 (21/12 – 28/12): Thuyết trình
- [ ] Làm slide (15-20 slides)
- [ ] Tập thuyết trình
- [ ] Bảo vệ Seminar
