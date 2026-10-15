# MedalGuard — Task Tracking

## GATE 1 (Cuối Week 4)
- [ ] Git repo có README
- [ ] DuckDB + TPC-H data (source schema)
- [ ] dbt pipeline: bronze -> silver -> gold chạy end-to-end
- [ ] Query Gold tables ra kết quả đúng

## GATE 2 (Cuối Week 8)
- [ ] Config C1 (dbt contracts) hoạt động
- [ ] Config C2 (Great Expectations) hoạt động
- [ ] MedalGuard framework (gate.py + 3 validators) hoạt động
- [ ] Test thử với 1-2 mutations -> detect đúng

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
- [ ] Đọc Paper 1: Jain et al. (CIDR 2023)
- [ ] Đọc Paper 2: Goedegebuure et al. (ACM 2024)
- [ ] Đọc Paper 3: Wasser et al. (BMSD 2025)
- [ ] Đọc Paper 4: Tagliabue et al. (arXiv 2026)
- [ ] Viết 1-page proposal

### Week 2 (21/09 – 27/09): Thiết kế
- [ ] Nghiên cứu TPC-H schema, vẽ ER diagram
- [ ] Thiết kế 5 loại mutation
- [ ] Viết contract YAML Gate 1 (bronze -> silver)
- [ ] Viết contract YAML Gate 2 (silver -> gold)

### Week 3 (28/09 – 04/10): Setup Environment
- [x] Tạo repo Git + cấu trúc thư mục
- [x] Cài Python venv + dependencies
- [x] Setup dbt_project.yml + profiles.yml
- [x] Viết script sinh TPC-H data
- [x] Viết dbt Bronze models
- [ ] Chạy dbt run lần đầu

### Week 4 (05/10 – 11/10): Pipeline end-to-end
- [ ] Viết dbt Silver models
- [ ] Viết dbt Gold models
- [ ] Chạy full pipeline bronze -> silver -> gold
- [ ] Verify Gold data
- [ ] **GATE 1 CHECKPOINT**

### Week 5 (12/10 – 18/10): Config C1 — dbt contracts
- [ ] Thêm contract definitions vào _silver_models.yml
- [ ] Test với dữ liệu sạch
- [ ] Test với 1 lỗi thủ công (xóa cột)
- [ ] Test với 1 lỗi type mismatch
- [ ] Ghi chú: dbt bắt/bỏ sót loại nào

### Week 6 (19/10 – 25/10): Config C2 — Great Expectations
- [ ] Setup GX context + DuckDB connection
- [ ] Viết expectation suite cho silver_orders
- [ ] Viết expectation suite cho silver_lineitem
- [ ] Test với dữ liệu sạch
- [ ] Test với 1 lỗi thủ công
- [ ] So sánh sơ bộ dbt vs GX

### Week 7 (26/10 – 01/11): MedalGuard core (phần 1)
- [ ] config.py: load contract YAML
- [ ] schema_validator.py: schema drift detection
- [ ] constraint_validator.py: NOT NULL, type, range, allowed values

### Week 8 (02/11 – 08/11): MedalGuard core (phần 2)
- [ ] semantic_validator.py: distribution / mean drift
- [ ] reporter.py: violation log + blast radius
- [ ] gate.py: ContractGate class tích hợp
- [ ] Test end-to-end với clean + dirty data
- [ ] **GATE 2 CHECKPOINT**

### Week 9 (09/11 – 15/11): Mutation Suite
- [ ] base.py: BaseMutation class
- [ ] m1_additive.py
- [ ] m2_destructive.py
- [ ] m3_type_change.py
- [ ] m4_constraint_breach.py
- [ ] m5_semantic_drift.py
- [ ] experiments/runner.py

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
