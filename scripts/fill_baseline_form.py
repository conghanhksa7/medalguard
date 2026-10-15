"""Fill Form Review Baseline - v2: Handle table-based layout correctly."""
import sys; sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.shared import Pt
import os

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "Thông Tin Baseline & Metrics"
TEMPLATE = str(BASE_DIR / "Form Review Ket Qua Baseline.docx")
OUTPUT = str(BASE_DIR / "23280057 - Lương Lê Công Hạnh - Baseline Result.docx")

doc = Document(TEMPLATE)

def set_cell(cell, text, size=10, bold=False):
    """Replace all text in a cell, removing any structured document tags (sdt)."""
    for p in cell.paragraphs:
        for child in list(p._p):
            if child.tag.endswith('sdt'):
                p._p.remove(child)
        for r in p.runs:
            r.text = ""
    p = cell.paragraphs[0]
    if p.runs:
        p.runs[0].text = text
        p.runs[0].font.size = Pt(size)
        p.runs[0].bold = bold
    else:
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.bold = bold

# ============================================================
# TABLE 1: Thông tin đề tài (Row 0-2)
# ============================================================
t1 = doc.tables[1]

# Row 0: Tên đề tài | [fill] | Nhóm/SV | [fill]
set_cell(t1.rows[0].cells[1], 
    "MedalGuard: Early Data Failure Detection Framework for Medallion Lakehouse via Automated Contract Validation at Layer Boundaries under Schema Evolution")
set_cell(t1.rows[0].cells[3], "23280057 - Lương Lê Công Hạnh (Cá nhân)")

# Row 1: Hướng nghiên cứu
set_cell(t1.rows[1].cells[1], 
    "□ LLM   □ Computer Vision   □ ML/RL   □ Data Analytics   ☑ Data Engineering   □ Software Engineering")

# Row 2: Nguồn Data | [fill] | Mô tả | [fill]
set_cell(t1.rows[2].cells[1], 
    "TPC-H Benchmark — DuckDB TPCH Extension (chuẩn công nghiệp Data Warehousing)")
set_cell(t1.rows[2].cells[3], 
    "SF=0.1: 866,602 rows (150K orders, 600K lineitem, 15K customer). SF=1.0: ~8.6M rows cho final benchmark.")

# ============================================================
# TABLE 2: Property + Mục tiêu
# ============================================================
t2 = doc.tables[2]

# Row 0: Property chính | [fill] | Property phụ | [fill]
set_cell(t2.rows[0].cells[1], 
    "Reliability (Detection Rate — tỷ lệ phát hiện lỗi) + Data Quality (Blast Radius — mức lan tỏa lỗi đến Gold)")
set_cell(t2.rows[0].cells[3], 
    "Performance (Pipeline Overhead < 15%) + Observability (Detection Depth — bắt lỗi ở tầng nào)")

# Row 1: Mục tiêu muốn cải thiện
set_cell(t2.rows[1].cells[1], 
    "Tăng Detection Rate từ 0% (C0) lên ≥95% (C3). Giảm Blast Radius từ 34.6% TB lỗi ngầm (đỉnh 92.1% ở M5a/M5b) xuống ≤5%. Phát hiện lỗi sớm ở Gate 1 (pre-transform) thay vì để lọt đến Gold.")

# ============================================================
# TABLE 3: Baseline đã setup
# ============================================================
t3 = doc.tables[3]

# Row 0: Baseline áp dụng | [fill] | Nguồn | [fill]
set_cell(t3.rows[0].cells[1], 
    "C0 Baseline: Medallion Lakehouse pipeline (Bronze→Silver→Gold) KHÔNG có enforcement")
set_cell(t3.rows[0].cells[3], "□ Paper   ☑ GitHub   ☑ Official repo   □ Khác")

# Row 1: Paper/GitHub | [fill] | Repo | [fill]
set_cell(t3.rows[1].cells[1], 
    "N/A (đề tài mới, chưa có framework tương đương)")
set_cell(t3.rows[1].cells[3], 
    "dbt-core: github.com/dbt-labs/dbt-core | DuckDB: duckdb.org | Local: medalguard-seminar/")

# Row 2: Setup chính | [fill] | Hardware | [fill]
set_cell(t3.rows[2].cells[1], 
    "dbt-core 1.12.5 + dbt-duckdb 1.11.0 + DuckDB 1.5.5 + Python 3.12.7 (Windows 11)")
set_cell(t3.rows[2].cells[3], 
    "CPU: Intel Core i5-1240P (12th Gen, 12C/16T) | RAM: 16 GB (15.7 GB usable) | SSD | Không dùng GPU | dbt threads=4")

# Row 3: Trạng thái chạy | [fill] | Reproducible | [fill]
set_cell(t3.rows[3].cells[1], 
    "☑ Chạy được end-to-end (dbt run: 8/8 models PASS trong 1.62s | dbt test: 5/5 PASS trong 0.42s)   □ Chạy một phần   □ Chưa chạy được", bold=True)
set_cell(t3.rows[3].cells[3], 
    "☑ Có lệnh/config rõ (dbt_project.yml + scripts/)   ☑ Có log kết quả (results/baseline/)")

# Row 4: Ghi chú lỗi/setup
set_cell(t3.rows[4].cells[1], 
    "Kiến trúc dbt đã chuẩn hóa với schema macro: bronze, silver, gold. DuckDB TPC-H dbgen() tạo bảng có NOT NULL constraints mặc định → mutations M4a/M4b tự động chuẩn bị schema trước khi inject. 100% mã nguồn đột biến vận hành theo hướng đối tượng (OOP).")

# ============================================================
# TABLE 5: Kết quả Metric Baseline (Section 4)
# ============================================================
t5 = doc.tables[5]

metrics = [
    ("1", "Detection Rate (DR)", "N/A (đề tài mới)", "0% (0/14 faults detected)", "☑ ↑ cao tốt  □ ↓ thấp tốt", 
     "C0 không có enforcement → DR = 0/14 = 0%. Thử nghiệm trên 14 đột biến lỗi (M1a-M5c). Thử nghiệm kiểm chứng 5 đột biến lành tính (B1, B2, B3, B5, B7) đạt FPR = 0/5 = 0% (không báo động giả)."),
    ("2", "Blast Radius (BR)", "N/A", "14.8% TB (all) | 34.6% TB (silent)", "□ ↑ cao tốt  ☑ ↓ thấp tốt", 
     "Đo thực tế bằng diff tầng Gold với snapshot chuẩn: 6/14 lỗi lan truyền ngầm làm sai lệch Gold (M5a/M5b BR=92.1%; M4a/b/c BR=2.6-10.5%); 5/14 lỗi tự triệt tiêu (M1, M3); 3/14 làm sập pipeline (M2a-c)."),
    ("3", "Detection Depth Index (DDI)", "N/A", "∞ (NOT_DETECTED)", "□ ↑ cao tốt  ☑ ↓ thấp tốt", 
     "Không có tầng kiểm soát nào trong C0. Lỗi hoặc đi thẳng tới Gold (DDI=∞), hoặc sập pipeline thụ động tại dbt. Mục tiêu C3: DDI = 0 (phát hiện sớm ngay tại Gate 1 pre-transform)."),
    ("4", "Pipeline Latency / Overhead", "N/A", "6,796 ms (wall) | 1,411 ms (dbt)", "□ ↑ cao tốt  ☑ ↓ thấp tốt", 
     "Đo 7 lần lặp trên dữ liệu sạch (SF=0.1): Thời gian thực thi dbt thuần median 1,411 ms (stdev 109 ms); thời gian trọn gói gồm khởi động CLI median 6,796 ms (stdev 636 ms). Chuẩn đối sánh C0 = 0% overhead."),
]

for row_idx, data in enumerate(metrics):
    r = row_idx + 1
    if r < len(t5.rows):
        for col_idx, val in enumerate(data):
            set_cell(t5.rows[r].cells[col_idx], val, size=9)

# ============================================================
# TABLE 6: Đánh giá Baseline + Next Step (Section 5)
# ============================================================
t6 = doc.tables[6]

next_steps = [
    ("Detection Rate", "0%", "≥ 80%", "≥ 95%", 
     "Triển khai MedalGuard multi-tier gates: schema drift + constraint + semantic validation tại ranh giới Bronze→Silver (Gate 1) và Silver→Gold (Gate 2). Kỳ vọng chặn đứng các lỗi M4, M5 vốn đang lọt ngầm 100%."),
    ("Blast Radius", "14.8% TB (34.6% silent)", "≤ 10%", "≤ 5%", 
     "Cơ chế Quarantine tại Gate 1: lọc bản ghi vi phạm hợp đồng vào bảng quarantine và tạo clean view cho dbt Silver xử lý → triệt tiêu Blast Radius về 0% cho các lỗi vi phạm ràng buộc & schema."),
]

for row_idx, data in enumerate(next_steps):
    r = row_idx + 1
    if r < len(t6.rows):
        for col_idx, val in enumerate(data):
            set_cell(t6.rows[r].cells[col_idx], val, size=9)

# ============================================================
# TABLE 7: Evidence (Section 6)
# ============================================================
t7 = doc.tables[7]
set_cell(t7.rows[0].cells[0], 
    "☑ GitHub/source/config   ☑ Dataset/split   ☑ Log metric   ☑ Chart/error cases")
set_cell(t7.rows[0].cells[1], 
    "Link evidence: medalguard-seminar/ (local repo) | results/baseline/baseline_c0_results.json (19 experiments) | baseline_c0_overhead.json (7 runs, wall vs dbt) | baseline_c0_summary.json | blast_radius_by_mutation.png | outcome_by_category.png | pipeline_overhead.png")

# ============================================================

# ============================================================
# Fix Orphan Section Headers (Section 3 & Section 5) cleanly
# ============================================================
for tbl_idx, banner_row_idx in [(2, 2), (5, 5)]:
    tbl = doc.tables[tbl_idx]
    # Remove w:tblHeader on Row 0 so Word does not repeat the previous section's table header after page break
    trPr = tbl.rows[0]._tr.get_or_add_trPr()
    for child in list(trPr):
        if child.tag.endswith('tblHeader'):
            trPr.remove(child)
    # Force the section banner row to start on the new page together with the next table
    for cell in tbl.rows[banner_row_idx].cells:
        for p in cell.paragraphs:
            p.paragraph_format.page_break_before = True
            p.paragraph_format.keep_with_next = True

# Save
# ============================================================
doc.save(OUTPUT)
print(f"✅ Form đã điền xong: {OUTPUT}")
print(f"   File size: {os.path.getsize(OUTPUT):,} bytes")
print(f"\n📌 Bước tiếp theo:")
print(f"   1. Mở file docx bằng Word để review lại")
print(f"   2. Xuất PDF: File → Save As → PDF")
print(f"   3. Đổi tên: 23280057 - Lương Lê Công Hạnh - Baseline Result.pdf")
print(f"   4. Nộp cho GVHD trước 15/10")
