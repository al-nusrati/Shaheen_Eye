from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER
import pandas as pd
import os
from datetime import datetime

def generate_overall_report(df: pd.DataFrame, output_path: str = "outputs/reports/overall_summary.pdf") -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2.0*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=16, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=6)
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)

    story = []

    # Header
    header_table = Table([[Paragraph("GOVERNMENT OF PAKISTAN - FEDERAL BOARD OF REVENUE", header_style)]], colWidths=[18*cm])
    header_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1a472a')), ('PADDING', (0,0), (-1,-1), 8)]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("TAX INTELLIGENCE – OVERALL POPULATION REPORT", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", styles['Italic']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a472a')))
    story.append(Spacer(1, 0.3*cm))

    # Summary stats
    total = len(df)
    critical = int((df['deviation_score'] >= 80).sum())
    high = int(((df['deviation_score'] >= 65) & (df['deviation_score'] < 80)).sum())
    median_score = df['deviation_score'].median()
    asset_col = 'total_assets_estimated' if 'total_assets_estimated' in df.columns else 'total_assets_val'
    estimated_tax_gap = df[df['deviation_score'] >= 65][asset_col].fillna(0).sum() * 0.15

    stats_data = [
        ["Total Citizens Analyzed", f"{total:,}"],
        ["Critical Risk (≥80)", f"{critical}"],
        ["High Risk (65-79)", f"{high}"],
        ["Median Compliance Score", f"{median_score:.1f}"],
        ["Estimated Tax Gap (15% of high-risk assets)", f"Rs. {estimated_tax_gap/1e9:.2f}B"],
    ]
    stats_table = Table(stats_data, colWidths=[8*cm, 8*cm])
    stats_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e8f0fe')), ('PADDING', (0,0), (-1,-1), 6)]))
    story.append(stats_table)
    story.append(Spacer(1, 0.4*cm))

    # Risk distribution table
    story.append(Paragraph("Risk Score Distribution", styles['Heading4']))
    bins = [0, 25, 45, 65, 80, 101]
    labels = ['COMPLIANT (0-24)', 'LOW (25-44)', 'MEDIUM (45-64)', 'HIGH (65-79)', 'CRITICAL (80-100)']
    df['score_bin'] = pd.cut(df['deviation_score'], bins=bins, labels=labels, right=False)
    dist = df['score_bin'].value_counts().reset_index()
    dist.columns = ['Risk Level', 'Count']
    dist_table = Table([dist.columns.tolist()] + dist.values.tolist(), colWidths=[9*cm, 9*cm])
    dist_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a472a')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('PADDING', (0,0), (-1,-1), 5)]))
    story.append(dist_table)
    story.append(Spacer(1, 0.4*cm))

    # Top 20 highest risk profiles
    story.append(Paragraph("Top 20 High‑Risk Profiles", styles['Heading4']))
    # Handle column name flexibility
    fraud_col = 'top_fraud_flags' if 'top_fraud_flags' in df.columns else 'top_risk_factor'
    top20 = df.nlargest(20, 'deviation_score')[['full_name', 'city', 'deviation_score', 'risk_category', fraud_col]].copy()
    top20.rename(columns={fraud_col: 'Fraud Indicators'}, inplace=True)
    top20_table = Table([top20.columns.tolist()] + top20.values.tolist(), colWidths=[4*cm, 2.5*cm, 2*cm, 2.5*cm, 7*cm])
    top20_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a472a')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('FONTSIZE', (0,0), (-1,-1), 7), ('PADDING', (0,0), (-1,-1), 3)]))
    story.append(top20_table)

    # Most common fraud patterns
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Most Common Fraud Patterns", styles['Heading4']))
    if fraud_col in df.columns:
        all_flags = []
        for flags_str in df[fraud_col].dropna():
            for f in str(flags_str).split(','):
                f = f.strip()
                if f and f not in ('None','nan',''):
                    all_flags.append(f)
        if all_flags:
            flag_counts = pd.Series(all_flags).value_counts().head(10).reset_index()
            flag_counts.columns = ['Fraud Pattern', 'Count']
            flag_table = Table([flag_counts.columns.tolist()] + flag_counts.values.tolist(), colWidths=[10*cm, 6*cm])
            flag_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a472a')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('PADDING', (0,0), (-1,-1), 5)]))
            story.append(flag_table)

    doc.build(story)
    return output_path