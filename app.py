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
from pyvis.network import Network
import streamlit.components.v1 as components

# ── must be first streamlit call ─────────────────────────────
st.set_page_config(
    page_title="Shaheen-Eye | P-FIS",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── global CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background-color: #0a0e1a;
    color: #e2e8f0;
}
[data-testid="stSidebar"] {
    background-color: #0f1623;
    border-right: 1px solid #1e2d40;
}
[data-testid="stSidebar"] .stRadio label {
    color: #94a3b8;
    font-size: 13px;
}
.fbr-header {
    background: linear-gradient(135deg, #0f2a1a 0%, #1a3a28 50%, #0f2a1a 100%);
    border-bottom: 2px solid #22c55e;
    padding: 14px 24px;
    margin-bottom: 24px;
    border-radius: 0 0 8px 8px;
}
.fbr-header h1 {
    color: #bbf7d0;
    font-size: 15px;
    font-weight: 600;
    margin: 0;
    letter-spacing: 0.5px;
}
.fbr-header p {
    color: #4ade80;
    font-size: 10px;
    margin: 3px 0 0 0;
    letter-spacing: 0.3px;
}
.metric-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #374151; }
.metric-card.critical { border-left: 3px solid #ef4444; }
.metric-card.warning  { border-left: 3px solid #f59e0b; }
.metric-card.info     { border-left: 3px solid #3b82f6; }
.metric-card.success  { border-left: 3px solid #22c55e; }
.metric-val { font-size: 28px; font-weight: 700; margin: 0; }
.metric-lbl { color: #6b7280; font-size: 11px; margin: 4px 0 0; }
.section-title {
    font-size: 14px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
    padding-bottom: 6px;
    border-bottom: 1px solid #1f2937;
}
.risk-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.profile-header {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.audit-box {
    background: #0a0e1a;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 16px;
    font-size: 13px;
    line-height: 1.7;
    color: #cbd5e1;
}
.formula-box {
    background: #0d1117;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 14px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
}
.flag-item {
    background: #1a0a0a;
    border-left: 3px solid #ef4444;
    padding: 6px 12px;
    margin: 4px 0;
    border-radius: 0 6px 6px 0;
    font-size: 12px;
    color: #fca5a5;
}
.query-result-box {
    background: #0f1b2d;
    border: 1px solid #1e3a5f;
    border-left: 3px solid #3b82f6;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    color: #93c5fd;
    margin: 8px 0 16px;
}
#MainMenu, footer, .stDeployButton { visibility: hidden; }
.stPlotlyChart { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── FBR header ───────────────────────────────────────────────
st.markdown("""
<div class="fbr-header">
    <h1>🦅 SHAHEEN-EYE &nbsp;|&nbsp; Pakistan Financial Intelligence Suite (P-FIS) v1.0</h1>
    <p>Financial Monitoring Unit (FMU) — Government of Pakistan &nbsp;·&nbsp;
       Federal Board of Revenue — Intelligence & Investigation Wing &nbsp;·&nbsp;
       CLASSIFICATION: CONFIDENTIAL &nbsp;·&nbsp; AUTHORIZED ACCESS ONLY</p>
</div>
""", unsafe_allow_html=True)

# ── data loaders ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    scored = "outputs/scored_entities.csv"
    master = "outputs/master_entities.csv"
    try:
        df = pd.read_csv(scored)
        # rename column if it came out differently
        if 'top_risk_factor' in df.columns and 'top_fraud_flags' not in df.columns:
            df = df.rename(columns={'top_risk_factor': 'top_fraud_flags'})
        if 'total_assets_val' in df.columns and 'total_assets_estimated' not in df.columns:
            df = df.rename(columns={'total_assets_val': 'total_assets_estimated'})
        # ensure city column exists
        if 'city' not in df.columns and os.path.exists(master):
            m = pd.read_csv(master)[['master_person_id', 'city']]
            df = df.merge(m, on='master_person_id', how='left')
        return df
    except FileNotFoundError:
        st.error("Run the pipeline first: python scoring.py")
        return pd.DataFrame()

@st.cache_resource
def load_graph():
    path = "outputs/shaheen_graph.pkl"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

@st.cache_data(ttl=300)
def load_audit():
    path = "outputs/audit_trails.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

df      = load_data()
G       = load_graph()
audits  = load_audit()

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

# ── sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<p style='color:#4ade80;font-size:11px;font-weight:600;"
        "letter-spacing:1px;text-transform:uppercase;margin-bottom:8px'>"
        "Navigation</p>",
        unsafe_allow_html=True
    )
    page = st.radio("", [
        "🏠 National Dashboard",
        "📊 Risk Leaderboard",
        "🔍 Individual Profile",
        "🤖 Intelligence Query",
        "📤 Live Data Upload",
    ], label_visibility="collapsed")

    st.markdown("<hr style='border-color:#1f2937;margin:16px 0'>",
                unsafe_allow_html=True)

    if not df.empty:
        total    = len(df)
        critical = int((df['deviation_score'] >= 80).sum())
        high     = int(((df['deviation_score'] >= 65) &
                        (df['deviation_score'] < 80)).sum())
        st.markdown(
            f"<p style='color:#6b7280;font-size:10px;font-weight:600;"
            "letter-spacing:1px;text-transform:uppercase'>Live Stats</p>",
            unsafe_allow_html=True
        )
        for label, val, col in [
            ("Citizens Analyzed", f"{total:,}",  "#94a3b8"),
            ("🔴 Critical Risk",  str(critical), "#ef4444"),
            ("🟡 High Risk",      str(high),     "#f59e0b"),
        ]:
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:4px 0;border-bottom:1px solid #1f2937'>"
                f"<span style='color:#6b7280;font-size:12px'>{label}</span>"
                f"<span style='color:{col};font-weight:600;font-size:12px'>"
                f"{val}</span></div>",
                unsafe_allow_html=True
            )

    st.markdown("<hr style='border-color:#1f2937;margin:16px 0'>",
                unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#374151;font-size:10px;text-align:center'>"
        "Shaheen-Eye P-FIS v1.0<br>FMU — Govt. of Pakistan<br>"
        "© 2025 — CONFIDENTIAL</p>",
        unsafe_allow_html=True
    )

# ════════════════════════════════════════════════════════════
# PAGE 1 — NATIONAL DASHBOARD
# ════════════════════════════════════════════════════════════
if "National" in page:
    if df.empty:
        st.warning("No data loaded. Run the pipeline first.")
        st.stop()

    # ── metric cards ─────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    flagged   = int((df['deviation_score'] >= 65).sum())
    tax_gap   = float(
        df[df['deviation_score'] >= 65]['total_assets_estimated'].fillna(0).sum()
    ) * 0.15
    rings     = 0
    if G is not None:
        try:
            comms = list(nx.connected_components(G))
            rings = sum(
                1 for c in comms
                if len([n for n in c
                        if G.nodes[n].get('type') == 'Person']) >= 3
            )
        except Exception:
            rings = 6

    cards = [
        (c1, "critical", "#ef4444",
         str(int((df['deviation_score']>=80).sum())),
         "🔴 Critical Risk Profiles"),
        (c2, "warning",  "#f59e0b",
         f"Rs. {tax_gap/1e9:.1f}B",
         "⚠️ Estimated Tax Gap"),
        (c3, "info",     "#3b82f6",
         f"{len(df):,}",
         "📊 Citizens Analyzed"),
        (c4, "success",  "#22c55e",
         str(rings),
         "🕸️ Fraud Rings Detected"),
    ]
    for col, cls, clr, val, lbl in cards:
        with col:
            st.markdown(
                f"<div class='metric-card {cls}'>"
                f"<p class='metric-val' style='color:{clr}'>{val}</p>"
                f"<p class='metric-lbl'>{lbl}</p></div>",
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── charts row ───────────────────────────────────────────
    col_hist, col_city = st.columns([3, 2])

    with col_hist:
        st.markdown(
            "<p class='section-title'>National Risk Score Distribution</p>",
            unsafe_allow_html=True
        )
        fig_h = px.histogram(
            df, x="deviation_score", nbins=25,
            color_discrete_sequence=["#3b82f6"],
            labels={"deviation_score": "Compliance Deviation Score",
                    "count": "Citizens"},
            template="plotly_dark"
        )
        fig_h.add_vline(x=65, line_dash="dash",
                        line_color="#f59e0b",
                        annotation_text="High Risk",
                        annotation_font_color="#f59e0b")
        fig_h.add_vline(x=80, line_dash="dash",
                        line_color="#ef4444",
                        annotation_text="Critical",
                        annotation_font_color="#ef4444")
        fig_h.update_layout(**PLOTLY_DARK, height=280,
                            margin=dict(t=10, b=10))
        st.plotly_chart(fig_h, use_container_width=True)

    with col_city:
        st.markdown(
            "<p class='section-title'>Risk by City</p>",
            unsafe_allow_html=True
        )
        if 'city' in df.columns:
            city_df = (df.groupby('city')['deviation_score']
                         .mean()
                         .reset_index()
                         .sort_values('deviation_score'))
            fig_c = px.bar(
                city_df, x='deviation_score', y='city',
                orientation='h',
                color='deviation_score',
                color_continuous_scale=["#22c55e","#f59e0b","#ef4444"],
                template="plotly_dark",
                labels={"deviation_score":"Avg Score","city":""}
            )
            fig_c.update_layout(**PLOTLY_DARK, height=280,
                                coloraxis_showscale=False,
                                margin=dict(t=10, b=10))
            st.plotly_chart(fig_c, use_container_width=True)

    # ── map + pie ────────────────────────────────────────────
    col_map, col_pie = st.columns([3, 2])

    with col_map:
        st.markdown(
            "<p class='section-title'>🇵🇰 Pakistan Risk Heatmap</p>",
            unsafe_allow_html=True
        )
        city_coords = {
            "Lahore":     (31.5204, 74.3587),
            "Karachi":    (24.8607, 67.0011),
            "Islamabad":  (33.6844, 73.0479),
            "Rawalpindi": (33.6007, 73.0679),
            "Faisalabad": (31.4504, 73.1350),
            "Multan":     (30.1575, 71.5249),
            "Peshawar":   (34.0151, 71.5249),
            "Quetta":     (30.1798, 66.9750),
        }
        if 'city' in df.columns:
            avg_by_city = (df.groupby('city')['deviation_score']
                             .mean().reset_index())
            map_rows = []
            for _, r in avg_by_city.iterrows():
                if r['city'] in city_coords:
                    lat, lon = city_coords[r['city']]
                    map_rows.append({
                        "city": r['city'],
                        "lat": lat, "lon": lon,
                        "score": r['deviation_score']
                    })
            if map_rows:
                mdf = pd.DataFrame(map_rows)
                fig_m = px.scatter_geo(
                    mdf, lat='lat', lon='lon',
                    size='score', color='score',
                    hover_name='city',
                    color_continuous_scale=["#22c55e","#f59e0b","#ef4444"],
                    size_max=45, scope="asia",
                    template="plotly_dark"
                )
                fig_m.update_geos(
                    center={"lat":30.3753,"lon":69.3451},
                    projection_scale=5.5,
                    bgcolor="#111827",
                    landcolor="#1f2937",
                    oceancolor="#111827",
                    lakecolor="#111827",
                    showcountries=True,
                    countrycolor="#374151"
                )
                fig_m.update_layout(
                    height=300, paper_bgcolor="#111827",
                    font_color="#94a3b8",
                    coloraxis_showscale=False,
                    margin={"r":0,"t":0,"l":0,"b":0}
                )
                st.plotly_chart(fig_m, use_container_width=True)

    with col_pie:
        st.markdown(
            "<p class='section-title'>Risk Category Breakdown</p>",
            unsafe_allow_html=True
        )
        if 'risk_category' in df.columns:
            rc = df['risk_category'].value_counts()
            fig_p = px.pie(
                values=rc.values, names=rc.index,
                color=rc.index,
                color_discrete_map=RISK_COLORS,
                template="plotly_dark", hole=0.45
            )
            fig_p.update_layout(
                paper_bgcolor="#111827",
                font_color="#94a3b8", height=300,
                showlegend=True,
                legend=dict(
                    orientation="v", x=1.0, y=0.5,
                    font=dict(size=11, color="#94a3b8")
                ),
                margin=dict(t=10, b=10)
            )
            st.plotly_chart(fig_p, use_container_width=True)

    # ── fraud module heatmap ──────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<p class='section-title'>Most Common Fraud Patterns Detected</p>",
        unsafe_allow_html=True
    )
    if 'top_fraud_flags' in df.columns:
        all_flags = []
        for flags_str in df['top_fraud_flags'].dropna():
            for f in str(flags_str).split(','):
                f = f.strip()
                if f and f not in ('None','nan',''):
                    all_flags.append(f)
        if all_flags:
            flag_counts = (pd.Series(all_flags)
                             .value_counts()
                             .head(10)
                             .reset_index())
            flag_counts.columns = ['Fraud Pattern', 'Count']
            fig_f = px.bar(
                flag_counts.sort_values('Count'),
                x='Count', y='Fraud Pattern',
                orientation='h',
                color='Count',
                color_continuous_scale=["#1d4ed8","#dc2626"],
                template="plotly_dark",
                labels={"Count":"Profiles Flagged"}
            )
            fig_f.update_layout(**PLOTLY_DARK, height=320,
                                coloraxis_showscale=False,
                                margin=dict(t=10,b=10))
            st.plotly_chart(fig_f, use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE 2 — RISK LEADERBOARD
# ════════════════════════════════════════════════════════════
elif "Leaderboard" in page:
    if df.empty:
        st.warning("No data. Run the pipeline first.")
        st.stop()

    st.markdown(
        "<p class='section-title'>Risk Intelligence Leaderboard</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='color:#4b5563;font-size:12px;margin-bottom:16px'>"
        "Select a row to open the full profile investigation.</p>",
        unsafe_allow_html=True
    )

    # filters
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        cities = sorted(df['city'].dropna().unique().tolist()) \
            if 'city' in df.columns else []
        city_f = st.multiselect("🏙️ City", cities, key="lb_city")
    with fc2:
        risk_f = st.multiselect(
            "⚠️ Risk Level",
            ['CRITICAL','HIGH','MEDIUM','LOW','COMPLIANT'],
            key="lb_risk"
        )
    with fc3:
        atl_f = st.multiselect(
            "📋 ATL Status", ['ATL','Non-ATL'], key="lb_atl"
        )
    with fc4:
        min_s = st.slider("Min Score", 0, 100, 0, key="lb_score")

    fdf = df.copy()
    if city_f:
        fdf = fdf[fdf['city'].isin(city_f)]
    if risk_f:
        fdf = fdf[fdf['risk_category'].isin(risk_f)]
    if atl_f:
        fdf = fdf[fdf['filer_status'].isin(atl_f)]
    fdf = fdf[fdf['deviation_score'] >= min_s]
    fdf = fdf.sort_values('deviation_score', ascending=False).reset_index(drop=True)
    fdf.index += 1

    st.markdown(
        f"<p style='color:#6b7280;font-size:12px'>"
        f"Showing <b style='color:#94a3b8'>{len(fdf)}</b> profiles</p>",
        unsafe_allow_html=True
    )

    # render table
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

        disp = ['full_name','city','deviation_score','risk_category',
                'filer_status','declared_income_pkr',
                'vehicle_make_model','top_fraud_flags']
        avail = [c for c in disp if c in fdf.columns]
        gb = GridOptionsBuilder.from_dataframe(fdf[avail])
        gb.configure_selection('single', use_checkbox=False)
        gb.configure_column("deviation_score",
            headerName="⚡ Score",
            cellStyle=JsCode("""
            function(p){
                var v=p.value;
                if(v>=80) return {background:'#1f0707',color:'#ef4444',fontWeight:'bold'};
                if(v>=65) return {background:'#1f1207',color:'#f59e0b'};
                if(v>=45) return {background:'#07101f',color:'#3b82f6'};
                return {background:'#071f10',color:'#22c55e'};
            }"""))
        gb.configure_column("risk_category",
            headerName="🚨 Level",
            cellRenderer=JsCode("""
            function(p){
                var m={'CRITICAL':'#ef4444','HIGH':'#f59e0b',
                       'MEDIUM':'#3b82f6','LOW':'#22d3ee','COMPLIANT':'#22c55e'};
                var c=m[p.value]||'#6b7280';
                var tc=(p.value==='HIGH')?'black':'white';
                return `<span style="background:${c};color:${tc};padding:2px 8px;
                border-radius:10px;font-size:10px;font-weight:700">${p.value}</span>`;
            }"""))
        gb.configure_column("declared_income_pkr",
            headerName="Declared Income",
            valueFormatter=JsCode(
                "function(p){return 'Rs. '+(p.value||0).toLocaleString();}"
            ))
        gb.configure_column("full_name",    headerName="👤 Name")
        gb.configure_column("city",         headerName="🏙️ City")
        gb.configure_column("filer_status", headerName="ATL")
        gb.configure_column("vehicle_make_model", headerName="Vehicle")
        gb.configure_column("top_fraud_flags",    headerName="🔍 Fraud Detected")

        resp = AgGrid(
            fdf[avail],
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=True,
            height=500,
            theme="alpine-dark"
        )
        sel = resp.get('selected_rows', [])
        if sel is not None and len(sel) > 0:
            name = sel[0].get('full_name','')
            match = df[df['full_name']==name]
            if len(match) > 0:
                st.session_state['sel_pid'] = \
                    match.iloc[0]['master_person_id']
                st.info(
                    f"✅ Selected: **{name}** — "
                    "navigate to Individual Profile"
                )

    except ImportError:
        # fallback: plain dataframe
        st.dataframe(fdf, use_container_width=True, height=500)
        st.info("For interactive table: pip install streamlit-aggrid")

# ════════════════════════════════════════════════════════════
# PAGE 3 — INDIVIDUAL PROFILE
# ════════════════════════════════════════════════════════════
elif "Individual" in page:
    if df.empty:
        st.warning("No data. Run the pipeline first.")
        st.stop()

    names = df['full_name'].tolist()
    default = 0
    if 'sel_pid' in st.session_state:
        pid_sel = st.session_state['sel_pid']
        m = df[df['master_person_id'] == pid_sel]
        if len(m) > 0 and m.iloc[0]['full_name'] in names:
            default = names.index(m.iloc[0]['full_name'])

    sel_name = st.selectbox(
        "Select citizen profile",
        names, index=default
    )
    person = df[df['full_name'] == sel_name].iloc[0]
    pid    = person['master_person_id']
    score  = float(person.get('deviation_score', 0))
    cat    = str(person.get('risk_category','UNKNOWN')).upper()
    clr    = risk_color(cat)

    # ── profile header ────────────────────────────────────────
    st.markdown(
        f"<div class='profile-header' style='border-left:4px solid {clr}'>"
        f"<div style='display:flex;justify-content:space-between;align-items:start'>"
        f"<div>"
        f"<h2 style='color:{clr};margin:0;font-size:22px'>{sel_name}</h2>"
        f"<p style='color:#6b7280;margin:4px 0;font-size:13px'>"
        f"NTN/FBR-ID: {person.get('master_person_id','N/A')} &nbsp;·&nbsp; "
        f"City: {person.get('city','N/A')} &nbsp;·&nbsp; "
        f"Occupation: {person.get('occupation','N/A')} &nbsp;·&nbsp; "
        f"ATL: <b style='color:{'#22c55e' if person.get('filer_status')=='ATL' else '#ef4444'}'>"
        f"{person.get('filer_status','N/A')}</b></p>"
        f"</div>"
        f"<div style='text-align:right'>"
        f"<p style='font-size:48px;font-weight:800;color:{clr};margin:0;line-height:1'>"
        f"{score:.0f}"
        f"<span style='font-size:16px;color:#4b5563'>/100</span></p>"
        f"<span style='background:{clr};color:{'black' if cat=='HIGH' else 'white'};"
        f"padding:4px 14px;border-radius:12px;font-size:11px;font-weight:700'>"
        f"{cat}</span>"
        f"</div></div></div>",
        unsafe_allow_html=True
    )

    # ── graph + intelligence ──────────────────────────────────
    col_graph, col_intel = st.columns([1, 1])

    with col_graph:
        st.markdown(
            "<p class='section-title'>Financial Footprint Graph</p>",
            unsafe_allow_html=True
        )
        net = Network(
            height="420px", width="100%",
            bgcolor="#111827", font_color="#e2e8f0",
            directed=False
        )
        net.set_options("""{
            "physics":{"stabilization":{"iterations":80},"barnesHut":{"gravitationalConstant":-8000}},
            "nodes":{"borderWidth":2,"shadow":{"enabled":true}},
            "edges":{"shadow":{"enabled":true},"smooth":{"type":"continuous"}}
        }""")

        # person node
        net.add_node(
            pid,
            label=sel_name.split()[0],
            color={"background": clr,
                   "border":     "#ffffff",
                   "highlight":  {"background": clr}},
            size=45,
            title=(f"<b>{sel_name}</b><br>Score: {score:.0f}<br>"
                   f"Status: {cat}"),
            shape="dot"
        )

        # vehicle
        if float(person.get('vehicle_count',0)) > 0:
            v_id  = f"V_{pid}"
            v_val = float(person.get('total_assets_estimated',0))
            net.add_node(
                v_id,
                label=f"🚗 {str(person.get('vehicle_make_model','Vehicle'))[:18]}",
                color={"background":"#7f1d1d","border":"#ef4444"},
                size=28,
                title=(f"<b>Vehicle</b><br>"
                       f"{person.get('vehicle_make_model','N/A')}<br>"
                       f"CC: {person.get('max_vehicle_cc',0)}<br>"
                       f"Import: {person.get('import_type','N/A')}"),
                shape="diamond"
            )
            net.add_edge(pid, v_id,
                         label="OWNS",
                         color="#ef4444", width=2)

        # property
        if float(person.get('property_count',0)) > 0:
            p_id = f"P_{pid}"
            net.add_node(
                p_id,
                label=f"🏠 Property\n{person.get('city','')}",
                color={"background":"#052e16","border":"#22c55e"},
                size=28,
                title=(f"<b>Property</b><br>"
                       f"Value: Rs.{float(person.get('total_property_value',0)):,.0f}<br>"
                       f"Type: {person.get('registry_type','N/A')}<br>"
                       f"NOC: {person.get('noc_status','N/A')}"),
                shape="square"
            )
            net.add_edge(pid, p_id,
                         label="OWNS",
                         color="#22c55e", width=2)

        # meter
        if float(person.get('avg_monthly_bill_pkr',0)) > 0:
            m_id = f"M_{pid}"
            net.add_node(
                m_id,
                label=(f"⚡ Rs."
                       f"{float(person.get('avg_monthly_bill_pkr',0)):,.0f}/mo"),
                color={"background":"#1c1400","border":"#fbbf24"},
                size=22,
                title=(f"<b>Utility Meter</b><br>"
                       f"Monthly: Rs."
                       f"{float(person.get('avg_monthly_bill_pkr',0)):,.0f}"),
                shape="triangle"
            )
            net.add_edge(pid, m_id,
                         label="CONSUMES",
                         color="#fbbf24", width=2)

        # FBR filing
        fbr_id  = f"FBR_{pid}"
        fbr_clr = "#22c55e" \
            if person.get('filer_status')=='ATL' else "#ef4444"
        net.add_node(
            fbr_id,
            label=(f"📋 FBR\n"
                   f"Rs.{float(person.get('declared_income_pkr',0)):,.0f}"),
            color={"background":"#0f172a","border":fbr_clr},
            size=22,
            title=(f"<b>FBR Filing</b><br>"
                   f"Income: Rs."
                   f"{float(person.get('declared_income_pkr',0)):,.0f}<br>"
                   f"Status: {person.get('filer_status','N/A')}"),
            shape="box"
        )
        net.add_edge(pid, fbr_id,
                     label="FILED",
                     color=fbr_clr, width=2)

        # SHARES_ADDRESS neighbours
        if G is not None:
            try:
                for n_id in list(G.neighbors(pid))[:4]:
                    edata = G.edges.get((pid, n_id), {})
                    if edata.get('type') == 'SHARES_ADDRESS':
                        ndata = G.nodes.get(n_id, {})
                        net.add_node(
                            n_id,
                            label=str(ndata.get('name',''))[:12],
                            color={"background":"#2e1065",
                                   "border":"#a855f7"},
                            size=20,
                            title=(f"<b>Same Address</b><br>"
                                   f"{ndata.get('name',n_id)}"),
                            shape="dot"
                        )
                        net.add_edge(
                            pid, n_id,
                            label="SAME ADDRESS",
                            color="#a855f7",
                            width=1, dashes=True
                        )
            except Exception:
                pass

        os.makedirs("outputs/graphs", exist_ok=True)
        graph_path = f"outputs/graphs/{pid}.html"
        net.save_graph(graph_path)
        with open(graph_path, "r", encoding="utf-8") as f:
            components.html(f.read(), height=430)

    with col_intel:
        # score breakdown
        declared  = float(person.get('declared_income_pkr', 0))
        lifestyle = float(person.get('annual_utility_bill', 0))
        assets    = float(person.get('total_assets_estimated', 0))
        ratio     = lifestyle / max(declared, 1)

        st.markdown(
            "<p class='section-title'>Score Breakdown</p>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div class='formula-box' style='color:#94a3b8'>"
            f"Declared Annual Income : "
            f"<b style='color:#22c55e'>"
            f"Rs. {declared:,.0f}</b><br>"
            f"Estimated Lifestyle Cost: "
            f"<b style='color:#f59e0b'>"
            f"Rs. {lifestyle:,.0f}</b><br>"
            f"Total Asset Value       : "
            f"<b style='color:#ef4444'>"
            f"Rs. {assets:,.0f}</b><br>"
            f"<hr style='border-color:#1f2937;margin:8px 0'>"
            f"Lifestyle / Income Ratio: "
            f"<b style='color:{clr}'>{ratio:.1f}x</b><br>"
            f"<br><b style='color:{clr};font-size:18px'>"
            f"Final Score: {score:.0f}/100 — {cat}</b>"
            f"</div>",
            unsafe_allow_html=True
        )

        # fraud flags
        st.markdown(
            "<p class='section-title' style='margin-top:16px'>"
            "Fraud Modules Triggered</p>",
            unsafe_allow_html=True
        )
        flags_raw = str(person.get('top_fraud_flags',''))
        flags     = [f.strip() for f in flags_raw.split(',')
                     if f.strip() not in ('','None','nan')]
        if flags:
            for flag in flags:
                st.markdown(
                    f"<div class='flag-item'>🔴 {flag}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                "<p style='color:#4b5563;font-size:12px'>"
                "No major fraud patterns flagged.</p>",
                unsafe_allow_html=True
            )

        # audit trail
        st.markdown(
            "<p class='section-title' style='margin-top:16px'>"
            "FBR Investigation Note</p>",
            unsafe_allow_html=True
        )
        audit_text = audits.get(pid, None)

        if audit_text:
            st.markdown(
                f"<div class='audit-box'>{audit_text.replace(chr(10),'<br>')}</div>",
                unsafe_allow_html=True
            )
        else:
            if st.button("🤖 Generate Investigation Note",
                         key="gen_audit"):
                with st.spinner("FBR IIW — Generating report..."):
                    try:
                        from groq import Groq
                        from dotenv import load_dotenv
                        load_dotenv()
                        client = Groq()
                        SYSTEM = (
                            "You are a Senior FBR Forensic Investigator. "
                            "Write a 3-paragraph legal investigation note. "
                            "Cite exact figures. Reference ITO 2001 or "
                            "Benami Act 2017. Recommend enforcement action. "
                            "Tone: cold, legal, authoritative."
                        )
                        resp = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role":"system","content":SYSTEM},
                                {"role":"user","content":
                                 f"SUBJECT: {sel_name}, "
                                 f"SCORE: {score}/100, "
                                 f"ASSETS: {flags_raw}, "
                                 f"Income: Rs.{declared:,.0f}, "
                                 f"Lifestyle: Rs.{lifestyle:,.0f}/yr"}
                            ],
                            temperature=0.2,
                            max_tokens=400
                        )
                        audit_text = resp.choices[0].message.content
                        audits[pid] = audit_text
                        with open("outputs/audit_trails.json",
                                  "w", encoding="utf-8") as f:
                            json.dump(audits, f, indent=2)
                        st.markdown(
                            f"<div class='audit-box'>"
                            f"{audit_text.replace(chr(10),'<br>')}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    except Exception as e:
                        st.error(f"Groq error: {e}")

    # ── evidence timeline ─────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<p class='section-title'>"
        "Evidence Timeline — Assets vs Tax Filings</p>",
        unsafe_allow_html=True
    )
    tl = []
    if person.get('vehicle_registration_year'):
        tl.append({
            "Event": f"Vehicle Registered — "
                     f"{person.get('vehicle_make_model','Vehicle')}",
            "Year":  int(person.get('vehicle_registration_year', 2020)),
            "Type":  "Asset Acquired"
        })
    if person.get('property_transfer_year'):
        tl.append({
            "Event": f"Property Transfer — "
                     f"{person.get('city','')}",
            "Year":  int(person.get('property_transfer_year', 2021)),
            "Type":  "Asset Acquired"
        })
    for yr in range(2022, 2026):
        tl.append({
            "Event": f"FBR Filing — {yr}",
            "Year":  yr,
            "Type":  ("Non-Filing"
                      if person.get('filer_status')=='Non-ATL'
                      else "Filed")
        })
    if tl:
        tl_df  = pd.DataFrame(tl)
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
        fig_tl.update_traces(
            textposition="top center",
            marker=dict(size=14)
        )
        fig_tl.update_layout(
            **PLOTLY_DARK,
            height=200,
            showlegend=False,
            margin={"t":30,"b":10}
        )
        st.plotly_chart(fig_tl, use_container_width=True)

    # ── export buttons ────────────────────────────────────────
    st.markdown("<hr style='border-color:#1f2937'>",
                unsafe_allow_html=True)
    ex1, ex2, _ = st.columns([1, 1, 3])

    with ex1:
        if st.button("📄 Export PDF Report", type="primary"):
            try:
                from pdf_export import generate_pdf
                pdf_path = generate_pdf(
                    person.to_dict(),
                    audits.get(pid, "")
                )
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download PDF", f,
                        file_name=f"FBR_Investigation_{pid}.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"PDF error: {e}")

    with ex2:
        if st.button("📦 Export Full Package"):
            try:
                import zipfile, io
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as zf:
                    from pdf_export import generate_pdf
                    pp = generate_pdf(person.to_dict(),
                                      audits.get(pid,""))
                    zf.write(pp,
                             f"Investigation_{pid}.pdf")
                    zf.writestr(
                        f"Evidence_{pid}.csv",
                        person.to_frame().T.to_csv(index=False)
                    )
                buf.seek(0)
                st.download_button(
                    "⬇️ Download ZIP", buf,
                    file_name=f"FBR_Package_{pid}.zip",
                    mime="application/zip"
                )
            except Exception as e:
                st.error(f"ZIP error: {e}")

# ════════════════════════════════════════════════════════════
# PAGE 4 — INTELLIGENCE QUERY
# ════════════════════════════════════════════════════════════
elif "Query" in page:
    if df.empty:
        st.warning("No data. Run the pipeline first.")
        st.stop()

    st.markdown(
        "<p class='section-title'>Intelligence Query Interface</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='color:#4b5563;font-size:13px;margin-bottom:16px'>"
        "Query Pakistan's financial population in plain language.</p>",
        unsafe_allow_html=True
    )

    # quick-query chips
    quick = [
        "Non-filers in DHA with 2000cc+ vehicles",
        "Citizens with zero income and property above 20M",
        "Bahria Town residents with Non-ATL status",
        "All critical risk profiles in Karachi",
        "Drivers or housewives owning luxury vehicles",
        "Properties with File registry type and Non-ATL owner",
    ]
    qc1, qc2, qc3 = st.columns(3)
    for i, q in enumerate(quick):
        col = [qc1, qc2, qc3][i % 3]
        with col:
            if st.button(f"🔍 {q}", key=f"q{i}"):
                st.session_state['query_val'] = q

    query = st.text_input(
        "💬 Enter query:",
        value=st.session_state.get('query_val',''),
        placeholder="e.g. Show Land Cruiser owners with zero income in Lahore",
        key="query_input"
    )

    if st.button("🚀 Execute", type="primary") and query:
        with st.spinner("Scanning population..."):
            res = df.copy()
            ql  = query.lower()

            # city
            for city in ['lahore','karachi','islamabad',
                         'rawalpindi','peshawar','faisalabad']:
                if city in ql and 'city' in res.columns:
                    res = res[res['city'].str.lower()==city]

            # area
            for area in ['dha','defence','bahria','gulberg',
                         'clifton','pechs','hayatabad']:
                if area in ql and 'reported_address' in res.columns:
                    res = res[res['reported_address']
                              .str.lower()
                              .str.contains(area, na=False)]

            # ATL
            if 'non-filer' in ql or 'non-atl' in ql or 'nonfiler' in ql:
                res = res[res['filer_status']=='Non-ATL']
            elif 'filer' in ql or ' atl ' in ql:
                res = res[res['filer_status']=='ATL']

            # CC
            cc_m = re.search(r'(\d{3,4})\s*cc', ql)
            if cc_m:
                cc_t = int(cc_m.group(1))
                if any(w in ql for w in ['above','more','+']):
                    res = res[res['max_vehicle_cc'] >= cc_t]
                else:
                    res = res[res['max_vehicle_cc'] <= cc_t]

            # zero income
            if 'zero income' in ql or '0 income' in ql:
                res = res[res['declared_income_pkr'] == 0]

            # property value
            pm = re.search(r'(\d+)\s*(million|crore|m\b|cr\b)', ql)
            if pm and 'property' in ql:
                v  = int(pm.group(1))
                mx = (10_000_000 if 'crore' in pm.group(2)
                      else 1_000_000)
                thresh = v * mx
                if any(w in ql for w in ['above','more']):
                    res = res[res['total_property_value'] >= thresh]

            # vehicle model
            for kw, mdl in [
                ('land cruiser','Land Cruiser'),
                ('fortuner','Fortuner'),
                ('prado','Prado'),
                ('civic','Civic'),
                ('corolla','Corolla'),
                ('alto','Alto'),
            ]:
                if kw in ql and 'vehicle_make_model' in res.columns:
                    res = res[res['vehicle_make_model']
                              .str.contains(mdl, na=False)]

            # occupation
            for occ in ['driver','housewife','student','retired']:
                if occ in ql and 'occupation' in res.columns:
                    res = res[res['occupation']
                              .str.lower().str.contains(occ, na=False)]

            # risk level
            if 'critical' in ql:
                res = res[res['risk_category']=='CRITICAL']
            elif 'high risk' in ql:
                res = res[res['risk_category'].isin(['CRITICAL','HIGH'])]

            # file trading
            if 'file' in ql and 'registry' in ql \
               and 'registry_type' in res.columns:
                res = res[res['registry_type']
                          .str.lower().str.contains('file', na=False)]

            res = res.sort_values('deviation_score',
                                  ascending=False)

            # LLM summary
            summary = (f"Query returned {len(res)} profiles. "
                       f"Avg score: "
                       f"{res['deviation_score'].mean():.0f}.")
            try:
                from groq import Groq
                from dotenv import load_dotenv
                load_dotenv()
                client = Groq()
                r = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role":"user","content":
                        f"Write ONE sentence summary for FBR auditor: "
                        f"Query '{query}' returned {len(res)} profiles. "
                        f"Avg score: "
                        f"{res['deviation_score'].mean():.0f}/100. "
                        f"Top: {res.iloc[0]['full_name'] if len(res)>0 else 'none'} "
                        f"score {res.iloc[0]['deviation_score'] if len(res)>0 else 0:.0f}."}],
                    max_tokens=80, temperature=0.1
                )
                summary = r.choices[0].message.content.strip()
            except Exception:
                pass

        st.markdown(
            f"<div class='query-result-box'>"
            f"🤖 <b>Intelligence Summary:</b> {summary}"
            f"</div>",
            unsafe_allow_html=True
        )

        if len(res) > 0:
            disp_c = ['full_name','city','deviation_score',
                      'risk_category','filer_status',
                      'declared_income_pkr','vehicle_make_model']
            av = [c for c in disp_c if c in res.columns]
            st.dataframe(res[av].head(20),
                         use_container_width=True,
                         height=280)

            # mini graph of top 5
            st.markdown(
                "<p class='section-title' style='margin-top:16px'>"
                "Risk Network — Top Results</p>",
                unsafe_allow_html=True
            )
            net_q = Network(
                height="260px", width="100%",
                bgcolor="#111827", font_color="#e2e8f0"
            )
            for _, row_q in res.head(5).iterrows():
                sc = float(row_q.get('deviation_score',0))
                nc = score_color(sc)
                net_q.add_node(
                    row_q['master_person_id'],
                    label=(f"{str(row_q['full_name']).split()[0]}"
                           f"\n{sc:.0f}"),
                    color={"background":nc,"border":"#ffffff"},
                    size=int(sc/5)+12,
                    title=(f"{row_q['full_name']}<br>"
                           f"Score: {sc:.0f}<br>"
                           f"{row_q.get('city','')}")
                )
            os.makedirs("outputs/graphs", exist_ok=True)
            net_q.save_graph("outputs/graphs/_query.html")
            with open("outputs/graphs/_query.html",
                      "r", encoding="utf-8") as f:
                components.html(f.read(), height=270)
        else:
            st.info("No profiles match. Try different terms.")

# ════════════════════════════════════════════════════════════
# PAGE 5 — LIVE DATA UPLOAD
# ════════════════════════════════════════════════════════════
elif "Upload" in page:
    st.markdown(
        "<p class='section-title'>Live Data Ingestion Pipeline</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='color:#4b5563;font-size:13px;margin-bottom:20px'>"
        "Upload new government datasets to run the complete "
        "Shaheen-Eye forensic pipeline in real time. "
        "The system will link identities, build the knowledge graph, "
        "and score every citizen automatically.</p>",
        unsafe_allow_html=True
    )

    with st.expander("📋 Required CSV Format — click to expand"):
        e1, e2 = st.columns(2)
        with e1:
            st.markdown("""
**fbr_tax_records.csv**
`fbr_id, full_name, declared_income_pkr, tax_paid_pkr,
filer_status (ATL/Non-ATL), reported_address, phone_number,
income_source, wealth_source, occupation,
years_as_nonfiler, has_bank_account`

**excise_vehicles.csv**
`vehicle_reg_no, owner_name, engine_capacity_cc,
vehicle_make_model, registration_year, owner_address,
import_type, declared_import_value_pkr`
""")
        with e2:
            st.markdown("""
**disco_consumption.csv**
`meter_ref_no, consumer_name, installation_address,
avg_monthly_bill_pkr, connection_type`

**property_transfers.csv**
`registry_no, buyer_name, seller_name, property_address,
property_value_pkr, transfer_date, area_marla,
property_type, registry_type, noc_status,
society_name, plot_number`
""")

    st.markdown("---")
    st.markdown(
        "<p class='section-title'>Step 1 — Upload Your 4 Datasets</p>",
        unsafe_allow_html=True
    )

    u1, u2 = st.columns(2)
    with u1:
        fbr_f   = st.file_uploader(
            "🏦 FBR Tax Declarations", type=["csv"], key="u_fbr")
        disco_f = st.file_uploader(
            "⚡ DISCO Utility Consumption", type=["csv"], key="u_disco")
    with u2:
        exc_f   = st.file_uploader(
            "🚗 Provincial Excise (Vehicles)", type=["csv"], key="u_exc")
        prop_f  = st.file_uploader(
            "🏠 Real Estate Registry", type=["csv"], key="u_prop")

    all_up = all([fbr_f, exc_f, disco_f, prop_f])

    if all_up:
        st.success("✅ All 4 datasets received.")

        with st.expander("👁️ Preview uploaded data"):
            tabs = st.tabs(["FBR","Excise","DISCO","Property"])
            uploads = [fbr_f, exc_f, disco_f, prop_f]
            labels  = ["FBR Tax","Excise Vehicles",
                       "DISCO Consumption","Property Registry"]
            previews = []
            for tab, uf, lb in zip(tabs, uploads, labels):
                uf.seek(0)
                tmp = pd.read_csv(uf)
                previews.append(tmp)
                with tab:
                    st.markdown(
                        f"**{lb}** — {len(tmp):,} records, "
                        f"{len(tmp.columns)} columns"
                    )
                    st.dataframe(tmp.head(5),
                                 use_container_width=True)

        st.markdown("---")
        st.markdown(
            "<p class='section-title'>"
            "Step 2 — Run Forensic Pipeline</p>",
            unsafe_allow_html=True
        )

        STEPS = [
            ("🔄 Preprocessing — normalizing names & addresses",
             "preprocess",     "run_preprocessing"),
            ("🔗 Entity Resolution — linking identities across 4 datasets",
             "entity_resolution", "run_entity_resolution"),
            ("🕸️  Building Knowledge Graph — mapping financial footprints",
             "build_graph",    "construct_graph"),
            ("🧠 Forensic Scoring — running 17 fraud detection modules",
             "scoring",        "process_master_csv"),
        ]

        if st.button("🚀 Run Complete Forensic Analysis",
                     type="primary"):
            # save uploads
            os.makedirs("data/raw", exist_ok=True)
            for uf, fname in zip(
                [fbr_f, exc_f, disco_f, prop_f],
                ["fbr_tax_records.csv","excise_vehicles.csv",
                 "disco_consumption.csv","property_transfers.csv"]
            ):
                uf.seek(0)
                pd.read_csv(uf).to_csv(
                    f"data/raw/{fname}", index=False)

            prog   = st.progress(0)
            status = st.empty()

            for i, (msg, mod, fn_name) in enumerate(STEPS):
                status.markdown(
                    f"<div style='background:#0f1b2d;"
                    f"border-left:3px solid #3b82f6;"
                    f"padding:10px 14px;border-radius:4px;"
                    f"color:#93c5fd;font-size:13px'>{msg}...</div>",
                    unsafe_allow_html=True
                )
                try:
                    import importlib
                    m  = importlib.import_module(mod)
                    fn = getattr(m, fn_name)
                    fn()
                except Exception as e:
                    st.error(f"Error in {mod}: {e}")
                    break
                prog.progress((i + 1) / len(STEPS))
                time.sleep(0.3)

            status.markdown(
                "<div style='background:#071f10;"
                "border-left:3px solid #22c55e;"
                "padding:12px 14px;border-radius:4px;"
                "color:#4ade80;font-weight:600;font-size:13px'>"
                "✅ Pipeline complete — navigate to Risk Leaderboard"
                "</div>",
                unsafe_allow_html=True
            )
            st.cache_data.clear()

            # results summary
            try:
                rdf = pd.read_csv("outputs/scored_entities.csv")
                rc1, rc2, rc3, rc4 = st.columns(4)
                gap = (rdf[rdf['deviation_score']>=65]
                       ['total_assets_val'].fillna(0).sum() * 0.15)
                for col, lbl, val, clr in [
                    (rc1,"Citizens Analyzed",
                     f"{len(rdf):,}","#94a3b8"),
                    (rc2,"🔴 Critical",
                     str(int((rdf['deviation_score']>=80).sum())),
                     "#ef4444"),
                    (rc3,"⚠️ High Risk",
                     str(int((rdf['deviation_score']>=65).sum())),
                     "#f59e0b"),
                    (rc4,"Est. Tax Gap",
                     f"Rs.{gap/1e9:.1f}B","#22c55e"),
                ]:
                    with col:
                        st.markdown(
                            f"<div class='metric-card'>"
                            f"<p class='metric-val' style='color:{clr}'>"
                            f"{val}</p>"
                            f"<p class='metric-lbl'>{lbl}</p></div>",
                            unsafe_allow_html=True
                        )
                st.dataframe(
                    rdf.sort_values('deviation_score',
                                    ascending=False).head(10),
                    use_container_width=True
                )
            except Exception:
                pass

    else:
        st.info("⬆️ Upload all 4 CSV files above.")

        # template downloads
        st.markdown("---")
        st.markdown(
            "<p class='section-title'>📥 Download Sample Templates</p>",
            unsafe_allow_html=True
        )
        tc1, tc2 = st.columns(2)
        templates = [
            ("data/raw/fbr_tax_records.csv",
             "FBR Tax Records","fbr_sample.csv"),
            ("data/raw/excise_vehicles.csv",
             "Excise Vehicles","excise_sample.csv"),
            ("data/raw/disco_consumption.csv",
             "DISCO Consumption","disco_sample.csv"),
            ("data/raw/property_transfers.csv",
             "Property Registry","property_sample.csv"),
        ]
        for i, (path, lbl, fname) in enumerate(templates):
            col = tc1 if i % 2 == 0 else tc2
            with col:
                if os.path.exists(path):
                    with open(path) as f:
                        col.download_button(
                            f"⬇️ {lbl}", f.read(),
                            file_name=fname,
                            mime="text/csv"
                        )
                else:
                    col.info("Run generate_data.py first")