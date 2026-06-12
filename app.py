import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import pickle
import json
import os
import time
import re
import shutil
from datetime import datetime
from pyvis.network import Network
import streamlit.components.v1 as components
from overall_report import generate_overall_report

# ── must be first streamlit call ─────────────────────────────
st.set_page_config(
    page_title="Shaheen-Eye | P-FIS",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── global CSS (sidebar contrast fix) ────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0a0e1a; color: #e2e8f0; }
[data-testid="stSidebar"] { background-color: #0f1623; border-right: 1px solid #1e2d40; }
[data-testid="stSidebar"] .stRadio label { color: #f1f5f9 !important; font-size: 14px; font-weight: 500; }
.fbr-header { background: linear-gradient(135deg, #0f2a1a 0%, #1a3a28 50%, #0f2a1a 100%); border-bottom: 2px solid #22c55e; padding: 14px 24px; margin-bottom: 24px; border-radius: 0 0 8px 8px; }
.fbr-header h1 { color: #bbf7d0; font-size: 15px; font-weight: 600; margin: 0; }
.fbr-header p { color: #4ade80; font-size: 10px; margin: 3px 0 0 0; }
.metric-card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 18px 20px; text-align: center; }
.metric-card.critical { border-left: 3px solid #ef4444; }
.metric-card.warning  { border-left: 3px solid #f59e0b; }
.metric-card.info     { border-left: 3px solid #3b82f6; }
.metric-card.success  { border-left: 3px solid #22c55e; }
.metric-val { font-size: 28px; font-weight: 700; margin: 0; }
.metric-lbl { color: #6b7280; font-size: 11px; margin: 4px 0 0; }
.section-title { font-size: 14px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; border-bottom: 1px solid #1f2937; }
.profile-header { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 20px 24px; margin-bottom: 16px; }
.audit-box { background: #0a0e1a; border: 1px solid #1f2937; border-radius: 8px; padding: 16px; font-size: 13px; line-height: 1.7; color: #cbd5e1; }
.formula-box { background: #0d1117; border: 1px solid #1f2937; border-radius: 8px; padding: 14px; font-family: 'Courier New', monospace; font-size: 12px; }
.flag-item { background: #1a0a0a; border-left: 3px solid #ef4444; padding: 6px 12px; margin: 4px 0; border-radius: 0 6px 6px 0; font-size: 12px; color: #fca5a5; }
.query-result-box { background: #0f1b2d; border: 1px solid #1e3a5f; border-left: 3px solid #3b82f6; padding: 12px 16px; border-radius: 0 8px 8px 0; font-size: 13px; color: #93c5fd; margin: 8px 0 16px; }
#MainMenu, footer, .stDeployButton { visibility: hidden; }
.stPlotlyChart { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── FBR header ───────────────────────────────────────────────
st.markdown("""
<div class="fbr-header">
    <h1>🦅 SHAHEEN-EYE | Pakistan Financial Intelligence Suite (P-FIS) v1.0</h1>
    <p>Financial Monitoring Unit (FMU) — Government of Pakistan · Federal Board of Revenue — Intelligence & Investigation Wing · CLASSIFICATION: CONFIDENTIAL · AUTHORIZED ACCESS ONLY</p>
</div>
""", unsafe_allow_html=True)

# ── Session management functions (kept for backward compatibility, but no session dropdown) ──
SESSIONS_DIR = "outputs/sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

def save_current_session():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_folder = os.path.join(SESSIONS_DIR, timestamp)
    os.makedirs(session_folder, exist_ok=True)
    for fname in ["scored_entities.csv", "master_entities.csv", "shaheen_graph.pkl", "audit_trails.json"]:
        src = f"outputs/{fname}"
        if os.path.exists(src):
            shutil.copy(src, os.path.join(session_folder, fname))
    return timestamp

# ── data loaders (always read fresh from disk) ───────────────
def load_data():
    scored = "outputs/scored_entities.csv"
    master = "outputs/master_entities.csv"
    try:
        df = pd.read_csv(scored)
        if 'top_risk_factor' in df.columns and 'top_fraud_flags' not in df.columns:
            df = df.rename(columns={'top_risk_factor': 'top_fraud_flags'})
        if 'total_assets_val' in df.columns and 'total_assets_estimated' not in df.columns:
            df = df.rename(columns={'total_assets_val': 'total_assets_estimated'})
        if 'city' not in df.columns and os.path.exists(master):
            m = pd.read_csv(master)[['master_person_id', 'city']]
            df = df.merge(m, on='master_person_id', how='left')
        return df
    except FileNotFoundError:
        return pd.DataFrame()

def load_graph():
    path = "outputs/shaheen_graph.pkl"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

def load_audit():
    path = "outputs/audit_trails.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ── colour helpers ────────────────────────────────────────────
RISK_COLORS = {
    "CRITICAL": "#ef4444",
    "HIGH":     "#f59e0b",
    "MEDIUM":   "#3b82f6",
    "LOW":      "#22d3ee",
    "COMPLIANT":"#22c55e",
}
def risk_color(cat):
    return RISK_COLORS.get(str(cat).upper(), "#6b7280")
def score_color(s):
    s = float(s) if s else 0
    if s >= 80: return "#ef4444"
    if s >= 65: return "#f59e0b"
    if s >= 45: return "#3b82f6"
    if s >= 25: return "#22d3ee"
    return "#22c55e"
PLOTLY_DARK = dict(
    plot_bgcolor="#111827",
    paper_bgcolor="#111827",
    font_color="#94a3b8",
    xaxis=dict(gridcolor="#1f2937", linecolor="#374151"),
    yaxis=dict(gridcolor="#1f2937", linecolor="#374151"),
)

# ── Query helpers ─────────────────────────────────────────────
def sanitize_query(query: str) -> str:
    dangerous = re.compile(r"\b(select|insert|update|delete|drop|union|create|alter|truncate|exec|declare|xp_cmdshell)\b", re.IGNORECASE)
    if dangerous.search(query):
        return None
    if re.search(r"(--|;|'|\"|\|)", query):
        return None
    cleaned = re.sub(r"[^a-zA-Z0-9\s\u0600-\u06FF\.,\-\?]", " ", query)
    return cleaned.strip()
URDU_TO_EN = {
    "لاہور": "lahore", "کراچی": "karachi", "اسلام آباد": "islamabad",
    "گاڑی": "vehicle", "کار": "car", "پراپرٹی": "property", "غیر فائلر": "non-filer"
}
def translate_urdu(txt: str) -> str:
    for ur, en in URDU_TO_EN.items():
        txt = txt.replace(ur, en)
    return txt

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR (no session dropdown – only navigation and live stats)
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("<p style='color:#4ade80;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px'>Navigation</p>", unsafe_allow_html=True)
    page = st.radio("", [
        "🏠 National Dashboard",
        "📊 Risk Leaderboard",
        "🔍 Individual Profile",
        "🤖 Intelligence Query",
        "📤 Live Data Upload",
    ], label_visibility="collapsed")

    st.markdown("<hr style='border-color:#1f2937;margin:16px 0'>", unsafe_allow_html=True)

    # --- Hard Reset button (clears all caches and reloads) ---
    if st.button("💣 Hard Reset (Clear all caches & reload)", key="hard_reset"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    # --- Live stats (fresh every time) ---
    df = load_data()
    if not df.empty:
        total = len(df)
        critical = int((df['deviation_score'] >= 80).sum())
        high = int(((df['deviation_score'] >= 65) & (df['deviation_score'] < 80)).sum())
        st.markdown("<p style='color:#6b7280;font-size:10px;font-weight:600;text-transform:uppercase'>Live Stats</p>", unsafe_allow_html=True)
        for label, val, col in [
            ("Citizens Analyzed", f"{total:,}", "#94a3b8"),
            ("🔴 Critical Risk", str(critical), "#ef4444"),
            ("🟡 High Risk", str(high), "#f59e0b"),
        ]:
            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1f2937'><span style='color:#6b7280;font-size:12px'>{label}</span><span style='color:{col};font-weight:600'>{val}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#6b7280;font-size:10px'>{total:,} profiles loaded</p>", unsafe_allow_html=True)
    else:
        st.info("No data found. Use Live Data Upload to load files.")

    st.markdown("<hr style='border-color:#1f2937;margin:16px 0'>", unsafe_allow_html=True)
    st.markdown("<p style='color:#374151;font-size:10px;text-align:center'>Shaheen-Eye P-FIS v1.0<br>FMU — Govt. of Pakistan<br>© 2025 — CONFIDENTIAL</p>", unsafe_allow_html=True)

# ── Load data for pages (fresh) ──────────────────────────────
df = load_data()
G = load_graph()
audits = load_audit()

# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 – NATIONAL DASHBOARD (unchanged)
# ════════════════════════════════════════════════════════════════════════════
if "National" in page:
    if df.empty:
        st.warning("No data loaded. Use Live Data Upload to load files.")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    tax_gap = float(df[df['deviation_score'] >= 65]['total_assets_estimated'].fillna(0).sum()) * 0.15
    rings = 0
    if G is not None:
        try:
            comms = list(nx.connected_components(G))
            rings = sum(1 for c in comms if len([n for n in c if G.nodes[n].get('type') == 'Person']) >= 3)
        except Exception:
            rings = 6
    cards = [
        (c1, "critical", "#ef4444", str(int((df['deviation_score']>=80).sum())), "🔴 Critical Risk Profiles"),
        (c2, "warning", "#f59e0b", f"Rs. {tax_gap/1e9:.1f}B", "⚠️ Estimated Tax Gap"),
        (c3, "info", "#3b82f6", f"{len(df):,}", "📊 Citizens Analyzed"),
        (c4, "success", "#22c55e", str(rings), "🕸️ Fraud Rings Detected"),
    ]
    for col, cls, clr, val, lbl in cards:
        with col:
            st.markdown(f"<div class='metric-card {cls}'><p class='metric-val' style='color:{clr}'>{val}</p><p class='metric-lbl'>{lbl}</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_hist, col_city = st.columns([3,2])
    with col_hist:
        st.markdown("<p class='section-title'>National Risk Score Distribution</p>", unsafe_allow_html=True)
        fig_h = px.histogram(df, x="deviation_score", nbins=25, color_discrete_sequence=["#3b82f6"], labels={"deviation_score": "Compliance Deviation Score", "count": "Citizens"}, template="plotly_dark")
        fig_h.add_vline(x=65, line_dash="dash", line_color="#f59e0b", annotation_text="High Risk", annotation_font_color="#f59e0b")
        fig_h.add_vline(x=80, line_dash="dash", line_color="#ef4444", annotation_text="Critical", annotation_font_color="#ef4444")
        fig_h.update_layout(**PLOTLY_DARK, height=280, margin=dict(t=10,b=10))
        st.plotly_chart(fig_h, use_container_width=True)

    with col_city:
        st.markdown("<p class='section-title'>Risk by City</p>", unsafe_allow_html=True)
        if 'city' in df.columns:
            city_df = df.groupby('city')['deviation_score'].mean().reset_index().sort_values('deviation_score')
            fig_c = px.bar(city_df, x='deviation_score', y='city', orientation='h', color='deviation_score', color_continuous_scale=["#22c55e","#f59e0b","#ef4444"], template="plotly_dark", labels={"deviation_score":"Avg Score","city":""})
            fig_c.update_layout(**PLOTLY_DARK, height=280, coloraxis_showscale=False, margin=dict(t=10,b=10))
            st.plotly_chart(fig_c, use_container_width=True)

    col_map, col_pie = st.columns([3,2])
    with col_map:
        st.markdown("<p class='section-title'>🇵🇰 Pakistan Risk Heatmap</p>", unsafe_allow_html=True)
        city_coords = {
            "Lahore": (31.5204, 74.3587), "Karachi": (24.8607, 67.0011), "Islamabad": (33.6844, 73.0479),
            "Rawalpindi": (33.6007, 73.0679), "Faisalabad": (31.4504, 73.1350), "Multan": (30.1575, 71.5249),
            "Peshawar": (34.0151, 71.5249), "Quetta": (30.1798, 66.9750), "Gujranwala": (32.1877, 74.1945),
            "Sialkot": (32.4945, 74.5229)
        }
        if 'city' in df.columns:
            avg_by_city = df.groupby('city')['deviation_score'].mean().reset_index()
            map_rows = []
            for _, r in avg_by_city.iterrows():
                if r['city'] in city_coords:
                    lat, lon = city_coords[r['city']]
                    map_rows.append({"city": r['city'], "lat": lat, "lon": lon, "score": r['deviation_score']})
            if map_rows:
                mdf = pd.DataFrame(map_rows)
                fig_m = px.scatter_geo(mdf, lat='lat', lon='lon', size='score', color='score', hover_name='city', color_continuous_scale=["#22c55e","#f59e0b","#ef4444"], size_max=15, scope="asia", template="plotly_dark")
                fig_m.update_geos(center={"lat":30.3753,"lon":69.3451}, projection_scale=5.5, bgcolor="#111827", landcolor="#1f2937", oceancolor="#111827", lakecolor="#111827", showcountries=True, countrycolor="#374151")
                fig_m.update_layout(height=300, paper_bgcolor="#111827", font_color="#94a3b8", coloraxis_showscale=False, margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig_m, use_container_width=True)

    with col_pie:
        st.markdown("<p class='section-title'>Risk Category Breakdown</p>", unsafe_allow_html=True)
        if 'risk_category' in df.columns:
            rc = df['risk_category'].value_counts()
            fig_p = px.pie(values=rc.values, names=rc.index, color=rc.index, color_discrete_map=RISK_COLORS, template="plotly_dark", hole=0.45)
            fig_p.update_layout(paper_bgcolor="#111827", font_color="#94a3b8", height=300, showlegend=True, legend=dict(orientation="v", x=1.0, y=0.5, font=dict(size=11)), margin=dict(t=10,b=10))
            st.plotly_chart(fig_p, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p class='section-title'>Most Common Fraud Patterns Detected</p>", unsafe_allow_html=True)
    if 'top_fraud_flags' in df.columns:
        all_flags = []
        for flags_str in df['top_fraud_flags'].dropna():
            for f in str(flags_str).split(','):
                f = f.strip()
                if f and f not in ('None','nan',''):
                    all_flags.append(f)
        if all_flags:
            flag_counts = pd.Series(all_flags).value_counts().head(10).reset_index()
            flag_counts.columns = ['Fraud Pattern', 'Count']
            fig_f = px.bar(flag_counts.sort_values('Count'), x='Count', y='Fraud Pattern', orientation='h', color='Count', color_continuous_scale=["#1d4ed8","#dc2626"], template="plotly_dark", labels={"Count":"Profiles Flagged"})
            fig_f.update_layout(**PLOTLY_DARK, height=320, coloraxis_showscale=False, margin=dict(t=10,b=10))
            st.plotly_chart(fig_f, use_container_width=True)

    col_btn1, col_btn2, _ = st.columns([1,1,3])
    with col_btn1:
        if st.button("📊 Export Overall Intelligence Report (PDF)", type="primary"):
            try:
                if df.empty:
                    st.error("No data to generate report.")
                else:
                    report_df = df.copy()
                    if 'top_fraud_flags' not in report_df.columns and 'top_risk_factor' not in report_df.columns:
                        report_df['top_fraud_flags'] = "No fraud data"
                    pdf_path = generate_overall_report(report_df)
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Overall Report",
                            data=f.read(),
                            file_name="FBR_Overall_Report.pdf",
                            mime="application/pdf",
                            key="download_overall_report"
                        )
            except Exception as e:
                st.error(f"Report generation error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 – RISK LEADERBOARD (unchanged)
# ════════════════════════════════════════════════════════════════════════════
elif "Leaderboard" in page:
    if df.empty:
        st.warning("No data. Use Live Data Upload to load files.")
        st.stop()

    st.markdown("<p class='section-title'>Risk Intelligence Leaderboard</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#4b5563;font-size:12px;margin-bottom:16px'>Select a row to open the full profile investigation.</p>", unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        cities = sorted(df['city'].dropna().unique().tolist()) if 'city' in df.columns else []
        city_f = st.multiselect("🏙️ City", cities, key="lb_city")
    with fc2:
        risk_f = st.multiselect("⚠️ Risk Level", ['CRITICAL','HIGH','MEDIUM','LOW','COMPLIANT'], key="lb_risk")
    with fc3:
        atl_f = st.multiselect("📋 ATL Status", ['ATL','Non-ATL'], key="lb_atl")
    with fc4:
        min_s = st.slider("Min Score", 0, 100, 0, key="lb_score")

    fdf = df.copy()
    if city_f: fdf = fdf[fdf['city'].isin(city_f)]
    if risk_f: fdf = fdf[fdf['risk_category'].isin(risk_f)]
    if atl_f: fdf = fdf[fdf['filer_status'].isin(atl_f)]
    fdf = fdf[fdf['deviation_score'] >= min_s]
    fdf = fdf.sort_values('deviation_score', ascending=False).reset_index(drop=True)
    fdf.index += 1

    st.markdown(f"<p style='color:#6b7280;font-size:12px'>Showing <b style='color:#94a3b8'>{len(fdf)}</b> profiles</p>", unsafe_allow_html=True)

    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
        disp = ['full_name','city','deviation_score','risk_category','filer_status','declared_income_pkr','vehicle_make_model','top_fraud_flags']
        avail = [c for c in disp if c in fdf.columns]
        gb = GridOptionsBuilder.from_dataframe(fdf[avail])
        gb.configure_selection('single', use_checkbox=False)
        gb.configure_grid_options(domLayout='normal', rowHeight=35)
        gb.configure_column("deviation_score", headerName="⚡ Score",
            cellStyle=JsCode("function(p){var v=p.value;if(v>=80) return {background:'#1f0707',color:'#ef4444',fontWeight:'bold'};if(v>=65) return {background:'#1f1207',color:'#f59e0b'};if(v>=45) return {background:'#07101f',color:'#3b82f6'};return {background:'#071f10',color:'#22c55e'};}"))
        gb.configure_column("risk_category", headerName="🚨 Level",
            cellRenderer=JsCode("function(p){var m={'CRITICAL':'#ef4444','HIGH':'#f59e0b','MEDIUM':'#3b82f6','LOW':'#22d3ee','COMPLIANT':'#22c55e'};var c=m[p.value]||'#6b7280';var tc=(p.value==='HIGH')?'black':'white';return `<span style=\"background:${c};color:${tc};padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700\">${p.value}</span>`;}"))
        gb.configure_column("declared_income_pkr", headerName="Declared Income", valueFormatter=JsCode("function(p){return 'Rs. '+(p.value||0).toLocaleString();}"))
        gb.configure_column("full_name", headerName="👤 Name")
        gb.configure_column("city", headerName="🏙️ City")
        gb.configure_column("filer_status", headerName="ATL")
        gb.configure_column("vehicle_make_model", headerName="Vehicle")
        gb.configure_column("top_fraud_flags", headerName="🔍 Fraud Detected")
        resp = AgGrid(fdf[avail], gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, height=600, theme="alpine-dark")

        sel = resp.get('selected_rows', [])
        if sel is not None and len(sel) > 0:
            if isinstance(sel, pd.DataFrame):
                row_sel = sel.iloc[0]
            else:
                row_sel = sel[0]
            name = row_sel.get('full_name', '')
            match = df[df['full_name'] == name]
            if len(match) > 0:
                st.session_state['sel_pid'] = match.iloc[0]['master_person_id']
                st.session_state['selected_name'] = name
                st.success(f"✅ Selected: **{name}** — navigate to Individual Profile")
    except ImportError:
        st.dataframe(fdf, use_container_width=True, height=600)
        st.info("For interactive table: pip install streamlit-aggrid")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 – INDIVIDUAL PROFILE (with fixed timeline)
# ════════════════════════════════════════════════════════════════════════════
elif "Individual" in page:
    if df.empty:
        st.warning("No data. Use Live Data Upload to load files.")
        st.stop()

    names = df['full_name'].drop_duplicates().tolist()
    default = 0
    if 'sel_pid' in st.session_state:
        pid_sel = st.session_state['sel_pid']
        m = df[df['master_person_id'] == pid_sel]
        if len(m) > 0 and m.iloc[0]['full_name'] in names:
            default = names.index(m.iloc[0]['full_name'])

    sel_name = st.selectbox("Select citizen profile", names, index=default)
    person = df[df['full_name'] == sel_name].iloc[0]
    pid = person['master_person_id']
    score = float(person.get('deviation_score', 0))
    flags_raw = str(person.get('top_fraud_flags', ''))
    cat = str(person.get('risk_category', 'UNKNOWN')).upper()
    clr = risk_color(cat)

    st.markdown(f"<div class='profile-header' style='border-left:4px solid {clr}'><div style='display:flex;justify-content:space-between;align-items:start'><div><h2 style='color:{clr};margin:0;font-size:22px'>{sel_name}</h2><p style='color:#6b7280;margin:4px 0;font-size:13px'>NTN/FBR-ID: {person.get('master_person_id','N/A')} &nbsp;·&nbsp; City: {person.get('city','N/A')} &nbsp;·&nbsp; Occupation: {person.get('occupation','N/A')} &nbsp;·&nbsp; ATL: <b style='color:{'#22c55e' if person.get('filer_status')=='ATL' else '#ef4444'}'>{person.get('filer_status','N/A')}</b></p></div><div style='text-align:right'><p style='font-size:48px;font-weight:800;color:{clr};margin:0;line-height:1'>{score:.0f}<span style='font-size:16px;color:#4b5563'>/100</span></p><span style='background:{clr};color:{'black' if cat=='HIGH' else 'white'};padding:4px 14px;border-radius:12px;font-size:11px;font-weight:700'>{cat}</span></div></div></div>", unsafe_allow_html=True)

    col_graph, col_intel = st.columns([1,1])
    with col_graph:
        st.markdown("<p class='section-title'>Financial Footprint Graph</p>", unsafe_allow_html=True)
        net = Network(height="420px", width="100%", bgcolor="#111827", font_color="#e2e8f0", directed=False)
        net.set_options("""{"physics":{"stabilization":{"iterations":80},"barnesHut":{"gravitationalConstant":-8000}},"nodes":{"borderWidth":2,"shadow":{"enabled":true}},"edges":{"shadow":{"enabled":true},"smooth":{"type":"continuous"}}}""")
        net.add_node(pid, label=sel_name.split()[0], color={"background": clr, "border": "#ffffff", "highlight": {"background": clr}}, size=45, title=f"<b>{sel_name}</b><br>Score: {score:.0f}<br>Status: {cat}", shape="dot")
        if float(person.get('vehicle_count',0)) > 0:
            v_id = f"V_{pid}"
            net.add_node(v_id, label=f"🚗 {str(person.get('vehicle_make_model','Vehicle'))[:18]}", color={"background":"#7f1d1d","border":"#ef4444"}, size=28, title=f"<b>Vehicle</b><br>{person.get('vehicle_make_model','N/A')}<br>CC: {person.get('max_vehicle_cc',0)}<br>Import: {person.get('import_type','N/A')}", shape="diamond")
            net.add_edge(pid, v_id, label="OWNS", color="#ef4444", width=2)
        if float(person.get('property_count',0)) > 0:
            p_id = f"P_{pid}"
            net.add_node(p_id, label=f"🏠 Property\n{person.get('city','')}", color={"background":"#052e16","border":"#22c55e"}, size=28, title=f"<b>Property</b><br>Value: Rs.{float(person.get('total_property_value',0)):,.0f}<br>Type: {person.get('registry_type','N/A')}<br>NOC: {person.get('noc_status','N/A')}", shape="square")
            net.add_edge(pid, p_id, label="OWNS", color="#22c55e", width=2)
        if float(person.get('avg_monthly_bill_pkr',0)) > 0:
            m_id = f"M_{pid}"
            net.add_node(m_id, label=f"⚡ Rs.{float(person.get('avg_monthly_bill_pkr',0)):,.0f}/mo", color={"background":"#1c1400","border":"#fbbf24"}, size=22, title=f"<b>Utility Meter</b><br>Monthly: Rs.{float(person.get('avg_monthly_bill_pkr',0)):,.0f}", shape="triangle")
            net.add_edge(pid, m_id, label="CONSUMES", color="#fbbf24", width=2)
        fbr_id = f"FBR_{pid}"
        fbr_clr = "#22c55e" if person.get('filer_status')=='ATL' else "#ef4444"
        net.add_node(fbr_id, label=f"📋 FBR\nRs.{float(person.get('declared_income_pkr',0)):,.0f}", color={"background":"#0f172a","border":fbr_clr}, size=22, title=f"<b>FBR Filing</b><br>Income: Rs.{float(person.get('declared_income_pkr',0)):,.0f}<br>Status: {person.get('filer_status','N/A')}", shape="box")
        net.add_edge(pid, fbr_id, label="FILED", color=fbr_clr, width=2)
        if G is not None:
            try:
                for n_id in list(G.neighbors(pid))[:4]:
                    edata = G.edges.get((pid, n_id), {})
                    if edata.get('type') == 'SHARES_ADDRESS':
                        ndata = G.nodes.get(n_id, {})
                        net.add_node(n_id, label=str(ndata.get('name',''))[:12], color={"background":"#2e1065","border":"#a855f7"}, size=20, title=f"<b>Same Address</b><br>{ndata.get('name',n_id)}", shape="dot")
                        net.add_edge(pid, n_id, label="SAME ADDRESS", color="#a855f7", width=1, dashes=True)
            except Exception:
                pass
        os.makedirs("outputs/graphs", exist_ok=True)
        graph_path = f"outputs/graphs/{pid}.html"
        try:
            net.save_graph(graph_path)
            with open(graph_path, "r", encoding="utf-8") as f:
                components.html(f.read(), height=430)
        except Exception as e:
            st.warning(f"Graph rendering error: {e}. Showing basic info.")
            if G is not None:
                neighbors = list(G.neighbors(pid))
                if neighbors:
                    st.write("Connected entities:", [G.nodes[n].get('name', n) for n in neighbors[:5]])

        st.markdown("<p class='section-title' style='margin-top:20px'>Forensic Enforcement Directive</p>", unsafe_allow_html=True)
        directive_text = ""
        if score >= 80:
            directive_text = "<b>CRITICAL:</b> Immediate enforcement mandated. "
        elif score >= 65:
            directive_text = "<b>HIGH RISK:</b> Priority audit sequence initiated. "
        if "Benami" in flags_raw:
            directive_text += "Benami holdings detected; initiate Section 24 asset freeze. "
        if "Dc Underinvoicing" in flags_raw or "DC Rate" in flags_raw:
            directive_text += "Valuation fraud detected; invoke ITO Section 68. "
        if "File Trading" in flags_raw:
            directive_text += "Documented evasion via File Trading; refer to regional registrar. "
        if not flags_raw or flags_raw == "None":
            directive_text = "No immediate legal violations detected. Maintain routine monitoring."
        st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid {clr}; border-radius: 8px; padding: 15px; color: {clr}; font-size: 13px;">
                <span style="font-size: 18px;">⚖️</span> {directive_text}
            </div>
        """, unsafe_allow_html=True)

    with col_intel:
        declared = float(person.get('declared_income_pkr', 0))
        lifestyle = float(person.get('annual_utility_bill', 0))
        assets = float(person.get('total_assets_estimated', 0))
        ratio = lifestyle / max(declared, 1)
        st.markdown("<p class='section-title'>Score Breakdown</p>", unsafe_allow_html=True)
        st.markdown(f"<div class='formula-box' style='color:#94a3b8'>Declared Annual Income : <b style='color:#22c55e'>Rs. {declared:,.0f}</b><br>Estimated Lifestyle Cost: <b style='color:#f59e0b'>Rs. {lifestyle:,.0f}</b><br>Total Asset Value       : <b style='color:#ef4444'>Rs. {assets:,.0f}</b><br><hr style='border-color:#1f2937;margin:8px 0'>Lifestyle / Income Ratio: <b style='color:{clr}'>{ratio:.1f}x</b><br><br><b style='color:{clr};font-size:18px'>Final Score: {score:.0f}/100 — {cat}</b></div>", unsafe_allow_html=True)
        st.markdown("<p class='section-title' style='margin-top:16px'>Fraud Modules Triggered</p>", unsafe_allow_html=True)
        flags = [f.strip() for f in flags_raw.split(',') if f.strip() not in ('','None','nan')]
        if flags:
            for flag in flags:
                st.markdown(f"<div class='flag-item'>🔴 {flag}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#4b5563;font-size:12px'>No major fraud patterns flagged.</p>", unsafe_allow_html=True)
        st.markdown("<p class='section-title' style='margin-top:16px'>FBR Investigation Note</p>", unsafe_allow_html=True)
        audit_text = audits.get(pid, None)
        if audit_text:
            st.markdown(f"<div class='audit-box'>{audit_text.replace(chr(10),'<br>')}</div>", unsafe_allow_html=True)
        else:
            if st.button("🤖 Generate Investigation Note", key="gen_audit"):
                with st.spinner("FBR IIW — Generating report..."):
                    try:
                        from groq import Groq
                        from dotenv import load_dotenv
                        load_dotenv()
                        client = Groq()
                        SYSTEM = "You are a Senior FBR Forensic Investigator. Write a 3-paragraph legal investigation note. Cite exact figures. Reference ITO 2001 or Benami Act 2017. Recommend enforcement action. Tone: cold, legal, authoritative."
                        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":SYSTEM},{"role":"user","content":f"SUBJECT: {sel_name}, SCORE: {score}/100, ASSETS: {flags_raw}, Income: Rs.{declared:,.0f}, Lifestyle: Rs.{lifestyle:,.0f}/yr"}], temperature=0.2, max_tokens=400)
                        audit_text = resp.choices[0].message.content
                        audits[pid] = audit_text
                        with open("outputs/audit_trails.json", "w", encoding="utf-8") as f:
                            json.dump(audits, f, indent=2)
                        st.markdown(f"<div class='audit-box'>{audit_text.replace(chr(10),'<br>')}</div>", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Groq error: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p class='section-title'>Evidence Timeline — Assets vs Tax Filings</p>", unsafe_allow_html=True)
    tl = []
    if person.get('vehicle_registration_year'):
        tl.append({"Event": f"Vehicle Registered — {person.get('vehicle_make_model','Vehicle')}", "Year": int(person.get('vehicle_registration_year', 2020)), "Type": "Asset Acquired"})
    if person.get('property_transfer_year'):
        tl.append({"Event": f"Property Transfer — {person.get('city','')}", "Year": int(person.get('property_transfer_year', 2021)), "Type": "Asset Acquired"})
    for yr in range(2022, 2026):
        tl.append({"Event": f"FBR Filing — {yr}", "Year": yr, "Type": "Non-Filing" if person.get('filer_status')=='Non-ATL' else "Filed"})
    if tl:
        tl_df = pd.DataFrame(tl)
        fig_tl = px.scatter(
            tl_df, x='Year', y='Type',
            text='Event', color='Type',
            template="plotly_dark",
            color_discrete_map={
                "Asset Acquired": "#ef4444",
                "Non-Filing":     "#f59e0b",
                "Filed":          "#22c55e"
            }
        )
        fig_tl.update_traces(textposition="top center", marker=dict(size=14), cliponaxis=False)
        min_yr = tl_df['Year'].min()
        max_yr = tl_df['Year'].max()
        padding = 0.5 if max_yr == min_yr else (max_yr - min_yr) * 0.15
        fig_tl.update_xaxes(range=[min_yr - padding, max_yr + padding])
        fig_tl.update_layout(**PLOTLY_DARK, height=240, showlegend=False, margin={"t": 50, "b": 10, "l": 10, "r": 50})
        st.plotly_chart(fig_tl, use_container_width=True)

    st.markdown("<hr style='border-color:#1f2937'>", unsafe_allow_html=True)
    ex1, ex2, _ = st.columns([1,1,3])
    with ex1:
        if st.button("📄 Export PDF Report", type="primary"):
            try:
                from pdf_export import generate_pdf
                pdf_path = generate_pdf(person.to_dict(), audits.get(pid, ""))
                with open(pdf_path, "rb") as f:
                    st.download_button("⬇️ Download PDF", f, file_name=f"FBR_Investigation_{pid}.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"PDF error: {e}")
    with ex2:
        if st.button("📦 Export Full Package"):
            try:
                import zipfile, io
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as zf:
                    from pdf_export import generate_pdf
                    pp = generate_pdf(person.to_dict(), audits.get(pid,""))
                    zf.write(pp, f"Investigation_{pid}.pdf")
                    zf.writestr(f"Evidence_{pid}.csv", person.to_frame().T.to_csv(index=False))
                buf.seek(0)
                st.download_button("⬇️ Download ZIP", buf, file_name=f"FBR_Package_{pid}.zip", mime="application/zip")
            except Exception as e:
                st.error(f"ZIP error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 4 – INTELLIGENCE QUERY (unchanged)
# ════════════════════════════════════════════════════════════════════════════
elif "Query" in page:
    if df.empty:
        st.warning("No data. Use Live Data Upload to load files.")
        st.stop()
    st.markdown("<p class='section-title'>Intelligence Query Interface</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#4b5563;font-size:13px;margin-bottom:16px'>Query Pakistan's financial population in plain language.</p>", unsafe_allow_html=True)
    quick = ["Non-filers in DHA with 2000cc+ vehicles", "Citizens with zero income and property above 20M", "Bahria Town residents with Non-ATL status", "All critical risk profiles in Karachi", "Drivers or housewives owning luxury vehicles", "Properties with File registry type and Non-ATL owner"]

    if 'auto_run' not in st.session_state:
        st.session_state['auto_run'] = False

    qc1, qc2, qc3 = st.columns(3)
    for i, q in enumerate(quick):
        col = [qc1, qc2, qc3][i % 3]
        with col:
            if st.button(f"🔍 {q}", key=f"q{i}"):
                st.session_state['query_val'] = q
                st.session_state['auto_run'] = True
                st.rerun()

    query = st.text_input("💬 Enter query:", value=st.session_state.get('query_val',''), placeholder="e.g. Show Land Cruiser owners with zero income in Lahore")
    if query != st.session_state.get('query_val',''):
        st.session_state['query_val'] = query

    execute_clicked = st.button("🚀 Execute", type="primary")
    if (execute_clicked or st.session_state['auto_run']) and query:
        st.session_state['auto_run'] = False
        safe_q = sanitize_query(query)
        if safe_q is None:
            st.error("🔒 Security violation: Unauthorized characters detected.")
        elif safe_q.strip() == "":
            st.warning("⚠️ Please enter a valid search query.")
        else:
            q_lower = translate_urdu(safe_q).lower()
            valid_keywords = ["lahore","karachi","islamabad","rawalpindi","non-filer","non-atl","filer","atl","cc","vehicle","luxury","high asset"]
            if not any(kw in q_lower for kw in valid_keywords):
                st.warning("No valid filter keywords found. Try 'lahore', 'non-filer', etc.")
                res = pd.DataFrame()
                summary = "No valid query terms."
            else:
                with st.spinner("Scanning population..."):
                    res = df.copy()
                    if "non-filer" in q_lower or "non-atl" in q_lower or "nonfiler" in q_lower:
                        res = res[res['filer_status'] == 'Non-ATL']
                    elif "filer" in q_lower or " atl " in q_lower:
                        res = res[res['filer_status'] == 'ATL']
                    cc_match = re.search(r'(\d{3,4})\s*cc', q_lower)
                    if cc_match:
                        cc_val = int(cc_match.group(1))
                        if "above" in q_lower or "more" in q_lower:
                            res = res[res['max_vehicle_cc'] >= cc_val]
                        else:
                            res = res[res['max_vehicle_cc'] <= cc_val]
                    for city in ['lahore','karachi','islamabad','rawalpindi']:
                        if city in q_lower:
                            res = res[res['city'].str.lower() == city]
                            break
                    if "zero income" in q_lower or "0 income" in q_lower:
                        res = res[res['declared_income_pkr'] == 0]
                    pm = re.search(r'(\d+)\s*(million|crore|m\b|cr\b)', q_lower)
                    if pm and 'property' in q_lower:
                        v = int(pm.group(1))
                        mx = 10_000_000 if 'crore' in pm.group(2) else 1_000_000
                        thresh = v * mx
                        if any(w in q_lower for w in ['above','more']):
                            res = res[res['total_property_value'] >= thresh]
                    for kw, mdl in [('land cruiser','Land Cruiser'),('fortuner','Fortuner'),('prado','Prado'),('civic','Civic'),('corolla','Corolla'),('alto','Alto')]:
                        if kw in q_lower and 'vehicle_make_model' in res.columns:
                            res = res[res['vehicle_make_model'].str.contains(mdl, na=False)]
                    for occ in ['driver','housewife','student','retired']:
                        if occ in q_lower and 'occupation' in res.columns:
                            res = res[res['occupation'].str.lower().str.contains(occ, na=False)]
                    if 'critical' in q_lower:
                        res = res[res['risk_category']=='CRITICAL']
                    elif 'high risk' in q_lower:
                        res = res[res['risk_category'].isin(['CRITICAL','HIGH'])]
                    if 'file' in q_lower and 'registry' in q_lower and 'registry_type' in res.columns:
                        res = res[res['registry_type'].str.lower().str.contains('file', na=False)]
                    res = res.sort_values('deviation_score', ascending=False)
                    summary = f"Query returned {len(res)} profiles. Avg score: {res['deviation_score'].mean():.0f}."
                    try:
                        from groq import Groq
                        from dotenv import load_dotenv
                        load_dotenv()
                        client = Groq()
                        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":f"Write ONE sentence summary for FBR auditor: Query '{query}' returned {len(res)} profiles. Avg score: {res['deviation_score'].mean():.0f}/100. Top: {res.iloc[0]['full_name'] if len(res)>0 else 'none'} score {res.iloc[0]['deviation_score'] if len(res)>0 else 0:.0f}."}], max_tokens=80, temperature=0.1)
                        summary = r.choices[0].message.content.strip()
                    except Exception:
                        pass
            if len(res) > 0:
                st.markdown(f"<div class='query-result-box'>🤖 <b>Intelligence Summary:</b> {summary}</div>", unsafe_allow_html=True)
                disp_c = ['full_name','city','deviation_score','risk_category','filer_status','declared_income_pkr','vehicle_make_model']
                av = [c for c in disp_c if c in res.columns]
                st.dataframe(res[av].head(20), use_container_width=True, height=280)
                st.markdown("<p class='section-title' style='margin-top:16px'>Risk Network — Top Results</p>", unsafe_allow_html=True)
                net_q = Network(height="260px", width="100%", bgcolor="#111827", font_color="#e2e8f0")
                for _, row_q in res.head(5).iterrows():
                    sc = float(row_q.get('deviation_score',0))
                    nc = score_color(sc)
                    net_q.add_node(row_q['master_person_id'], label=f"{str(row_q['full_name']).split()[0]}\n{sc:.0f}", color={"background":nc,"border":"#ffffff"}, size=int(sc/5)+12, title=f"{row_q['full_name']}<br>Score: {sc:.0f}<br>{row_q.get('city','')}")
                os.makedirs("outputs/graphs", exist_ok=True)
                net_q.save_graph("outputs/graphs/_query.html")
                with open("outputs/graphs/_query.html", "r", encoding="utf-8") as f:
                    components.html(f.read(), height=270)
            else:
                st.info("No profiles match. Try different terms.")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 5 – LIVE DATA UPLOAD (Test + Merge workflow with both upload modes)
# ════════════════════════════════════════════════════════════════════════════
elif "Upload" in page:

    # ── helpers ───────────────────────────────────────────────────────────
    def smart_merge(existing_df, new_df, id_cols):
        """
        Upsert new_df into existing_df.
        - Match on id_cols (unique record identifiers, NOT names).
        - For matched rows: update every column in existing with new values.
        - For unmatched rows: append as genuinely new records.
        Returns (merged_df, n_updated, n_added).
        """
        if existing_df.empty:
            return new_df.copy(), 0, len(new_df)
        if new_df.empty:
            return existing_df.copy(), 0, 0

        valid_ids = [c for c in id_cols if c in existing_df.columns and c in new_df.columns]
        if not valid_ids:
            merged = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates()
            return merged, 0, len(new_df)

        existing_idx = existing_df.set_index(valid_ids)
        new_idx      = new_df.set_index(valid_ids)

        overlap_keys = existing_idx.index.intersection(new_idx.index)
        n_updated = len(overlap_keys)
        new_keys  = new_idx.index.difference(existing_idx.index)
        n_added   = len(new_keys)

        if n_updated > 0:
            shared_cols = [c for c in new_df.columns if c in existing_df.columns and c not in valid_ids]
            existing_idx.loc[overlap_keys, shared_cols] = new_idx.loc[overlap_keys, shared_cols]

        if n_added > 0:
            new_rows = new_idx.loc[new_keys].reset_index()
            existing_idx = pd.concat([existing_idx.reset_index(), new_rows], ignore_index=True).set_index(valid_ids)

        return existing_idx.reset_index(), n_updated, n_added

    def run_pipeline_steps():
        """Run the 4-step forensic pipeline. Returns (success, error_msg)."""
        steps = [
            ("🔄 Preprocessing — normalizing names & addresses",            "preprocess",        "run_preprocessing"),
            ("🔗 Entity Resolution — linking identities across 4 datasets", "entity_resolution", "run_entity_resolution"),
            ("🕸️  Building Knowledge Graph — mapping financial footprints",  "build_graph",       "construct_graph"),
            ("🧠 Forensic Scoring — running 17 fraud detection modules",     "scoring",           "process_master_csv"),
        ]
        prog   = st.progress(0)
        status = st.empty()
        for i, (msg, mod, fn_name) in enumerate(steps):
            status.markdown(
                f"<div style='background:#0f1b2d;border-left:3px solid #3b82f6;"
                f"padding:10px 14px;border-radius:4px;color:#93c5fd;font-size:13px'>{msg}...</div>",
                unsafe_allow_html=True)
            try:
                import importlib
                m  = importlib.import_module(mod)
                fn = getattr(m, fn_name)
                fn()
            except Exception as e:
                status.empty()
                return False, f"Error in **{mod}**: {e}"
            prog.progress((i + 1) / len(steps))
            time.sleep(0.3)
        status.markdown(
            "<div style='background:#071f10;border-left:3px solid #22c55e;"
            "padding:12px 14px;border-radius:4px;color:#4ade80;"
            "font-weight:600;font-size:13px'>✅ Pipeline complete!</div>",
            unsafe_allow_html=True)
        return True, ""

    def render_dashboard(rdf, label="Preview"):
        """Render a National-Dashboard-style view for any scored dataframe."""
        if rdf.empty:
            st.warning("No scored data to display.")
            return

        if 'top_risk_factor' in rdf.columns and 'top_fraud_flags' not in rdf.columns:
            rdf = rdf.rename(columns={'top_risk_factor': 'top_fraud_flags'})
        if 'total_assets_val' in rdf.columns and 'total_assets_estimated' not in rdf.columns:
            rdf = rdf.rename(columns={'total_assets_val': 'total_assets_estimated'})

        tax_gap = float(rdf[rdf['deviation_score'] >= 65]['total_assets_estimated'].fillna(0).sum()) * 0.15 \
                  if 'total_assets_estimated' in rdf.columns else 0
        mc1, mc2, mc3, mc4 = st.columns(4)
        cards = [
            (mc1, "critical", "#ef4444", str(int((rdf['deviation_score'] >= 80).sum())),        "🔴 Critical Risk"),
            (mc2, "warning",  "#f59e0b", str(int(((rdf['deviation_score'] >= 65) & (rdf['deviation_score'] < 80)).sum())), "🟡 High Risk"),
            (mc3, "info",     "#3b82f6", f"{len(rdf):,}",                                        "📊 Profiles Scored"),
            (mc4, "success",  "#22c55e", f"Rs. {tax_gap/1e9:.2f}B",                              "⚠️ Est. Tax Gap"),
        ]
        for col, cls, clr, val, lbl in cards:
            with col:
                st.markdown(
                    f"<div class='metric-card {cls}'>"
                    f"<p class='metric-val' style='color:{clr}'>{val}</p>"
                    f"<p class='metric-lbl'>{lbl}</p></div>",
                    unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        ch1, ch2 = st.columns([3, 2])
        with ch1:
            st.markdown("<p class='section-title'>Risk Score Distribution</p>", unsafe_allow_html=True)
            fig_h = px.histogram(rdf, x="deviation_score", nbins=25,
                                 color_discrete_sequence=["#3b82f6"],
                                 labels={"deviation_score": "Score", "count": "Profiles"},
                                 template="plotly_dark")
            fig_h.add_vline(x=65, line_dash="dash", line_color="#f59e0b",
                            annotation_text="High Risk", annotation_font_color="#f59e0b")
            fig_h.add_vline(x=80, line_dash="dash", line_color="#ef4444",
                            annotation_text="Critical", annotation_font_color="#ef4444")
            fig_h.update_layout(**PLOTLY_DARK, height=260, margin=dict(t=10, b=10))
            st.plotly_chart(fig_h, use_container_width=True)

        with ch2:
            st.markdown("<p class='section-title'>Avg Score by City</p>", unsafe_allow_html=True)
            if 'city' in rdf.columns:
                city_df = rdf.groupby('city')['deviation_score'].mean().reset_index().sort_values('deviation_score')
                fig_c = px.bar(city_df, x='deviation_score', y='city', orientation='h',
                               color='deviation_score',
                               color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444"],
                               template="plotly_dark",
                               labels={"deviation_score": "Avg Score", "city": ""})
                fig_c.update_layout(**PLOTLY_DARK, height=260, coloraxis_showscale=False, margin=dict(t=10, b=10))
                st.plotly_chart(fig_c, use_container_width=True)

        ch3, ch4 = st.columns([2, 3])
        with ch3:
            st.markdown("<p class='section-title'>Risk Breakdown</p>", unsafe_allow_html=True)
            if 'risk_category' in rdf.columns:
                rc = rdf['risk_category'].value_counts()
                fig_p = px.pie(values=rc.values, names=rc.index,
                               color=rc.index, color_discrete_map=RISK_COLORS,
                               template="plotly_dark", hole=0.45)
                fig_p.update_layout(paper_bgcolor="#111827", font_color="#94a3b8",
                                    height=260, showlegend=True,
                                    legend=dict(orientation="v", x=1.0, y=0.5, font=dict(size=10)),
                                    margin=dict(t=10, b=10))
                st.plotly_chart(fig_p, use_container_width=True)

        with ch4:
            st.markdown("<p class='section-title'>Top Fraud Patterns</p>", unsafe_allow_html=True)
            if 'top_fraud_flags' in rdf.columns:
                all_flags = []
                for fs in rdf['top_fraud_flags'].dropna():
                    for f in str(fs).split(','):
                        f = f.strip()
                        if f and f not in ('None', 'nan', ''):
                            all_flags.append(f)
                if all_flags:
                    fc = pd.Series(all_flags).value_counts().head(8).reset_index()
                    fc.columns = ['Pattern', 'Count']
                    fig_f = px.bar(fc.sort_values('Count'), x='Count', y='Pattern',
                                   orientation='h', color='Count',
                                   color_continuous_scale=["#1d4ed8", "#dc2626"],
                                   template="plotly_dark")
                    fig_f.update_layout(**PLOTLY_DARK, height=260,
                                        coloraxis_showscale=False, margin=dict(t=10, b=10))
                    st.plotly_chart(fig_f, use_container_width=True)

        st.markdown("<p class='section-title'>Top 10 Highest-Risk Profiles</p>", unsafe_allow_html=True)
        disp_cols = ['full_name', 'deviation_score', 'risk_category',
                     'filer_status', 'declared_income_pkr', 'city', 'top_fraud_flags']
        avail = [c for c in disp_cols if c in rdf.columns]
        st.dataframe(
            rdf.sort_values('deviation_score', ascending=False)[avail].head(10),
            use_container_width=True)

    # ── page header ───────────────────────────────────────────────────────
    st.markdown("<p class='section-title'>Live Data Ingestion Pipeline</p>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#4b5563;font-size:13px;margin-bottom:20px'>"
        "Upload new government datasets. Test them in isolation, then merge them into the live database when ready.</p>",
        unsafe_allow_html=True)

    # ── Upload mode toggle ────────────────────────────────────
    upload_mode = st.radio(
        "📂 Upload mode",
        ["4 Separate Files (standard)", "1 Combined File (auto-split)"],
        horizontal=True,
        key="upload_mode"
    )

    # ════════════════════════════════════
    # MODE A — 4 separate files (original)
    # ════════════════════════════════════
    if upload_mode == "4 Separate Files (standard)":
        with st.expander("📋 Required CSV Format — click to expand"):
            e1, e2 = st.columns(2)
            with e1:
                st.markdown(
                    "**fbr_tax_records.csv**\n"
                    "`fbr_id, full_name, declared_income_pkr, tax_paid_pkr,\n"
                    "filer_status (ATL/Non-ATL), reported_address, phone_number,\n"
                    "income_source, wealth_source, occupation,\n"
                    "years_as_nonfiler, has_bank_account`\n\n"
                    "**excise_vehicles.csv**\n"
                    "`vehicle_reg_no, owner_name, engine_capacity_cc,\n"
                    "vehicle_make_model, registration_year, owner_address,\n"
                    "import_type, declared_import_value_pkr`")
            with e2:
                st.markdown(
                    "**disco_consumption.csv**\n"
                    "`meter_ref_no, consumer_name, installation_address,\n"
                    "avg_monthly_bill_pkr, connection_type`\n\n"
                    "**property_transfers.csv**\n"
                    "`registry_no, buyer_name, seller_name, property_address,\n"
                    "property_value_pkr, transfer_date, area_marla,\n"
                    "property_type, registry_type, noc_status,\n"
                    "society_name, plot_number`")

        st.markdown("---")
        st.markdown("<p class='section-title'>Step 1 — Upload Your 4 Datasets</p>", unsafe_allow_html=True)

        u1, u2 = st.columns(2)
        with u1:
            fbr_f   = st.file_uploader("🏦 FBR Tax Declarations",        type=["csv"], key="u_fbr")
            disco_f = st.file_uploader("⚡ DISCO Utility Consumption",    type=["csv"], key="u_disco")
        with u2:
            exc_f   = st.file_uploader("🚗 Provincial Excise (Vehicles)", type=["csv"], key="u_exc")
            prop_f  = st.file_uploader("🏠 Real Estate Registry",         type=["csv"], key="u_prop")

        all_up = all([fbr_f, exc_f, disco_f, prop_f])

        if all_up:
            # cache uploaded previews
            current_files = (fbr_f.name, exc_f.name, disco_f.name, prop_f.name)
            if st.session_state.get('_up_names') != current_files:
                previews = []
                for uf in [fbr_f, exc_f, disco_f, prop_f]:
                    uf.seek(0)
                    previews.append(pd.read_csv(uf))
                st.session_state['_up_dfs']   = previews
                st.session_state['_up_names'] = current_files
                for k in ['_test_done', '_test_rdf', '_merge_done']:
                    st.session_state.pop(k, None)

            up_dfs = st.session_state['_up_dfs']
            fbr_new, exc_new, disco_new, prop_new = up_dfs

            with st.expander("👁️ Preview uploaded data"):
                tabs   = st.tabs(["FBR", "Excise", "DISCO", "Property"])
                labels = ["FBR Tax", "Excise Vehicles", "DISCO Consumption", "Property Registry"]
                for tab, tmp, lb in zip(tabs, up_dfs, labels):
                    with tab:
                        st.markdown(f"**{lb}** — {len(tmp):,} records · {len(tmp.columns)} columns")
                        st.dataframe(tmp.head(5), use_container_width=True)

            st.markdown("---")
            st.markdown("<p class='section-title'>Step 2 — Choose Action</p>", unsafe_allow_html=True)

            col_test, col_merge, col_clear = st.columns([2, 2, 1])
            with col_test:
                test_btn = st.button(
                    "🧪 Test — Run on uploaded files only (don't touch live data)",
                    type="secondary", use_container_width=True)
            with col_merge:
                merge_btn = st.button(
                    "🔀 Merge into Live Database",
                    type="primary", use_container_width=True,
                    disabled=not st.session_state.get('_test_done', False),
                    help="Run a Test first, then this button activates.")
            with col_clear:
                if st.button("🗑️ Clear", use_container_width=True):
                    for k in ['u_fbr', 'u_exc', 'u_disco', 'u_prop',
                              '_up_dfs', '_up_names', '_test_done', '_test_rdf', '_merge_done']:
                        st.session_state.pop(k, None)
                    st.rerun()

            if not st.session_state.get('_test_done', False):
                st.info("👆 Click **Test** to run the pipeline on your uploaded files and preview results before committing to the live database.")

            # ── Test run (4‑file mode) ─────────────────────────────────
            if test_btn:
                st.session_state.pop('_test_done', None)
                st.session_state.pop('_test_rdf', None)

                TEMP_RAW = "data/raw_test"
                TEMP_OUT = "outputs/test_run"
                os.makedirs(TEMP_RAW, exist_ok=True)
                os.makedirs(TEMP_OUT, exist_ok=True)

                for df_tmp, fname in zip(
                        [fbr_new, exc_new, disco_new, prop_new],
                        ["fbr_tax_records.csv", "excise_vehicles.csv",
                         "disco_consumption.csv", "property_transfers.csv"]):
                    df_tmp.to_csv(os.path.join(TEMP_RAW, fname), index=False)

                # Backup and swap
                BACKUP = "data/raw_backup"
                os.makedirs(BACKUP, exist_ok=True)
                raw_files = ["fbr_tax_records.csv","excise_vehicles.csv","disco_consumption.csv","property_transfers.csv"]
                for fn in raw_files:
                    src = f"data/raw/{fn}"
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(BACKUP, fn))
                    df_map = dict(zip(raw_files, [fbr_new, exc_new, disco_new, prop_new]))
                    df_map[fn].to_csv(src, index=False)

                out_files = ["scored_entities.csv","master_entities.csv","shaheen_graph.pkl","audit_trails.json"]
                OUT_BACKUP = "outputs/backup_before_test"
                os.makedirs(OUT_BACKUP, exist_ok=True)
                for fn in out_files:
                    src = f"outputs/{fn}"
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(OUT_BACKUP, fn))

                ok = False
                try:
                    with st.spinner("Running forensic pipeline on test data…"):
                        ok, err = run_pipeline_steps()
                    if ok:
                        rdf = pd.read_csv("outputs/scored_entities.csv")
                        st.session_state['_test_rdf']  = rdf
                        st.session_state['_test_done'] = True
                    else:
                        st.error(err)
                except Exception as e:
                    st.error(f"Test run error: {e}")
                finally:
                    # Restore original files
                    for fn in raw_files:
                        bk = os.path.join(BACKUP, fn)
                        if os.path.exists(bk):
                            shutil.copy(bk, f"data/raw/{fn}")
                        elif os.path.exists(f"data/raw/{fn}"):
                            os.remove(f"data/raw/{fn}")
                    for fn in out_files:
                        bk = os.path.join(OUT_BACKUP, fn)
                        if os.path.exists(bk):
                            shutil.copy(bk, f"outputs/{fn}")

                if ok:
                    st.rerun()

            # Show test dashboard
            if st.session_state.get('_test_done') and st.session_state.get('_test_rdf') is not None:
                st.markdown("---")
                st.markdown(
                    "<div style='background:#071f10;border:1px solid #22c55e;border-radius:8px;"
                    "padding:12px 18px;margin-bottom:16px'>"
                    "<span style='color:#4ade80;font-weight:700;font-size:14px'>🧪 TEST RUN RESULTS</span>"
                    "<span style='color:#6b7280;font-size:12px;margin-left:12px'>"
                    "Pipeline ran on your uploaded files only — live database is unchanged.</span>"
                    "</div>",
                    unsafe_allow_html=True)
                render_dashboard(st.session_state['_test_rdf'].copy(), label="Test Run")
                if not st.session_state.get('_merge_done'):
                    st.markdown("---")
                    st.info("✅ Satisfied with the results? Click **🔀 Merge into Live Database** above to commit these files.")

            # ── Merge (4‑file mode) ─────────────────────────────────────
            if merge_btn and st.session_state.get('_test_done'):
                os.makedirs("data/raw", exist_ok=True)
                merge_log = []

                # FBR
                fbr_path = "data/raw/fbr_tax_records.csv"
                if os.path.exists(fbr_path):
                    existing_fbr = pd.read_csv(fbr_path)
                    merged_fbr, upd, added = smart_merge(existing_fbr, fbr_new, id_cols=['fbr_id'])
                    merge_log.append(f"**FBR:** {upd} updated · {added} new")
                else:
                    merged_fbr = fbr_new.copy()
                    merge_log.append(f"**FBR:** {len(merged_fbr)} written (new)")
                merged_fbr.to_csv(fbr_path, index=False)

                # Excise
                exc_path = "data/raw/excise_vehicles.csv"
                if os.path.exists(exc_path):
                    existing_exc = pd.read_csv(exc_path)
                    merged_exc, upd, added = smart_merge(existing_exc, exc_new, id_cols=['vehicle_reg_no'])
                    merge_log.append(f"**Excise:** {upd} updated · {added} new")
                else:
                    merged_exc = exc_new.copy()
                    merge_log.append(f"**Excise:** {len(merged_exc)} written (new)")
                merged_exc.to_csv(exc_path, index=False)

                # DISCO
                disco_path = "data/raw/disco_consumption.csv"
                if os.path.exists(disco_path):
                    existing_disco = pd.read_csv(disco_path)
                    merged_disco, upd, added = smart_merge(existing_disco, disco_new, id_cols=['meter_ref_no'])
                    merge_log.append(f"**DISCO:** {upd} updated · {added} new")
                else:
                    merged_disco = disco_new.copy()
                    merge_log.append(f"**DISCO:** {len(merged_disco)} written (new)")
                merged_disco.to_csv(disco_path, index=False)

                # Property
                prop_path = "data/raw/property_transfers.csv"
                if os.path.exists(prop_path):
                    existing_prop = pd.read_csv(prop_path)
                    merged_prop, upd, added = smart_merge(existing_prop, prop_new, id_cols=['registry_no'])
                    merge_log.append(f"**Property:** {upd} updated · {added} new")
                else:
                    merged_prop = prop_new.copy()
                    merge_log.append(f"**Property:** {len(merged_prop)} written (new)")
                merged_prop.to_csv(prop_path, index=False)

                st.markdown("---")
                st.markdown("<p class='section-title'>Merge Summary</p>", unsafe_allow_html=True)
                for line in merge_log:
                    st.markdown(
                        f"<div style='background:#0f1b2d;border-left:3px solid #3b82f6;"
                        f"padding:8px 14px;border-radius:4px;color:#93c5fd;"
                        f"font-size:13px;margin:4px 0'>{line}</div>",
                        unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                with st.spinner("Re-running full forensic pipeline on merged database…"):
                    ok2, err2 = run_pipeline_steps()
                if ok2:
                    st.session_state['_merge_done'] = True
                    st.success("✅ Merge complete. Live database updated. Navigate to National Dashboard to see updated results.")
                    st.balloons()
                    for k in ['_test_done', '_test_rdf']:
                        st.session_state.pop(k, None)
                    st.rerun()
                else:
                    st.error(f"Pipeline failed after merge: {err2}")

        else:
            st.info("⬆️ Upload all 4 CSV files above to continue.")
            st.markdown("---")
            st.markdown("<p class='section-title'>📥 Download Sample Templates</p>", unsafe_allow_html=True)
            tc1, tc2 = st.columns(2)
            templates = [
                ("data/raw/fbr_tax_records.csv",    "FBR Tax Records",   "fbr_sample.csv"),
                ("data/raw/excise_vehicles.csv",     "Excise Vehicles",   "excise_sample.csv"),
                ("data/raw/disco_consumption.csv",   "DISCO Consumption", "disco_sample.csv"),
                ("data/raw/property_transfers.csv",  "Property Registry", "property_sample.csv"),
            ]
            for i, (path, lbl, fname) in enumerate(templates):
                col = tc1 if i % 2 == 0 else tc2
                with col:
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            col.download_button(f"⬇️ {lbl}", f.read(), file_name=fname, mime="text/csv")
                    else:
                        col.info("Run generate_data.py first")

    # ════════════════════════════════════
    # MODE B — 1 combined file (auto-split)
    # ════════════════════════════════════
    else:
        st.markdown("---")
        st.markdown("<p class='section-title'>Step 1 — Upload Combined CSV</p>", unsafe_allow_html=True)
        st.markdown(
            "<div style='background:#0f1b2d;border-left:3px solid #3b82f6;padding:12px 16px;border-radius:4px;color:#93c5fd;font-size:13px;margin-bottom:16px'>"
            "<b>Auto-split mode:</b> Upload a single CSV that contains columns from any or all of the 4 datasets. "
            "The system will detect which columns belong to which dataset and route them automatically.<br>"
            "Recognised column sets:<br>"
            "• <b>FBR:</b> fbr_id / full_name / declared_income_pkr / filer_status<br>"
            "• <b>Excise:</b> vehicle_reg_no / engine_capacity_cc / vehicle_make_model<br>"
            "• <b>DISCO:</b> meter_ref_no / avg_monthly_bill_pkr / connection_type<br>"
            "• <b>Property:</b> registry_no / property_value_pkr / registry_type"
            "</div>",
            unsafe_allow_html=True)

        combined_f = st.file_uploader("📄 Upload combined CSV", type=["csv"], key="u_combined")

        if combined_f:
            combined_f.seek(0)
            cdf = pd.read_csv(combined_f)
            st.success(f"✅ Loaded {len(cdf):,} rows · {len(cdf.columns)} columns")

            # Define expected column sets
            FBR_COLS   = {'fbr_id','full_name','declared_income_pkr','tax_paid_pkr','filer_status',
                          'reported_address','phone_number','income_source','wealth_source',
                          'occupation','years_as_nonfiler','has_bank_account'}
            EXC_COLS   = {'vehicle_reg_no','owner_name','engine_capacity_cc','vehicle_make_model',
                          'registration_year','owner_address','import_type','declared_import_value_pkr'}
            DISCO_COLS = {'meter_ref_no','consumer_name','installation_address',
                          'avg_monthly_bill_pkr','connection_type'}
            PROP_COLS  = {'registry_no','buyer_name','seller_name','property_address',
                          'property_value_pkr','transfer_date','area_marla','property_type',
                          'registry_type','noc_status','society_name','plot_number'}

            actual = set(cdf.columns)
            fbr_found   = actual & FBR_COLS
            exc_found   = actual & EXC_COLS
            disco_found = actual & DISCO_COLS
            prop_found  = actual & PROP_COLS

            KEY_FBR   = {'fbr_id','full_name','declared_income_pkr','filer_status'}
            KEY_EXC   = {'vehicle_reg_no','engine_capacity_cc','vehicle_make_model'}
            KEY_DISCO = {'meter_ref_no','avg_monthly_bill_pkr'}
            KEY_PROP  = {'registry_no','property_value_pkr','registry_type'}

            det_fbr   = bool(fbr_found & KEY_FBR)
            det_exc   = bool(exc_found & KEY_EXC)
            det_disco = bool(disco_found & KEY_DISCO)
            det_prop  = bool(prop_found & KEY_PROP)

            st.markdown("**Detected datasets in your file:**")
            dc1, dc2, dc3, dc4 = st.columns(4)
            for col, label, detected, found in [
                (dc1, "🏦 FBR Tax",    det_fbr,   fbr_found),
                (dc2, "🚗 Excise",     det_exc,   exc_found),
                (dc3, "⚡ DISCO",      det_disco, disco_found),
                (dc4, "🏠 Property",   det_prop,  prop_found),
            ]:
                with col:
                    color = "#22c55e" if detected else "#6b7280"
                    icon  = "✅" if detected else "❌"
                    st.markdown(f"<div style='background:#111827;border:1px solid {color};border-radius:8px;padding:10px;text-align:center'>"
                                f"<p style='color:{color};font-weight:700;margin:0'>{icon} {label}</p>"
                                f"<p style='color:#6b7280;font-size:11px;margin:4px 0 0'>{len(found)} cols matched</p>"
                                f"</div>", unsafe_allow_html=True)

            if not any([det_fbr, det_exc, det_disco, det_prop]):
                st.error("❌ No recognisable columns found. Please check column names match the expected formats.")
                st.stop()

            with st.expander("👁️ Preview uploaded data (first 5 rows)"):
                st.dataframe(cdf.head(5), use_container_width=True)

            st.markdown("---")
            st.markdown("<p class='section-title'>Step 2 — Choose Action</p>", unsafe_allow_html=True)

            col_test2, col_merge2, col_clear2 = st.columns([2,2,1])
            with col_test2:
                test_btn2 = st.button(
                    "🧪 Test — Run on uploaded files only (don't touch live data)",
                    type="secondary", use_container_width=True, key="test_comb")
            with col_merge2:
                merge_btn2 = st.button(
                    "🔀 Merge into Live Database",
                    type="primary", use_container_width=True, key="merge_comb",
                    disabled=not st.session_state.get('_test_done_comb', False),
                    help="Run a Test first, then this button activates.")
            with col_clear2:
                if st.button("🗑️ Clear", use_container_width=True, key="clear_comb"):
                    for k in ['u_combined', '_test_done_comb', '_test_rdf_comb', '_merge_done_comb',
                              '_up_combined_df']:
                        st.session_state.pop(k, None)
                    st.rerun()

            if not st.session_state.get('_test_done_comb', False):
                st.info("👆 Click **Test** to run the pipeline on your uploaded file and preview results before committing to the live database.")

            # ── Test run (combined mode) ─────────────────────────────────
            if test_btn2:
                st.session_state.pop('_test_done_comb', None)
                st.session_state.pop('_test_rdf_comb', None)

                # Build individual dataframes from combined file
                cols_to_fbr   = list(fbr_found)
                cols_to_exc   = list(exc_found)
                cols_to_disco = list(disco_found)
                cols_to_prop  = list(prop_found)

                fbr_comb   = cdf[cols_to_fbr].copy()   if cols_to_fbr   else pd.DataFrame()
                exc_comb   = cdf[cols_to_exc].copy()   if cols_to_exc   else pd.DataFrame()
                disco_comb = cdf[cols_to_disco].copy() if cols_to_disco else pd.DataFrame()
                prop_comb  = cdf[cols_to_prop].copy()  if cols_to_prop  else pd.DataFrame()

                # Store them in session for later merge
                st.session_state['_fbr_comb']   = fbr_comb
                st.session_state['_exc_comb']   = exc_comb
                st.session_state['_disco_comb'] = disco_comb
                st.session_state['_prop_comb']  = prop_comb

                # Backup and replace
                BACKUP = "data/raw_backup"
                os.makedirs(BACKUP, exist_ok=True)
                raw_files = ["fbr_tax_records.csv","excise_vehicles.csv","disco_consumption.csv","property_transfers.csv"]
                df_map = {
                    "fbr_tax_records.csv": fbr_comb,
                    "excise_vehicles.csv": exc_comb,
                    "disco_consumption.csv": disco_comb,
                    "property_transfers.csv": prop_comb
                }

                for fn in raw_files:
                    src = f"data/raw/{fn}"
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(BACKUP, fn))
                    df_map[fn].to_csv(src, index=False)

                out_files = ["scored_entities.csv","master_entities.csv","shaheen_graph.pkl","audit_trails.json"]
                OUT_BACKUP = "outputs/backup_before_test"
                os.makedirs(OUT_BACKUP, exist_ok=True)
                for fn in out_files:
                    src = f"outputs/{fn}"
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(OUT_BACKUP, fn))

                ok = False
                try:
                    with st.spinner("Running forensic pipeline on test data…"):
                        ok, err = run_pipeline_steps()
                    if ok:
                        rdf = pd.read_csv("outputs/scored_entities.csv")
                        st.session_state['_test_rdf_comb']  = rdf
                        st.session_state['_test_done_comb'] = True
                    else:
                        st.error(err)
                except Exception as e:
                    st.error(f"Test run error: {e}")
                finally:
                    for fn in raw_files:
                        bk = os.path.join(BACKUP, fn)
                        if os.path.exists(bk):
                            shutil.copy(bk, f"data/raw/{fn}")
                        elif os.path.exists(f"data/raw/{fn}"):
                            os.remove(f"data/raw/{fn}")
                    for fn in out_files:
                        bk = os.path.join(OUT_BACKUP, fn)
                        if os.path.exists(bk):
                            shutil.copy(bk, f"outputs/{fn}")

                if ok:
                    st.rerun()

            # Show test dashboard (combined)
            if st.session_state.get('_test_done_comb') and st.session_state.get('_test_rdf_comb') is not None:
                st.markdown("---")
                st.markdown(
                    "<div style='background:#071f10;border:1px solid #22c55e;border-radius:8px;"
                    "padding:12px 18px;margin-bottom:16px'>"
                    "<span style='color:#4ade80;font-weight:700;font-size:14px'>🧪 TEST RUN RESULTS</span>"
                    "<span style='color:#6b7280;font-size:12px;margin-left:12px'>"
                    "Pipeline ran on your uploaded file only — live database is unchanged.</span>"
                    "</div>",
                    unsafe_allow_html=True)
                render_dashboard(st.session_state['_test_rdf_comb'].copy(), label="Test Run")
                if not st.session_state.get('_merge_done_comb', False):
                    st.markdown("---")
                    st.info("✅ Satisfied with the results? Click **🔀 Merge into Live Database** above to commit this file.")

            # ── Merge (combined mode) ─────────────────────────────────────
            if merge_btn2 and st.session_state.get('_test_done_comb'):
                os.makedirs("data/raw", exist_ok=True)
                fbr_comb   = st.session_state.get('_fbr_comb', pd.DataFrame())
                exc_comb   = st.session_state.get('_exc_comb', pd.DataFrame())
                disco_comb = st.session_state.get('_disco_comb', pd.DataFrame())
                prop_comb  = st.session_state.get('_prop_comb', pd.DataFrame())

                merge_log = []

                # FBR
                fbr_path = "data/raw/fbr_tax_records.csv"
                if os.path.exists(fbr_path) and not fbr_comb.empty:
                    existing_fbr = pd.read_csv(fbr_path)
                    merged_fbr, upd, added = smart_merge(existing_fbr, fbr_comb, id_cols=['fbr_id'])
                    merge_log.append(f"**FBR:** {upd} updated · {added} new")
                else:
                    merged_fbr = fbr_comb.copy()
                    merge_log.append(f"**FBR:** {len(merged_fbr)} written (new)")
                if not merged_fbr.empty:
                    merged_fbr.to_csv(fbr_path, index=False)

                # Excise
                exc_path = "data/raw/excise_vehicles.csv"
                if os.path.exists(exc_path) and not exc_comb.empty:
                    existing_exc = pd.read_csv(exc_path)
                    merged_exc, upd, added = smart_merge(existing_exc, exc_comb, id_cols=['vehicle_reg_no'])
                    merge_log.append(f"**Excise:** {upd} updated · {added} new")
                else:
                    merged_exc = exc_comb.copy()
                    merge_log.append(f"**Excise:** {len(merged_exc)} written (new)")
                if not merged_exc.empty:
                    merged_exc.to_csv(exc_path, index=False)

                # DISCO
                disco_path = "data/raw/disco_consumption.csv"
                if os.path.exists(disco_path) and not disco_comb.empty:
                    existing_disco = pd.read_csv(disco_path)
                    merged_disco, upd, added = smart_merge(existing_disco, disco_comb, id_cols=['meter_ref_no'])
                    merge_log.append(f"**DISCO:** {upd} updated · {added} new")
                else:
                    merged_disco = disco_comb.copy()
                    merge_log.append(f"**DISCO:** {len(merged_disco)} written (new)")
                if not merged_disco.empty:
                    merged_disco.to_csv(disco_path, index=False)

                # Property
                prop_path = "data/raw/property_transfers.csv"
                if os.path.exists(prop_path) and not prop_comb.empty:
                    existing_prop = pd.read_csv(prop_path)
                    merged_prop, upd, added = smart_merge(existing_prop, prop_comb, id_cols=['registry_no'])
                    merge_log.append(f"**Property:** {upd} updated · {added} new")
                else:
                    merged_prop = prop_comb.copy()
                    merge_log.append(f"**Property:** {len(merged_prop)} written (new)")
                if not merged_prop.empty:
                    merged_prop.to_csv(prop_path, index=False)

                st.markdown("---")
                st.markdown("<p class='section-title'>Merge Summary</p>", unsafe_allow_html=True)
                for line in merge_log:
                    st.markdown(
                        f"<div style='background:#0f1b2d;border-left:3px solid #3b82f6;"
                        f"padding:8px 14px;border-radius:4px;color:#93c5fd;"
                        f"font-size:13px;margin:4px 0'>{line}</div>",
                        unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                with st.spinner("Re-running full forensic pipeline on merged database…"):
                    ok2, err2 = run_pipeline_steps()
                if ok2:
                    st.session_state['_merge_done_comb'] = True
                    st.success("✅ Merge complete. Live database updated. Navigate to National Dashboard to see updated results.")
                    st.balloons()
                    for k in ['_test_done_comb', '_test_rdf_comb', '_fbr_comb', '_exc_comb', '_disco_comb', '_prop_comb']:
                        st.session_state.pop(k, None)
                    st.rerun()
                else:
                    st.error(f"Pipeline failed after merge: {err2}")

        else:
            st.info("⬆️ Upload your combined CSV file above to continue.")
            st.markdown("---")
            st.markdown("<p class='section-title'>📥 Download Sample Templates</p>", unsafe_allow_html=True)
            tc1, tc2 = st.columns(2)
            templates = [
                ("data/raw/fbr_tax_records.csv",    "FBR Tax Records",   "fbr_sample.csv"),
                ("data/raw/excise_vehicles.csv",     "Excise Vehicles",   "excise_sample.csv"),
                ("data/raw/disco_consumption.csv",   "DISCO Consumption", "disco_sample.csv"),
                ("data/raw/property_transfers.csv",  "Property Registry", "property_sample.csv"),
            ]
            for i, (path, lbl, fname) in enumerate(templates):
                col = tc1 if i % 2 == 0 else tc2
                with col:
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            col.download_button(f"⬇️ {lbl}", f.read(), file_name=fname, mime="text/csv")
                    else:
                        col.info("Run generate_data.py first")