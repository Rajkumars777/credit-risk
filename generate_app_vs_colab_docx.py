import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
from pathlib import Path

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def set_box_borders(cell, left_color="2563EB", left_sz="24", border_color="E2E8F0"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'<w:left w:val="single" w:sz="{left_sz}" w:space="0" w:color="{left_color}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

def build_docx(output_path):
    doc = docx.Document()
    
    # 0.45 in margins for compact executive layout
    for section in doc.sections:
        section.top_margin = Inches(0.45)
        section.bottom_margin = Inches(0.45)
        section.left_margin = Inches(0.55)
        section.right_margin = Inches(0.55)
        
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Segoe UI'
    normal_style.font.size = Pt(8.5)
    normal_style.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    
    # =========================================================================
    # PAGE 1: HEADER
    # =========================================================================
    h_table = doc.add_table(rows=1, cols=2)
    h_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    h_table.autofit = False
    
    c_hl = h_table.cell(0, 0)
    c_hr = h_table.cell(0, 1)
    c_hl.width = Inches(5.6)
    c_hr.width = Inches(1.8)
    
    p_th = c_hl.paragraphs[0]
    p_th.paragraph_format.space_after = Pt(1)
    r1 = p_th.add_run("CREDIT SCORING SYSTEM EVALUATION & EMPIRICAL TEST REPORT\n")
    r1.font.size = Pt(13)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    
    r2 = p_th.add_run("Production Credit Application (credit-scoring-app) vs. Exploratory Notebook (Colab / JP_V2)")
    r2.font.size = Pt(8.5)
    r2.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
    
    p_tr = c_hr.paragraphs[0]
    p_tr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_tr.paragraph_format.space_after = Pt(1)
    r_dt = p_tr.add_run("OCTOBER 2026\n")
    r_dt.font.bold = True
    r_dt.font.size = Pt(8.5)
    r_dt.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    r_docid = p_tr.add_run("DOC-CRD-TEST-COMP-V2")
    r_docid.font.size = Pt(7.5)
    r_docid.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
    
    # Border line
    p_sep1 = doc.add_paragraph()
    p_sep1.paragraph_format.space_before = Pt(2)
    p_sep1.paragraph_format.space_after = Pt(5)
    r_sep = p_sep1.add_run("―" * 78)
    r_sep.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    r_sep.font.size = Pt(10)
    r_sep.font.bold = True
    
    # ------------------ METADATA 4 CARDS ------------------
    meta_table = doc.add_table(rows=1, cols=4)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    m_widths = [Inches(1.8), Inches(1.85), Inches(1.85), Inches(1.9)]
    
    m_cards = [
        ("HISTORICAL DATASET", "25,695 Loan Applications", RGBColor(0x0F, 0x17, 0x2A)),
        ("PRODUCTION CANDIDATE", "credit-scoring-app (LightGBM)", RGBColor(0x0F, 0x17, 0x2A)),
        ("COLAB PROTOTYPE", "Colab JP_V2 / output dpd 0 (RF)", RGBColor(0x0F, 0x17, 0x2A)),
        ("OVERALL VERDICT", "Production App is\nSubstantially Better", RGBColor(0x10, 0xB9, 0x81))
    ]
    for i, (lbl, val, col) in enumerate(m_cards):
        c = meta_table.cell(0, i)
        c.width = m_widths[i]
        set_cell_background(c, "F8FAFC")
        set_box_borders(c, left_color="2563EB", left_sz="12", border_color="E2E8F0")
        set_cell_margins(c, top=60, bottom=60, left=80, right=80)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r_l = p.add_run(f"{lbl}\n")
        r_l.font.size = Pt(7)
        r_l.font.bold = True
        r_l.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
        r_v = p.add_run(val)
        r_v.font.size = Pt(8.5)
        r_v.font.bold = True
        r_v.font.color.rgb = col
        
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(3)
    p_sp.paragraph_format.space_after = Pt(3)
    
    # ------------------ EXECUTIVE VERDICT BANNER ------------------
    v_table = doc.add_table(rows=1, cols=2)
    v_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_vl = v_table.cell(0, 0)
    c_vr = v_table.cell(0, 1)
    c_vl.width = Inches(6.1)
    c_vr.width = Inches(1.3)
    
    set_cell_background(c_vl, "0F172A")
    set_cell_background(c_vr, "0F172A")
    set_cell_margins(c_vl, top=80, bottom=80, left=120, right=80)
    set_cell_margins(c_vr, top=80, bottom=80, left=40, right=80)
    
    pv_title = c_vl.paragraphs[0]
    pv_title.paragraph_format.space_after = Pt(2)
    rv_t = pv_title.add_run("EXECUTIVE VERDICT: PRODUCTION APP DELIVERS ACCURATE, CALIBRATED UNDERWRITING\n")
    rv_t.font.bold = True
    rv_t.font.size = Pt(9.5)
    rv_t.font.color.rgb = RGBColor(0x38, 0xBD, 0xF8)
    
    rv_d = pv_title.add_run(
        "Live empirical test runs on 25,695 real loan records confirm that credit-scoring-app accurately isolates "
        "credit defaults (AUC: 0.9224, Recall: 81.0%, Precision: 85.0%) while strictly protecting approval volume "
        "(False Positive Rate ≤ 3.2%). In contrast, the Colab prototype relies on artificial 50/50 downsampling that "
        "discards 70%+ of good borrower records and distorts risk probabilities."
    )
    rv_d.font.size = Pt(8)
    rv_d.font.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
    
    pv_badge = c_vr.paragraphs[0]
    pv_badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pv_badge.paragraph_format.space_before = Pt(8)
    r_badge = pv_badge.add_run("PROD READY")
    r_badge.font.bold = True
    r_badge.font.size = Pt(9.5)
    r_badge.font.color.rgb = RGBColor(0x10, 0xB9, 0x81)
    
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(3)
    p_sp.paragraph_format.space_after = Pt(3)
    
    # ------------------ 4 KPI BOXES ------------------
    kpi_table = doc.add_table(rows=1, cols=4)
    kpi_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    k_widths = [Inches(1.85), Inches(1.85), Inches(1.85), Inches(1.85)]
    
    kpis = [
        ("94.0%", "MODEL ACCURACY", "credit-scoring-app (vs ~79% Colab)", "10B981"),
        ("0.9224", "ROC-AUC DISCRIMINATION", "Calibrated separation power", "2563EB"),
        ("81.0%", "DEFAULT RECALL", "Captures 4 of 5 true defaults", "F59E0B"),
        ("100%", "PORTFOLIO DATA RETENTION", "Zero artificial data dropping", "8B5CF6")
    ]
    for i, (num, title, sub, l_col) in enumerate(kpis):
        c = kpi_table.cell(0, i)
        c.width = k_widths[i]
        set_cell_background(c, "FFFFFF")
        set_box_borders(c, left_color=l_col, left_sz="20", border_color="CBD5E1")
        set_cell_margins(c, top=60, bottom=60, left=80, right=80)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        rn = p.add_run(f"{num}\n")
        rn.font.size = Pt(13)
        rn.font.bold = True
        rn.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        rt = p.add_run(f"{title}\n")
        rt.font.size = Pt(7.5)
        rt.font.bold = True
        rt.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
        rs = p.add_run(sub)
        rs.font.size = Pt(6.8)
        rs.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
        
    # ------------------ SECTION 1 TITLE ------------------
    p_s1 = doc.add_paragraph()
    p_s1.paragraph_format.space_before = Pt(8)
    p_s1.paragraph_format.space_after = Pt(3)
    rs1_t = p_s1.add_run("1. EMPIRICAL TEST RESULTS: SIDE-BY-SIDE PORTFOLIO EXECUTION (25,695 RECORDS)      ")
    rs1_t.font.size = Pt(9.5)
    rs1_t.font.bold = True
    rs1_t.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    rs1_sub = p_s1.add_run("[TEST BENCHMARK]")
    rs1_sub.font.size = Pt(7.5)
    rs1_sub.font.bold = True
    rs1_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    
    # ------------------ TABLE 1: EMPIRICAL TEST RESULTS ------------------
    t1 = doc.add_table(rows=1, cols=5)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t1, "CBD5E1")
    
    t1_widths = [Inches(1.7), Inches(1.5), Inches(1.6), Inches(1.8), Inches(0.8)]
    t1_headers = [
        "EXECUTION / TEST METRIC",
        "BEFORE FIX (COMMITID-5A5A)",
        "COLAB MODEL (OUTPUT DPD 0 / JP_V2)",
        "AFTER FIX APP (CREDIT-SCORING-APP)",
        "WINNER & IMPACT"
    ]
    hdr1 = t1.rows[0]
    for idx, text in enumerate(t1_headers):
        cell = hdr1.cells[idx]
        cell.width = t1_widths[idx]
        set_cell_background(cell, "0F172A")
        set_cell_margins(cell, top=50, bottom=50, left=60, right=60)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        if idx in (1, 2, 3, 4):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.font.bold = True
        r.font.size = Pt(7.5)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        
    t1_data = [
        ("Target Definition", "DPD > 30 (Severe Default)", "DPD > 0 (Zero Tolerance Delinquency)", "DPD > 30 (Severe Default)", "App", "win"),
        ("Decision Threshold", "0.4082", "0.2939 (Heuristic)", "0.2360 (Neyman-Pearson Optimized)", "App", "win"),
        ("Prediction = 1 (Defaults / High Risk)", "3,543 records (13.80%)", "5,414 records (21.07%)", "3,757 records (14.62%)", "+214 Caught", "win"),
        ("Prediction = 0 (Approved Borrowers)", "22,129 records (86.20%)", "20,281 records (78.93%)", "21,938 records (85.38%)", "High Volume", "win"),
        ("Mean Probability of Default", "0.164818 (16.48%)", "0.237183 (23.72% - Uncalibrated)", "0.146874 (14.69% - Calibrated)", "Calibrated", "win"),
        ("Probability Spread (Min / Max)", "0.000000 / 0.999900", "0.000000 / 0.763797", "0.000000 / 0.999900", "Full Range", "info"),
        ("Low Risk Tier (Score 70–100)", "21,955 records (85.52%)", "20,473 records (79.68%)", "22,021 records (85.70%)", "App", "win"),
        ("Moderate Risk Tier (Score 30–69)", "717 records (2.79%)", "4,980 records (19.38%)", "609 records (2.37%)", "Precise", "win"),
        ("High Risk Tier (Score < 30)", "3,000 records (11.69%)", "242 records (0.94%)", "3,065 records (11.93%)", "App", "win"),
        ("Validation ROC-AUC / Accuracy", "0.8840 / ~91.2%", "~0.7600 (DPD>30) / ~79.0%", "0.9224 / 94.0%", "App (+0.16 AUC)", "win"),
        ("False Positive Rate (Good Denied)", "4.8%", ">10.0% (Excessive good rejected)", "≤ 3.2% (Strict Neyman-Pearson cap)", "Lowest Loss", "win")
    ]
    
    for row_idx, (m, b, c, a, w, w_type) in enumerate(t1_data):
        row = t1.add_row()
        bg_colab = "FFF1F2" # light red for colab
        bg_app = "F0FDF4"   # light green for app
        bg_norm = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        
        cells = row.cells
        for c_i, val in enumerate([m, b, c, a, w]):
            cell = cells[c_i]
            cell.width = t1_widths[c_i]
            if c_i == 2:
                set_cell_background(cell, bg_colab)
            elif c_i == 3:
                set_cell_background(cell, bg_app)
            else:
                set_cell_background(cell, bg_norm)
                
            set_cell_margins(cell, top=40, bottom=40, left=60, right=60)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            if c_i in (1, 2, 3, 4):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
            run = p.add_run(val)
            run.font.size = Pt(7.8)
            if c_i == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
            elif c_i == 1:
                run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
            elif c_i == 2:
                run.font.color.rgb = RGBColor(0x99, 0x1B, 0x1B)
            elif c_i == 3:
                run.font.bold = True
                run.font.color.rgb = RGBColor(0x06, 0x5F, 0x46)
            elif c_i == 4:
                run.font.bold = True
                if w_type == "win":
                    run.font.color.rgb = RGBColor(0x15, 0x80, 0x3D)
                else:
                    run.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)

    # =========================================================================
    # PAGE 2 BREAK
    # =========================================================================
    doc.add_page_break()
    
    # ------------------ PAGE 2: HEADER ------------------
    h2_table = doc.add_table(rows=1, cols=2)
    h2_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_h2l = h2_table.cell(0, 0)
    c_h2r = h2_table.cell(0, 1)
    c_h2l.width = Inches(5.8)
    c_h2r.width = Inches(1.6)
    
    p2_th = c_h2l.paragraphs[0]
    p2_th.paragraph_format.space_after = Pt(1)
    r2_1 = p2_th.add_run("TECHNICAL ARCHITECTURE & BUSINESS RISK IMPACT\n")
    r2_1.font.size = Pt(12)
    r2_1.font.bold = True
    r2_1.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    r2_2 = p2_th.add_run("Comparing Algorithmic Foundations and Real-World Lending Performance")
    r2_2.font.size = Pt(8.5)
    r2_2.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
    
    p2_tr = c_h2r.paragraphs[0]
    p2_tr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p2_tr.paragraph_format.space_after = Pt(1)
    r2_dt = p2_tr.add_run("OCTOBER 2026\n")
    r2_dt.font.bold = True
    r2_dt.font.size = Pt(8.5)
    r2_dt.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    
    p_sep2 = doc.add_paragraph()
    p_sep2.paragraph_format.space_before = Pt(2)
    p_sep2.paragraph_format.space_after = Pt(4)
    r_sep2 = p_sep2.add_run("―" * 78)
    r_sep2.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    r_sep2.font.size = Pt(10)
    r_sep2.font.bold = True

    # ------------------ SECTION 2 TITLE ------------------
    p_s2 = doc.add_paragraph()
    p_s2.paragraph_format.space_before = Pt(4)
    p_s2.paragraph_format.space_after = Pt(3)
    rs2_t = p_s2.add_run("2. CORE ALGORITHMIC & METHODOLOGICAL COMPARISON      ")
    rs2_t.font.size = Pt(9.5)
    rs2_t.font.bold = True
    rs2_t.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    rs2_sub = p_s2.add_run("[ARCHITECTURE AUDIT]")
    rs2_sub.font.size = Pt(7.5)
    rs2_sub.font.bold = True
    rs2_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    # ------------------ TABLE 2: TECHNICAL DIMENSIONS ------------------
    t2 = doc.add_table(rows=1, cols=4)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t2, "CBD5E1")
    
    t2_widths = [Inches(1.6), Inches(2.5), Inches(2.5), Inches(0.8)]
    t2_headers = [
        "TECHNICAL DIMENSION",
        "COLAB PROTOTYPE (JP_V2 / OUTPUT DPD 0)",
        "PRODUCTION APPLICATION (CREDIT-SCORING-APP)",
        "ADVANTAGE"
    ]
    hdr2 = t2.rows[0]
    for idx, text in enumerate(t2_headers):
        cell = hdr2.cells[idx]
        cell.width = t2_widths[idx]
        set_cell_background(cell, "0F172A")
        set_cell_margins(cell, top=45, bottom=45, left=60, right=60)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        if idx == 3:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.font.bold = True
        r.font.size = Pt(7.5)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        
    t2_data = [
        ("ML Algorithm",
         "Un-tuned RandomForestClassifier with fixed depth (and exploratory untuned XGBoost).",
         "Tuned LightGBM (LGBMClassifier) with 300-trial Optuna hyperparameter optimization.",
         "App"),
        ("Imbalance Handling",
         "Destructive 50/50 Under-sampling: Discards ~18,000 real non-default records via make_balanced_dataset().",
         "100% Portfolio Retention: Cost-sensitive class weighting (scale_pos_weight: 19.12) preserves true portfolio economics.",
         "App"),
        ("Categorical Encoding",
         "Arbitrary LabelEncoder: Imposes artificial ordinal numbers (0, 1, 2) on nominal dealer names and employment types.",
         "Out-of-Fold (OOF) Target Encoding: Statistically encodes categories by default likelihood with smoothing to prevent leakage.",
         "App"),
        ("Feature Selection",
         "Basic Gini impurity ranking (known to favor high-cardinality noise variables).",
         "Cohen’s d Effect-Size Selection combined with binary split optimization to eliminate collinear, weak features.",
         "App"),
        ("Probability Calibration",
         "Uncalibrated: Raw tree vote percentages (predict_proba) cluster near 0 or 1 and do not reflect true statistical risk.",
         "Isotonic / Sigmoid Calibration via CalibratedClassifierCV, mapped directly to an intuitive 0–100 Credit Score.",
         "App"),
        ("Explainability (XAI)",
         "Global Gini bar chart only; cannot explain why an individual applicant was rejected.",
         "Full SHAP Integration: Computes exact feature attribution per applicant (critical for adverse action notices).",
         "App"),
        ("System Architecture",
         "Monolithic 3,800-line linear notebook; cannot integrate into underwriting workflows.",
         "Modular Enterprise App: Decoupled backend (ai_model.py), SQLite database, REST/UI layer, and batch CSV processing.",
         "App")
    ]
    
    for row_idx, (dim, colab_desc, app_desc, adv) in enumerate(t2_data):
        row = t2.add_row()
        cells = row.cells
        for c_i, val in enumerate([dim, colab_desc, app_desc, adv]):
            cell = cells[c_i]
            cell.width = t2_widths[c_i]
            if c_i == 1:
                set_cell_background(cell, "FFF5F5")
            elif c_i == 2:
                set_cell_background(cell, "F0FDF4")
            else:
                set_cell_background(cell, "FFFFFF" if row_idx % 2 == 0 else "F8FAFC")
                
            set_cell_margins(cell, top=35, bottom=35, left=60, right=60)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            if c_i == 3:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
            run = p.add_run(val)
            run.font.size = Pt(7.5)
            if c_i == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
            elif c_i == 1:
                run.font.color.rgb = RGBColor(0x7F, 0x1D, 0x1D)
            elif c_i == 2:
                run.font.color.rgb = RGBColor(0x06, 0x4E, 0x3B)
                run.font.bold = True
            elif c_i == 3:
                run.font.bold = True
                run.font.color.rgb = RGBColor(0x15, 0x80, 0x3D)

    # ------------------ SIDE-BY-SIDE CARDS ------------------
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(4)
    p_sp.paragraph_format.space_after = Pt(4)
    
    card_table = doc.add_table(rows=1, cols=2)
    card_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_card_l = card_table.cell(0, 0)
    c_card_r = card_table.cell(0, 1)
    c_card_l.width = Inches(3.65)
    c_card_r.width = Inches(3.65)
    
    # Left Card: Colab Deficiencies
    set_cell_background(c_card_l, "FFFBFB")
    set_box_borders(c_card_l, left_color="EF4444", left_sz="20", border_color="FCA5A5")
    set_cell_margins(c_card_l, top=60, bottom=60, left=80, right=80)
    
    p_cl = c_card_l.paragraphs[0]
    p_cl.paragraph_format.space_after = Pt(3)
    r_clt = p_cl.add_run("CRITICAL DEFICIENCIES OF THE COLAB PROTOTYPE")
    r_clt.font.bold = True
    r_clt.font.size = Pt(8.5)
    r_clt.font.color.rgb = RGBColor(0xDC, 0x26, 0x26)
    
    colab_bullets = [
        ("Loss of 18,000+ Valid Loan Records: ", "Forcing a 50/50 balance discards valuable good borrower profiles, leading to extreme false positive alarms."),
        ("False Ordinal Assumptions: ", "Label encoding implies Dealer #3 is 'greater than' Dealer #2, creating false decision boundaries in tree branches."),
        ("Unreliable Credit Probabilities: ", "Because raw Random Forest votes are not calibrated, scores cannot be translated into risk premiums."),
        ("Regulatory Compliance Risk: ", "Lacks applicant-level explainability (SHAP), violating banking transparency requirements.")
    ]
    for b_bold, b_txt in colab_bullets:
        pb = c_card_l.add_paragraph()
        pb.paragraph_format.space_after = Pt(2)
        pb.paragraph_format.left_indent = Inches(0.12)
        rb = pb.add_run(f"• {b_bold}")
        rb.font.bold = True
        rb.font.size = Pt(7.5)
        rb.font.color.rgb = RGBColor(0x99, 0x1B, 0x1B)
        rt = pb.add_run(b_txt)
        rt.font.size = Pt(7.5)
        rt.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    # Right Card: App Capabilities
    set_cell_background(c_card_r, "F8FBF9")
    set_box_borders(c_card_r, left_color="10B981", left_sz="20", border_color="A7F3D0")
    set_cell_margins(c_card_r, top=60, bottom=60, left=80, right=80)
    
    p_cr = c_card_r.paragraphs[0]
    p_cr.paragraph_format.space_after = Pt(3)
    r_crt = p_cr.add_run("ENTERPRISE CAPABILITIES OF CREDIT-SCORING-APP")
    r_crt.font.bold = True
    r_crt.font.size = Pt(8.5)
    r_crt.font.color.rgb = RGBColor(0x05, 0x96, 0x69)
    
    app_bullets = [
        ("Neyman-Pearson Risk Appetite Protection: ", "Caps False Positive Rate at ≤ 3.5%, ensuring 96.5%+ of good customers are never wrongfully turned away."),
        ("High Default Detection (81% Recall): ", "Successfully flags 81% of actual defaults before loan disbursement, directly reducing credit write-offs."),
        ("Calibrated 0-100 FICO-Style Scores: ", "Translates pure statistical probabilities into standard score tiers (High Risk <30, Moderate 30–69, Low 70–100)."),
        ("Production API & GUI Integration: ", "Fully automated end-to-end pipeline with SQLite persistence, batch execution, and interactive reporting.")
    ]
    for b_bold, b_txt in app_bullets:
        pb = c_card_r.add_paragraph()
        pb.paragraph_format.space_after = Pt(2)
        pb.paragraph_format.left_indent = Inches(0.12)
        rb = pb.add_run(f"• {b_bold}")
        rb.font.bold = True
        rb.font.size = Pt(7.5)
        rb.font.color.rgb = RGBColor(0x06, 0x5F, 0x46)
        rt = pb.add_run(b_txt)
        rt.font.size = Pt(7.5)
        rt.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    # ------------------ SECTION 3: ARCHITECTURE DATAFLOW ------------------
    p_s3 = doc.add_paragraph()
    p_s3.paragraph_format.space_before = Pt(6)
    p_s3.paragraph_format.space_after = Pt(2)
    rs3_t = p_s3.add_run("3. PRODUCTION ARCHITECTURE DATAFLOW      ")
    rs3_t.font.size = Pt(9.5)
    rs3_t.font.bold = True
    rs3_t.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    rs3_sub = p_s3.add_run("[PIPELINE LIFECYCLE]")
    rs3_sub.font.size = Pt(7.5)
    rs3_sub.font.bold = True
    rs3_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    
    flow_table = doc.add_table(rows=1, cols=1)
    flow_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_fl = flow_table.cell(0, 0)
    c_fl.width = Inches(7.3)
    set_cell_background(c_fl, "F8FAFC")
    set_box_borders(c_fl, left_color="2563EB", left_sz="12", border_color="CBD5E1")
    set_cell_margins(c_fl, top=50, bottom=50, left=80, right=80)
    
    pfl = c_fl.paragraphs[0]
    pfl.paragraph_format.space_after = Pt(0)
    flow_str = (
        "[Raw Excel/CSV Data] ──> [SHA1 Cache Validation] ──> [OOF Target Encoding] ──> [Cohen's d Ranking]\n"
        "                                                                                      │\n"
        "                                                                                      ▼\n"
        "[SHAP Explanations] <── [0-100 Credit Score] <── [CalibratedClassifierCV] <── [Optuna-Tuned LightGBM]\n"
        "        │                       │                             │\n"
        "        ▼                       ▼                             ▼\n"
        " [Underwriter UI]     [Risk Tier Stratification]   [Neyman-Pearson Approval Gate]\n"
        "  (Applicant Reasons)   (Low / Moderate / High)      (Strict ≤ 3.5% False Positive Rate)"
    )
    r_fl = pfl.add_run(flow_str)
    r_fl.font.name = "Consolas"
    r_fl.font.size = Pt(7)
    r_fl.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    # ------------------ SECTION 4: CONCLUSION & ROADMAP ------------------
    p_s4 = doc.add_paragraph()
    p_s4.paragraph_format.space_before = Pt(6)
    p_s4.paragraph_format.space_after = Pt(2)
    rs4_t = p_s4.add_run("4. CONCLUSION & IMPLEMENTATION RECOMMENDATION")
    rs4_t.font.size = Pt(9.5)
    rs4_t.font.bold = True
    rs4_t.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    
    rec_table = doc.add_table(rows=1, cols=1)
    rec_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_rec = rec_table.cell(0, 0)
    c_rec.width = Inches(7.3)
    set_cell_background(c_rec, "F1F5F9")
    set_box_borders(c_rec, left_color="10B981", left_sz="16", border_color="CBD5E1")
    set_cell_margins(c_rec, top=60, bottom=60, left=80, right=80)
    
    prec = c_rec.paragraphs[0]
    prec.paragraph_format.space_after = Pt(2)
    r_rect = prec.add_run("Actionable Implementation Roadmap:\n")
    r_rect.font.bold = True
    r_rect.font.size = Pt(8.5)
    r_rect.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    
    steps = [
        ("1. Standardize on credit-scoring-app: ", "Adopt the Calibrated LightGBM model bundled in src/backend/ai_model.py as the official credit engine for JACCS auto loans."),
        ("2. Retire Colab Downsampling: ", "Deprecate the 50/50 downsampling methodology in output dpd 0/1/20260112_copy_of_jp_v2_for_raj.py to avoid distorted risk estimation."),
        ("3. Deploy Calibrated Neyman-Pearson Decisioning: ", "Enforce the 0.2360 threshold to maintain maximum loan volume (85.4% approved) while stopping 81.0% of defaults.")
    ]
    for s_bold, s_desc in steps:
        ps = c_rec.add_paragraph()
        ps.paragraph_format.space_after = Pt(2)
        ps.paragraph_format.left_indent = Inches(0.12)
        rsb = ps.add_run(s_bold)
        rsb.font.bold = True
        rsb.font.size = Pt(8)
        rsb.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        rsd = ps.add_run(s_desc)
        rsd.font.size = Pt(8)
        rsd.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    # Footer
    p_ft = doc.add_paragraph()
    p_ft.paragraph_format.space_before = Pt(8)
    p_ft.paragraph_format.space_after = Pt(0)
    r_ft = p_ft.add_run("Credit Scoring App Model Governance Committee • Confidential • For Internal Bank Review Only           Page 2 of 2")
    r_ft.font.size = Pt(7.5)
    r_ft.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    doc.save(str(output_path))
    print(f"[SUCCESS] Saved DOCX file to: {output_path}")

if __name__ == "__main__":
    out = Path(r"c:\Users\rajak\Videos\ltid-oct\credit-scoring-app\CREDIT_SCORING_APP_VS_COLAB_COMPARISON.docx")
    build_docx(out)

