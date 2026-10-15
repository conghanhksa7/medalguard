"""Fill and Format Form Review Baseline with Unified Page 4 Table.
- Page 4: Section 5 & Section 6 unified seamlessly into Table 6, exactly matching user layout:
    Row 0: 5. ĐÁNH GIÁ BASELINE & MỤC TIÊU NEXT STEP (banner, full width)
    Row 1: Header (Metric ưu tiên | Baseline nhóm đạt | Mức tiêu chuẩn cần đạt | Next-step Target | Cách dự kiến...)
    Row 2: Detection Rate (0%, >= 80%, >= 95%, description)
    Row 3: Blast Radius (14.8% TB, <= 10%, <= 5%, description)
    Row 4: Empty row (5 columns)
    Row 5: 6. EVIDENCE NỘP KÈM BASELINE (banner, full width)
    Row 6: Evidence checkboxes & Link
- Page 3: Table 5 ends cleanly with 4 metrics, no orphan row 5.
- Page 2: Table 3 starts with Banner 3.
- Page 1: Table 0, 1, 2 all pixel-perfect aligned to 15,364 dxa.
- All tables set to exactly 15,364 dxa with unified #B8C7D9 borders.
- Zero gaps, zero dotted outlines, zero misalignments.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

BASE_DIR = Path(r"D:\Study\Seminar\Thông Tin Baseline & Metrics")
TEMPLATE = str(BASE_DIR / "Form Review Ket Qua Baseline.docx")
OUTPUT_DOCX = str(BASE_DIR / "23280057 - Lương Lê Công Hạnh - Baseline Result.docx")
OUTPUT_PDF = str(BASE_DIR / "23280057 - Lương Lê Công Hạnh - Baseline Result.pdf")

doc = Document(TEMPLATE)
BORDER_COLOR = "B8C7D9"
BANNER_FILL = "0B3A6E"
TABLE_WIDTH_DXA = 15364

def set_cell(cell, text, size=10, bold=False):
    for p in cell.paragraphs:
        for child in list(p._p):
            if child.tag.endswith('sdt'):
                p._p.remove(child)
        for r in p.runs:
            r.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.05
    if p.runs:
        p.runs[0].text = text
        p.runs[0].font.size = Pt(size)
        p.runs[0].bold = bold
    else:
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.bold = bold

def set_cell_width(cell, width_dxa):
    tcPr = cell._tc.get_or_add_tcPr()
    tcW = tcPr.find(qn('w:tcW'))
    if tcW is None:
        tcW = OxmlElement('w:tcW')
        tcPr.append(tcW)
    tcW.set(qn('w:w'), str(width_dxa))
    tcW.set(qn('w:type'), 'dxa')

def set_cell_span(cell, span_val):
    tcPr = cell._tc.get_or_add_tcPr()
    span = tcPr.find(qn('w:gridSpan'))
    if span is None:
        span = OxmlElement('w:gridSpan')
        tcPr.append(span)
    span.set(qn('w:val'), str(span_val))

def set_table_borders(tbl, color=BORDER_COLOR, sz="6"):
    tblPr = tbl._tbl.tblPr
    existing = tblPr.find(qn('w:tblBorders'))
    if existing is not None:
        tblPr.remove(existing)
    borders_xml = f"""
    <w:tblBorders {nsdecls('w')}>
        <w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:insideV w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
    </w:tblBorders>
    """
    tblPr.append(parse_xml(borders_xml))

def set_cell_border_solid(cell, color=BORDER_COLOR, sz="6"):
    tcPr = cell._tc.get_or_add_tcPr()
    existing = tcPr.find(qn('w:tcBorders'))
    if existing is not None:
        tcPr.remove(existing)
    borders_xml = f"""
    <w:tcBorders {nsdecls('w')}>
        <w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
    </w:tcBorders>
    """
    tcPr.append(parse_xml(borders_xml))

def set_cell_shading(cell, color=BANNER_FILL):
    tcPr = cell._tc.get_or_add_tcPr()
    existing = tcPr.find(qn('w:shd'))
    if existing is not None:
        tcPr.remove(existing)
    shd_xml = f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{color}"/>'
    tcPr.append(parse_xml(shd_xml))

def set_table_geometry(tbl, col_widths):
    tblPr = tbl._tbl.tblPr
    tblW = tblPr.find(qn('w:tblW'))
    if tblW is None:
        tblW = OxmlElement('w:tblW')
        tblPr.append(tblW)
    tblW.set(qn('w:w'), str(TABLE_WIDTH_DXA))
    tblW.set(qn('w:type'), 'dxa')
    
    jc = tblPr.find(qn('w:jc'))
    if jc is None:
        jc = OxmlElement('w:jc')
        tblPr.append(jc)
    jc.set(qn('w:val'), 'center')
    
    tblGrid = tbl._tbl.tblGrid
    for child in list(tblGrid):
        tblGrid.remove(child)
    for w in col_widths:
        col = OxmlElement('w:gridCol')
        col.set(qn('w:w'), str(w))
        tblGrid.append(col)

# ============================================================
# TABLE 0: Header Section 1
# ============================================================
t0 = doc.tables[0]
set_table_borders(t0)
set_table_geometry(t0, [TABLE_WIDTH_DXA])
set_cell_width(t0.rows[0].cells[0], TABLE_WIDTH_DXA)
set_cell_border_solid(t0.rows[0].cells[0])

# ============================================================
# TABLE 1: Thông tin đề tài (Row 0-2) + Banner 2 (Row 3)
# ============================================================
t1 = doc.tables[1]
t1_cols = [2000, 6600, 1800, 4964]  # sum = 15364
set_table_borders(t1)
set_table_geometry(t1, t1_cols)

set_cell(t1.rows[0].cells[1], "MedalGuard: Early Data Failure Detection Framework for Medallion Lakehouse via Automated Contract Validation at Layer Boundaries under Schema Evolution")
set_cell(t1.rows[0].cells[3], "23280057 - Lương Lê Công Hạnh (Cá nhân)")
set_cell(t1.rows[1].cells[1], "[ ] LLM   [ ] Computer Vision   [ ] ML/RL   [ ] Data Analytics   [x] Data Engineering   [ ] Software Engineering")
set_cell(t1.rows[2].cells[1], "TPC-H Benchmark - DuckDB TPCH Extension (chuẩn công nghiệp Data Warehousing)")
set_cell(t1.rows[2].cells[3], "SF=0.1: 866,602 rows (150K orders, 600K lineitem, 15K customer). SF=1.0: ~8.6M rows cho final benchmark.")

for r_idx in [0, 2]:
    for c_idx, w in enumerate(t1_cols):
        set_cell_width(t1.rows[r_idx].cells[c_idx], w)

set_cell_width(t1.rows[1].cells[0], t1_cols[0])
set_cell_span(t1.rows[1].cells[1], 3)
set_cell_width(t1.rows[1].cells[1], sum(t1_cols[1:]))

# Row 3: Banner 2
set_cell_span(t1.rows[3].cells[0], 4)
set_cell_width(t1.rows[3].cells[0], TABLE_WIDTH_DXA)
set_cell_border_solid(t1.rows[3].cells[0])
set_cell_shading(t1.rows[3].cells[0], BANNER_FILL)

# ============================================================
# TABLE 2: Property (Row 0-1) + Banner 3 (Row 2)
# ============================================================
t2 = doc.tables[2]
t2_cols = [2000, 6600, 1800, 4964]  # sum = 15364
set_table_borders(t2)
set_table_geometry(t2, t2_cols)

set_cell(t2.rows[0].cells[1], "Reliability (Detection Rate - tỷ lệ phát hiện lỗi) + Data Quality (Blast Radius - mức lan tỏa lỗi đến Gold)")
set_cell(t2.rows[0].cells[3], "Performance (Pipeline Overhead < 15%) + Observability (Detection Depth - bắt lỗi ở tầng nào)")
set_cell(t2.rows[1].cells[1], "Tăng Detection Rate từ 0% (C0) lên >= 95% (C3). Giảm Blast Radius từ 34.6% TB lỗi ngầm (đỉnh 92.1% ở M5a/M5b) xuống <= 5%. Phát hiện lỗi sớm ở Gate 1 (pre-transform) thay vì để lọt đến Gold.")

for c_idx, w in enumerate(t2_cols):
    set_cell_width(t2.rows[0].cells[c_idx], w)

set_cell_width(t2.rows[1].cells[0], t2_cols[0])
set_cell_span(t2.rows[1].cells[1], 3)
set_cell_width(t2.rows[1].cells[1], sum(t2_cols[1:]))

# Row 2: Banner 3
set_cell_span(t2.rows[2].cells[0], 4)
set_cell_width(t2.rows[2].cells[0], TABLE_WIDTH_DXA)
set_cell_border_solid(t2.rows[2].cells[0])
set_cell_shading(t2.rows[2].cells[0], BANNER_FILL)

# ============================================================
# TABLE 3: Baseline đã setup (Row 0-4)
# ============================================================
t3 = doc.tables[3]
t3_cols = [2200, 6400, 1800, 4964]  # sum = 15364
set_table_borders(t3)
set_table_geometry(t3, t3_cols)

set_cell(t3.rows[0].cells[1], "C0 Baseline: Medallion Lakehouse pipeline (Bronze -> Silver -> Gold) KHÔNG có enforcement")
set_cell(t3.rows[0].cells[3], "[ ] Paper   [x] GitHub   [x] Official repo   [ ] Khác")
set_cell(t3.rows[1].cells[1], "N/A (đề tài mới, chưa có framework tương đương)")
set_cell(t3.rows[1].cells[3], "https://github.com/conghanhksa7/medalguard (MedalGuard Framework & Baseline C0)", size=8.5)
set_cell(t3.rows[2].cells[1], "dbt-core 1.12.5 + dbt-duckdb 1.11.0 + DuckDB 1.5.5 + Python 3.12.7 (Windows 11)")
set_cell(t3.rows[2].cells[3], "CPU: Intel Core i5-1240P (12th Gen, 12C/16T) | RAM: 16 GB (15.7 GB usable) | SSD | Không dùng GPU | dbt threads=4")
set_cell(t3.rows[3].cells[1], "[x] Chạy được end-to-end (dbt run: 8/8 models PASS trong 1.62s | dbt test: 5/5 PASS trong 0.42s)   [ ] Chạy một phần   [ ] Chưa chạy được", bold=True)
set_cell(t3.rows[3].cells[3], "[x] Có lệnh/config rõ (dbt_project.yml + scripts/)   [x] Có log kết quả (results/baseline/)")
set_cell(t3.rows[4].cells[1], "Kiến trúc dbt đã chuẩn hóa với schema macro: bronze, silver, gold. DuckDB TPC-H dbgen() tạo bảng có NOT NULL constraints mặc định -> mutations M4a/M4b tự động chuẩn bị schema trước khi inject. 100% mã nguồn đột biến vận hành theo hướng đối tượng (OOP).")

for r_idx in range(4):
    for c_idx, w in enumerate(t3_cols):
        set_cell_width(t3.rows[r_idx].cells[c_idx], w)

set_cell_width(t3.rows[4].cells[0], t3_cols[0])
set_cell_span(t3.rows[4].cells[1], 3)
set_cell_width(t3.rows[4].cells[1], sum(t3_cols[1:]))

# ============================================================
# TABLE 4: Header Section 4
# ============================================================
t4 = doc.tables[4]
set_table_borders(t4)
set_table_geometry(t4, [TABLE_WIDTH_DXA])
set_cell_width(t4.rows[0].cells[0], TABLE_WIDTH_DXA)
set_cell_border_solid(t4.rows[0].cells[0])

# ============================================================
# TABLE 5: Kết quả Metric Baseline (Section 4 Metrics ONLY)
# ============================================================
t5 = doc.tables[5]
t5_cols = [500, 2400, 1500, 2600, 1864, 6500]  # sum = 15364
set_table_borders(t5)
set_table_geometry(t5, t5_cols)

metrics = [
    ("1", "Detection Rate (DR)", "N/A (đề tài mới)", "0% (0/14 faults detected)", "[x] Cao tốt   [ ] Thấp tốt", 
     "C0 không có enforcement -> DR = 0/14 = 0%. Thử nghiệm trên 14 đột biến lỗi (M1a-M5c). Thử nghiệm kiểm chứng 5 đột biến lành tính (B1, B2, B3, B5, B7) đạt FPR = 0/5 = 0% (không báo động giả)."),
    ("2", "Blast Radius (BR)", "N/A", "14.8% TB (all) | 34.6% TB (silent)", "[ ] Cao tốt   [x] Thấp tốt", 
     "Đo thực tế bằng diff tầng Gold với snapshot chuẩn: 6/14 lỗi lan truyền ngầm làm sai lệch Gold (M5a/M5b BR=92.1%; M4a/b/c BR=2.6-10.5%); 5/14 lỗi tự triệt tiêu (M1, M3); 3/14 làm sập pipeline (M2a-c)."),
    ("3", "Detection Depth Index (DDI)", "N/A", "Không xác định (NOT_DETECTED)", "[ ] Cao tốt   [x] Thấp tốt", 
     "Không có tầng kiểm soát nào trong C0. Lỗi hoặc đi thẳng tới Gold (DDI = không xác định), hoặc sập pipeline thụ động tại dbt. Mục tiêu C3: DDI = 0 (phát hiện sớm ngay tại Gate 1 pre-transform)."),
    ("4", "Pipeline Latency / Overhead", "N/A", "6,796 ms (wall) | 1,411 ms (dbt)", "[ ] Cao tốt   [x] Thấp tốt", 
     "Đo 7 lần lặp trên dữ liệu sạch (SF=0.1): Thời gian thực thi dbt thuần median 1,411 ms (stdev 109 ms); thời gian trọn gói gồm khởi động CLI median 6,796 ms (stdev 636 ms). Chuẩn đối sánh C0 = 0% overhead."),
]

for row_idx, data in enumerate(metrics):
    r = row_idx + 1
    if r < len(t5.rows):
        for col_idx, val in enumerate(data):
            set_cell(t5.rows[r].cells[col_idx], val, size=9)

for r_idx in range(5):
    for c_idx, w in enumerate(t5_cols):
        set_cell_width(t5.rows[r_idx].cells[c_idx], w)

# REMOVE Row 5 from Table 5 (it will be moved to Table 6 on Page 4!)
if len(t5.rows) > 5:
    tr_to_remove = t5.rows[5]._tr
    t5._tbl.remove(tr_to_remove)

# Remove tblHeader from Table 5 Row 0
trPr_t5 = t5.rows[0]._tr.get_or_add_trPr()
for c in list(trPr_t5):
    if c.tag.endswith('tblHeader'):
        trPr_t5.remove(c)

# ============================================================
# TABLE 6: UNIFIED TABLE FOR PAGE 4 (Sections 5 & 6)
# ============================================================
t6 = doc.tables[6]
t6_cols = [2200, 2400, 2000, 2000, 6764]  # sum = 15364
set_table_borders(t6)
set_table_geometry(t6, t6_cols)

# Clear any gridBefore / wBefore / tblHeader in t6
for r in t6.rows:
    trPr = r._tr.trPr
    if trPr is not None:
        for child in list(trPr):
            if child.tag.endswith(('gridBefore', 'gridAfter', 'wBefore', 'wAfter', 'tblHeader')):
                trPr.remove(child)

# Row 0: Insert Section 5 Banner at the very top of Table 6!
banner5_xml = f"""
<w:tr {nsdecls('w')}>
    <w:trPr>
        <w:cantSplit/>
        <w:jc w:val="center"/>
    </w:trPr>
    <w:tc>
        <w:tcPr>
            <w:tcW w:w="{TABLE_WIDTH_DXA}" w:type="dxa"/>
            <w:gridSpan w:val="5"/>
            <w:tcBorders>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="{BORDER_COLOR}"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="{BORDER_COLOR}"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{BORDER_COLOR}"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="{BORDER_COLOR}"/>
            </w:tcBorders>
            <w:shd w:val="clear" w:color="auto" w:fill="{BANNER_FILL}"/>
            <w:tcMar>
                <w:top w:w="70" w:type="dxa"/>
                <w:left w:w="120" w:type="dxa"/>
                <w:bottom w:w="70" w:type="dxa"/>
                <w:right w:w="120" w:type="dxa"/>
            </w:tcMar>
        </w:tcPr>
        <w:p>
            <w:pPr>
                <w:pageBreakBefore/>
                <w:keepNext/>
                <w:spacing w:before="40" w:after="40" w:line="252" w:lineRule="auto"/>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:b/>
                    <w:bCs/>
                    <w:color w:val="FFFFFF"/>
                    <w:sz w:val="22"/>
                    <w:szCs w:val="22"/>
                </w:rPr>
                <w:t>5. ĐÁNH GIÁ BASELINE &amp; MỤC TIÊU NEXT STEP</w:t>
            </w:r>
        </w:p>
    </w:tc>
</w:tr>
"""
t6._tbl.insert(t6._tbl.index(t6.rows[0]._tr), parse_xml(banner5_xml))

# Next steps data: Row 2 & Row 3
set_cell(t6.rows[2].cells[0], "Detection Rate", size=9, bold=True)
set_cell(t6.rows[2].cells[1], "0%", size=9)
set_cell(t6.rows[2].cells[2], ">= 80%", size=9)
set_cell(t6.rows[2].cells[3], ">= 95%", size=9)
set_cell(t6.rows[2].cells[4], "Triển khai MedalGuard multi-tier gates: schema drift + constraint + semantic validation tại ranh giới Bronze -> Silver (Gate 1) và Silver -> Gold (Gate 2). Kỳ vọng chặn đứng các lỗi M4, M5 vốn đang lọt ngầm 100%.", size=9)

set_cell(t6.rows[3].cells[0], "Blast Radius", size=9, bold=True)
set_cell(t6.rows[3].cells[1], "14.8% TB (34.6% silent)", size=9)
set_cell(t6.rows[3].cells[2], "<= 10%", size=9)
set_cell(t6.rows[3].cells[3], "<= 5%", size=9)
set_cell(t6.rows[3].cells[4], "Cơ chế Quarantine tại Gate 1: lọc bản ghi vi phạm hợp đồng vào bảng quarantine và tạo clean view cho dbt Silver xử lý -> triệt tiêu Blast Radius về 0% cho các lỗi vi phạm ràng buộc & schema.", size=9)

for r_idx in [1, 2, 3]:
    for c_idx, w in enumerate(t6_cols):
        set_cell_width(t6.rows[r_idx].cells[c_idx], w)

# Insert empty row between Row 3 (Blast Radius) and Row 4 (Banner 6) as in user's image
empty_row_xml = f"""
<w:tr {nsdecls('w')}>
    <w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>
    <w:tc><w:tcPr><w:tcW w:w="{t6_cols[0]}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr></w:p></w:tc>
    <w:tc><w:tcPr><w:tcW w:w="{t6_cols[1]}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr></w:p></w:tc>
    <w:tc><w:tcPr><w:tcW w:w="{t6_cols[2]}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr></w:p></w:tc>
    <w:tc><w:tcPr><w:tcW w:w="{t6_cols[3]}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr></w:p></w:tc>
    <w:tc><w:tcPr><w:tcW w:w="{t6_cols[4]}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr></w:p></w:tc>
</w:tr>
"""
t6._tbl.insert(t6._tbl.index(t6.rows[4]._tr), parse_xml(empty_row_xml))

# Row 5: Banner 6 ("6. EVIDENCE NỘP KÈM BASELINE")
set_cell_span(t6.rows[5].cells[0], 5)
set_cell_width(t6.rows[5].cells[0], TABLE_WIDTH_DXA)
set_cell_border_solid(t6.rows[5].cells[0])
set_cell_shading(t6.rows[5].cells[0], BANNER_FILL)

# Row 6: Evidence content (moved from Table 7)
evidence_txt1 = "[x] GitHub/source/config   [x] Dataset/split\n[x] Log metric   [x] Chart/error cases"
evidence_txt2 = "Link evidence: https://github.com/conghanhksa7/medalguard (Repo mã nguồn đầy đủ, cấu hình dbt, log JSON 19 thí nghiệm tại results/baseline/ và 3 biểu đồ thực nghiệm)"

evidence_row_xml = f"""
<w:tr {nsdecls('w')}>
    <w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>
    <w:tc>
        <w:tcPr>
            <w:tcW w:w="{t6_cols[0] + t6_cols[1]}" w:type="dxa"/>
            <w:gridSpan w:val="2"/>
            <w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>
        </w:tcPr>
        <w:p>
            <w:pPr><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>
            <w:r><w:rPr><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{evidence_txt1}</w:t></w:r>
        </w:p>
    </w:tc>
    <w:tc>
        <w:tcPr>
            <w:tcW w:w="{sum(t6_cols[2:])}" w:type="dxa"/>
            <w:gridSpan w:val="3"/>
            <w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>
        </w:tcPr>
        <w:p>
            <w:pPr><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>
            <w:r><w:rPr><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{evidence_txt2}</w:t></w:r>
        </w:p>
    </w:tc>
</w:tr>
"""
t6._tbl.append(parse_xml(evidence_row_xml))

# Remove Table 7
t7 = doc.tables[7]
t7._tbl.getparent().remove(t7._tbl)

# ============================================================
# Page Breaks and Keep-With-Next
# ============================================================
# Page 1 -> 2: Table 2 Row 2 (Banner 3) page_break_before
for cell in t2.rows[2].cells:
    for p in cell.paragraphs:
        p.paragraph_format.page_break_before = True
        p.paragraph_format.keep_with_next = True

# Remove tblHeader from Table 2 Row 0
trPr_t2 = t2.rows[0]._tr.get_or_add_trPr()
for c in list(trPr_t2):
    if c.tag.endswith('tblHeader'):
        trPr_t2.remove(c)

# Save DOCX
doc.save(OUTPUT_DOCX)
print(f"✅ Form DOCX đã điền xong: {OUTPUT_DOCX}")
print(f"   Dung lượng: {os.path.getsize(OUTPUT_DOCX):,} bytes")

# Convert to PDF
from docx2pdf import convert
print("🔄 Đang xuất PDF...")
convert(OUTPUT_DOCX, OUTPUT_PDF)
print(f"✅ Đã xuất PDF thành công: {OUTPUT_PDF}")
print(f"   Dung lượng: {os.path.getsize(OUTPUT_PDF):,} bytes")
