from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from datetime import datetime
import matplotlib.pyplot as plt
import networkx as nx

# FBR Dark Green color
FBR_GREEN = colors.HexColor('#1a472a')
FBR_LIGHT_GREEN = colors.HexColor('#40916c')
DANGER_RED = colors.HexColor('#c0392b')
WARNING_ORANGE = colors.HexColor('#e67e22')
TEXT_DARK = colors.HexColor('#1a1a2e')

def generate_static_graph(person_data, output_path):
    """Draws a high-resolution, perfectly aligned tree-graph for PDF reports."""
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
        
        # Clear any existing plots from memory to prevent ghosting
        plt.clf()
        plt.close('all')

        G = nx.Graph()
        
        # --- 1. DATA EXTRACTION & FORMATTING ---
        def fmt_pkr(val):
            val = float(val or 0)
            if val >= 10_000_000:
                return f"Rs.{val/10_000_000:.1f}Cr"
            if val >= 100_000:
                return f"Rs.{val/100_000:.1f}L"
            return f"Rs.{val:,.0f}"

        full_name = person_data.get('full_name', 'Subject')
        p_label = f"{full_name.split()[0]}\n(Subject)"
        
        assets = []
        # Vehicle
        if float(person_data.get('vehicle_count', 0)) > 0:
            cc = int(float(person_data.get('max_vehicle_cc', 0)))
            v_label = f"Vehicle\n{cc}cc"
            G.add_node("V", label=v_label, color='#7f1d1d')
            assets.append("V")
        # Property
        if float(person_data.get('property_count', 0)) > 0:
            p_val = float(person_data.get('total_property_value', 0))
            pr_label = f"Property\n{fmt_pkr(p_val)}"
            G.add_node("P", label=pr_label, color='#052e16')
            assets.append("P")
        # Meter
        if float(person_data.get('avg_monthly_bill_pkr', 0)) > 0:
            bill = float(person_data.get('avg_monthly_bill_pkr', 0))
            m_label = f"Utility\n{fmt_pkr(bill)}/mo"
            G.add_node("M", label=m_label, color='#d97706')
            assets.append("M")
        # FBR
        inc = float(person_data.get('declared_income_pkr', 0))
        f_label = f"FBR Filing\n{fmt_pkr(inc)}"
        G.add_node("F", label=f_label, color='#22c55e' if person_data.get('filer_status')=='ATL' else '#ef4444')
        assets.append("F")

        # Add central node
        G.add_node("Person", label=p_label, color='#3b82f6')
        for a in assets:
            G.add_edge("Person", a)

        # --- 2. HIERARCHICAL POSITIONS (Tree Style) ---
        pos = {"Person": (0, 1)}  # Top Center
        
        if len(assets) > 0:
            # Spread nodes wider to prevent text overlap
            width = 3.5
            x_step = width / (len(assets) - 1) if len(assets) > 1 else 0
            start_x = -width / 2
            for i, node_id in enumerate(assets):
                pos[node_id] = (start_x + (i * x_step), 0)  # Bottom Row

        # --- 3. RENDERING ---
        plt.figure(figsize=(10, 6))
        
        # Draw Edges (BLACK and THICK)
        nx.draw_networkx_edges(G, pos, width=2.5, edge_color='black', alpha=0.8)
        
        # Draw Nodes (LARGE to fit text)
        node_colors = [G.nodes[n]['color'] for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos,
                               node_color=node_colors,
                               node_size=8500,
                               edgecolors='black',
                               linewidths=1.5)
        
        # Draw Labels (Clean and Centered)
        labels = {n: G.nodes[n]['label'] for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=labels,
                                font_size=9,
                                font_color='white',
                                font_weight='bold',
                                font_family='sans-serif')
        
        plt.axis('off')
        plt.margins(0.2)
        plt.savefig(output_path, format="PNG", bbox_inches='tight', dpi=150, transparent=True)
        
        plt.clf()
        plt.close('all')
        return True
    except Exception as e:
        print(f"Graph generation failed: {e}")
        return False

def generate_pdf(person_data: dict, audit_text: str = "", output_dir: str = "outputs/reports") -> str:
    os.makedirs(output_dir, exist_ok=True)
    pid = person_data.get('master_person_id', 'UNKNOWN')
    name = person_data.get('full_name', 'Unknown Person')
    safe_name = name.replace(' ', '_').replace('.', '')
    filename = os.path.join(output_dir, f"FBR_Investigation_{pid}_{safe_name}.pdf")
    
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle('FBRHeader', parent=styles['Normal'],
                                  fontSize=9, textColor=colors.white,
                                  fontName='Helvetica', alignment=TA_CENTER)
    
    title_style = ParagraphStyle('Title', parent=styles['Normal'],
                                  fontSize=16, textColor=TEXT_DARK,
                                  fontName='Helvetica-Bold', alignment=TA_CENTER,
                                  spaceAfter=6)
    
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                    fontSize=10, textColor=colors.HexColor('#666666'),
                                    fontName='Helvetica', alignment=TA_CENTER,
                                    spaceAfter=4)
    
    section_header_style = ParagraphStyle('SectionHeader', parent=styles['Normal'],
                                          fontSize=11, textColor=colors.white,
                                          fontName='Helvetica-Bold', spaceAfter=4,
                                          spaceBefore=8)
    
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                fontSize=10, textColor=TEXT_DARK,
                                fontName='Helvetica', spaceAfter=4, leading=14)
    
    audit_style = ParagraphStyle('Audit', parent=styles['Normal'],
                                 fontSize=10, textColor=TEXT_DARK,
                                 fontName='Helvetica', spaceAfter=6, leading=16,
                                 leftIndent=10, rightIndent=10)
    
    story = []
    
    score = person_data.get('deviation_score', 0)
    risk_cat = person_data.get('risk_category', 'UNKNOWN')
    risk_color = DANGER_RED if score >= 80 else WARNING_ORANGE if score >= 65 else colors.blue
    
    # ---- HEADER ----
    header_table_data = [[
        Paragraph("GOVERNMENT OF PAKISTAN", header_style),
        Paragraph("FEDERAL BOARD OF REVENUE", header_style),
        Paragraph("Financial Monitoring Unit (FMU)", header_style),
    ]]
    header_table = Table(header_table_data, colWidths=[6*cm, 6*cm, 6*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), FBR_GREEN),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ---- CLASSIFICATION BANNER ----
    conf_style = ParagraphStyle('Conf', parent=styles['Normal'],
                                fontSize=10, textColor=colors.white,
                                fontName='Helvetica-Bold', alignment=TA_CENTER)
    conf_table = Table([[Paragraph("⚠ CONFIDENTIAL — INTELLIGENCE & INVESTIGATION WING — AUTHORIZED ACCESS ONLY ⚠", conf_style)]],
                       colWidths=[18*cm])
    conf_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DANGER_RED),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(conf_table)
    story.append(Spacer(1, 0.4*cm))
    
    # ---- REPORT TITLE ----
    story.append(Paragraph("TAX COMPLIANCE INVESTIGATION REPORT", title_style))
    story.append(Paragraph(f"Case ID: {pid} | Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", subtitle_style))
    story.append(Paragraph("Income Tax Ordinance, 2001 — Intelligence & Investigation Wing", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=FBR_GREEN))
    story.append(Spacer(1, 0.3*cm))
    
    # ---- RISK SCORE BOX ----
    score_style = ParagraphStyle('Score', parent=styles['Normal'],
                                 fontSize=28, leading=34,
                                 textColor=risk_color,
                                 fontName='Helvetica-Bold', alignment=TA_CENTER,
                                 spaceAfter=8)
    score_label_style = ParagraphStyle('ScoreLabel', parent=styles['Normal'],
                                       fontSize=11, textColor=TEXT_DARK,
                                       fontName='Helvetica', alignment=TA_CENTER)
    score_table = Table([
        [Paragraph(name.upper(), title_style)],
        [Paragraph(f"{score:.0f} / 100", score_style)],
        [Paragraph(f"COMPLIANCE DEVIATION INDEX — {risk_cat}", score_label_style)],
    ], colWidths=[18*cm])
    score_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 2, risk_color),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fff8f8') if score >= 80 else colors.HexColor('#fffdf0')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.4*cm))
    
    # ---- SUBJECT IDENTITY ----
    def section_header(text):
        t = Table([[Paragraph(f"  {text}", section_header_style)]], colWidths=[18*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), FBR_GREEN),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        return t
    
    story.append(section_header("I. SUBJECT IDENTIFICATION"))
    story.append(Spacer(1, 0.2*cm))
    
    safe_address = str(person_data.get('reported_address', 'N/A'))
    if safe_address.lower() == 'nan':
        safe_address = 'N/A'
    address_paragraph = Paragraph(safe_address, body_style)
    
    safe_income = str(person_data.get('income_source', 'N/A'))
    if safe_income.lower() == 'nan':
        safe_income = 'N/A'

    id_data = [
        ["Full Name:", name, "NTN/FBR-ID:", person_data.get('fbr_id','N/A')],
        ["City:", person_data.get('city','N/A'), "ATL Status:", person_data.get('filer_status','N/A')],
        ["Address:", address_paragraph, "Occupation:", person_data.get('occupation','N/A')],
        ["Phone:", person_data.get('phone_number','N/A'), "Years Non-ATL:", str(person_data.get('years_as_nonfiler',0))],
        ["Income Source:", safe_income, "Wealth Source:", person_data.get('wealth_source','N/A')],
    ]
    id_table = Table(id_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
    id_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f0f0')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f0f0f0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('TEXTCOLOR', (1,1), (1,1),
         colors.HexColor('#c0392b') if person_data.get('filer_status')=='Non-ATL' else colors.HexColor('#27ae60')),
    ]))
    story.append(id_table)
    story.append(Spacer(1, 0.3*cm))

    # ---- NETWORK GRAPH IMAGE ----
    graph_img_path = os.path.join(output_dir, f"temp_graph_{pid}.png")
    if generate_static_graph(person_data, graph_img_path):
        story.append(section_header("II. FINANCIAL FOOTPRINT NETWORK"))
        story.append(Spacer(1, 0.2*cm))
        img = Image(graph_img_path, width=12*cm, height=8.4*cm)
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Spacer(1, 0.3*cm))

    # ---- ASSET INVENTORY ----
    story.append(section_header("III. DECLARED vs ESTIMATED ASSET INVENTORY"))
    story.append(Spacer(1, 0.2*cm))
    
    declared = person_data.get('declared_income_pkr', 0)
    lifestyle = person_data.get('lifestyle_cost_annual', person_data.get('avg_monthly_bill_pkr', 0) * 12)
    total_assets = person_data.get('total_assets_estimated', 0)
    
    asset_data = [
        ["Asset Category", "Details", "Estimated Value (PKR)", "Declared (PKR)"],
        ["Declared Annual Income", person_data.get('income_source','N/A'), "—", f"Rs. {declared:,.0f}"],
        ["Vehicle(s)", f"{person_data.get('vehicle_make_model','N/A')} ({person_data.get('max_vehicle_cc',0)}cc) x{person_data.get('vehicle_count',0)}",
         f"Rs. {person_data.get('total_vehicle_value', person_data.get('max_vehicle_cc',0)*3000):,.0f}", "—"],
        ["Property/Real Estate", f"{person_data.get('property_count',0)} properties | {person_data.get('area_marla',0)} marla | {person_data.get('registry_type','N/A')}",
         f"Rs. {person_data.get('total_property_value',0):,.0f}", f"Rs. {person_data.get('property_value_pkr',0):,.0f}"],
        ["Utility Consumption", f"Avg Rs. {person_data.get('avg_monthly_bill_pkr',0):,.0f}/month",
         f"Rs. {lifestyle:,.0f}/year", "—"],
        ["TOTAL ESTIMATED ASSETS", "", f"Rs. {total_assets:,.0f}", f"Rs. {declared:,.0f}"],
        ["DISCREPANCY RATIO", "", f"{lifestyle/max(declared,1):.1f}x annual income", ""],
    ]
    
    asset_table = Table(asset_data, colWidths=[4.5*cm, 6*cm, 4*cm, 3.5*cm])
    asset_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), FBR_GREEN),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-2), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-2), (-1,-1), colors.HexColor('#fff3cd')),
        ('TEXTCOLOR', (2,-2), (2,-1), risk_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (2,0), (3,-1), 'RIGHT'),
    ]))
    story.append(asset_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ---- FRAUD FLAGS ----
    story.append(section_header("IV. FORENSIC FRAUD MODULES TRIGGERED"))
    story.append(Spacer(1, 0.2*cm))
    
    flags = str(person_data.get('top_fraud_flags','')).split(',')
    flag_refs = {
        'Benami Proxy': 'Benami Transactions (Prohibition) Act 2017, Section 2(9)',
        'DC Rate Fraud': 'ITO 2001 Section 68 (Fair Market Value)',
        'File Trading': 'FBR Property Documentation Requirements',
        'Section 111 Abuse': 'ITO 2001 Section 111(4)',
        'Agri Shield': 'ITO 2001 Section 41 (Agricultural Income)',
        'Gift Declaration': 'ITO 2001 Section 39 (Income from Other Sources)',
        'Hawala Signature': 'Anti-Money Laundering Act 2010',
        'Non-ATL Surcharge': 'ITO 2001 Non-Filer Surcharge Provisions',
        'Illegal Society': 'CDA Ordinance 1960 / LDA Act 1975',
        'Vehicle Underinvoicing': 'Customs Act 1969 + AML Act 2010',
    }
    
    flag_data = [["#", "Fraud Pattern Detected", "Legal Reference", "Risk Points"]]
    for i, flag in enumerate(flags, 1):
        flag = flag.strip()
        if flag and flag not in ['None', 'nan', '']:
            ref = flag_refs.get(flag, 'ITO 2001 Section 111')
            pts = person_data.get('forensic_breakdown', {}).get(flag.lower().replace(' ','_'), 30)
            flag_data.append([str(i), flag, ref, str(pts)])
    
    if len(flag_data) > 1:
        flag_table = Table(flag_data, colWidths=[0.8*cm, 5*cm, 9*cm, 2*cm])
        flag_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), FBR_GREEN),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('PADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f8f8')]),
        ]))
        story.append(flag_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ---- AI AUDIT TRAIL ----
    story.append(section_header("V. INVESTIGATOR'S REPORT (AI-ASSISTED ANALYSIS)"))
    story.append(Spacer(1, 0.2*cm))
    
    if audit_text:
        paragraphs = audit_text.split('\n')
        for para in paragraphs:
            para = para.strip()
            if para:
                story.append(Paragraph(para, audit_style))
                story.append(Spacer(1, 0.15*cm))
    else:
        story.append(Paragraph("Audit trail not generated. Please run the AI analysis from the dashboard.", audit_style))
    
    story.append(Spacer(1, 0.3*cm))
    
    # ---- ENFORCEMENT DIRECTIVE ----
    story.append(section_header("VI. ENFORCEMENT DIRECTIVE"))
    story.append(Spacer(1, 0.2*cm))
    
    flags_list = str(person_data.get('top_fraud_flags',''))
    
    if score >= 80:
        action = "<b>CRITICAL NON-COMPLIANCE DETECTED:</b> System mandates immediate issuance of Show-Cause Notice under Section 122(9) of the Income Tax Ordinance, 2001. "
        if "Benami" in flags_list:
            action += "<b>Benami indicators confirmed:</b> Refer to Benami Zone for immediate asset freezing under Section 24 of the Benami Act 2017. "
        if "Dc Underinvoicing" in flags_list or "DC Rate" in flags_list:
            action += "<b>Valuation Fraud:</b> Re-calculate tax liability based on Fair Market Value under Section 68. "
        action += "Refer case to FIA for Anti-Money Laundering investigation."
    elif score >= 65:
        action = "<b>HIGH RISK PROFILE:</b> Initiate mandatory audit under Section 114. Subject is required to provide physical source of wealth documentation for all identified assets within 15 days."
    elif score >= 45:
        action = "<b>MONITORING:</b> Add subject to FBR Watchlist. Issue notice for voluntary wealth statement reconciliation."
    else:
        action = "<b>COMPLIANT:</b> No enforcement action required at this stage. Profile remains within acceptable deviation parameters."
    
    action_table = Table([[Paragraph(action, audit_style)]], colWidths=[18*cm])
    action_color = colors.HexColor('#fff8f8') if score >= 80 else colors.HexColor('#f8f9fa')
    action_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.5, risk_color),
        ('BACKGROUND', (0,0), (-1,-1), action_color),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(action_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ---- FOOTER ----
    story.append(HRFlowable(width="100%", thickness=1, color=FBR_GREEN))
    footer_data = [[
        Paragraph(f"Case ID: {pid}", ParagraphStyle('f', fontSize=8, textColor=colors.grey)),
        Paragraph(f"Generated by Shaheen-Eye P-FIS | {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                  ParagraphStyle('f', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)),
        Paragraph("CONFIDENTIAL — FMU, Govt. of Pakistan",
                  ParagraphStyle('f', fontSize=8, textColor=colors.grey, alignment=TA_RIGHT)),
    ]]
    footer = Table(footer_data, colWidths=[6*cm, 6*cm, 6*cm])
    footer.setStyle(TableStyle([('PADDING', (0,0), (-1,-1), 4)]))
    story.append(footer)
    
    doc.build(story)
    return filename