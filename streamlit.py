import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time

from main import main

st.set_page_config(
    page_title="Airline Disruption Recovery",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Minimal CSS — only what Streamlit won't fight
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
.block-container { padding-top: 0 !important; padding-left: 2rem !important; padding-right: 2rem !important; max-width: 100% !important; }
.stTabs [data-baseweb="tab-list"] { background: #fff; gap: 4px; }
.stTabs [data-baseweb="tab"] { font-size: 13px; font-weight: 500; }
.stTabs [aria-selected="true"] { color: #2563eb !important; font-weight: 700 !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: #2563eb !important; }
</style>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data
def get_flight_data():
    return pd.DataFrame([
        {"Flight":"AA101","Aircraft":"A320-01","From":"JFK","To":"LAX","Dep":"08:00","Arr":"11:30","PAX":156,"Status":"Scheduled","Delay":0},
        {"Flight":"AA102","Aircraft":"B737-03","From":"LAX","To":"ORD","Dep":"09:15","Arr":"14:45","PAX":142,"Status":"Recovered","Delay":25},
        {"Flight":"AA103","Aircraft":"A321-07","From":"ORD","To":"DFW","Dep":"10:00","Arr":"12:30","PAX":187,"Status":"Delayed","Delay":45},
        {"Flight":"AA104","Aircraft":"B777-02","From":"DFW","To":"MIA","Dep":"07:30","Arr":"11:00","PAX":214,"Status":"Scheduled","Delay":0},
        {"Flight":"AA105","Aircraft":"A320-05","From":"MIA","To":"JFK","Dep":"12:00","Arr":"15:30","PAX":163,"Status":"Cancelled","Delay":0},
        {"Flight":"AA106","Aircraft":"B737-01","From":"SEA","To":"SFO","Dep":"06:45","Arr":"09:00","PAX":128,"Status":"Scheduled","Delay":0},
        {"Flight":"AA107","Aircraft":"A321-03","From":"SFO","To":"DEN","Dep":"10:30","Arr":"13:45","PAX":175,"Status":"Recovered","Delay":15},
        {"Flight":"AA108","Aircraft":"B777-05","From":"DEN","To":"ATL","Dep":"08:00","Arr":"12:15","PAX":231,"Status":"Scheduled","Delay":0},
    ])

@st.cache_data
def get_aircraft_data():
    return pd.DataFrame([
        {"Aircraft":"A320-01","Type":"A320","Seats":156,"Base":"JFK","Status":"Active","Util%":87},
        {"Aircraft":"B737-03","Type":"B737","Seats":142,"Base":"LAX","Status":"Active","Util%":74},
        {"Aircraft":"A321-07","Type":"A321","Seats":187,"Base":"ORD","Status":"Active","Util%":91},
        {"Aircraft":"B777-02","Type":"B777","Seats":214,"Base":"DFW","Status":"Active","Util%":95},
        {"Aircraft":"A320-05","Type":"A320","Seats":163,"Base":"MIA","Status":"Maintenance","Util%":38},
        {"Aircraft":"B737-01","Type":"B737","Seats":128,"Base":"SEA","Status":"Active","Util%":82},
        {"Aircraft":"A321-03","Type":"A321","Seats":175,"Base":"SFO","Status":"Active","Util%":79},
        {"Aircraft":"B777-05","Type":"B777","Seats":231,"Base":"DEN","Status":"Active","Util%":88},
    ])

@st.cache_data
def get_airport_data():
    return pd.DataFrame([
        {"Code":"JFK","City":"New York","Lat":40.6413,"Lon":-73.7781,"AvgDelay":42,"Flights":84},
        {"Code":"LAX","City":"Los Angeles","Lat":33.9425,"Lon":-118.408,"AvgDelay":18,"Flights":61},
        {"Code":"ORD","City":"Chicago","Lat":41.9742,"Lon":-87.9073,"AvgDelay":35,"Flights":73},
        {"Code":"DFW","City":"Dallas","Lat":32.8998,"Lon":-97.0403,"AvgDelay":22,"Flights":58},
        {"Code":"MIA","City":"Miami","Lat":25.7959,"Lon":-80.287,"AvgDelay":15,"Flights":42},
        {"Code":"SEA","City":"Seattle","Lat":47.4502,"Lon":-122.3088,"AvgDelay":8,"Flights":37},
        {"Code":"SFO","City":"San Francisco","Lat":37.6213,"Lon":-122.379,"AvgDelay":20,"Flights":49},
        {"Code":"ATL","City":"Atlanta","Lat":33.6407,"Lon":-84.4277,"AvgDelay":28,"Flights":67},
        {"Code":"DEN","City":"Denver","Lat":39.8561,"Lon":-104.6737,"AvgDelay":12,"Flights":44},
    ])

flight_df   = get_flight_data()
aircraft_df = get_aircraft_data()
airport_df  = get_airport_data()

# ── Session state ─────────────────────────────────────────────────────────────
if "chat_history"   not in st.session_state: st.session_state.chat_history = []
if "opt_status"     not in st.session_state: st.session_state.opt_status   = "Optimal"
if "show_math"      not in st.session_state: st.session_state.show_math    = False
if "chat_key"       not in st.session_state: st.session_state.chat_key     = 0
if "uploaded"       not in st.session_state: st.session_state.uploaded     = {
    "Flights":True,"Aircraft":True,"Airports":False,"Crew":False,"Maintenance":False,"Passenger":False
}

# ══════════════════════════════════════════════════════════════════
# HEADER  — pure HTML, fixed height, no Streamlit columns
# ══════════════════════════════════════════════════════════════════
sc_color = {"Optimal":"#10b981","Running":"#f59e0b","Infeasible":"#ef4444"}.get(st.session_state.opt_status,"#10b981")
now_str  = datetime.now().strftime("%b %d · %H:%M")

st.markdown(f"""
<div style="background:linear-gradient(135deg,#1e40af,#3b82f6,#06b6d4);
            padding:14px 32px;display:flex;justify-content:space-between;
            align-items:center;border-radius:12px;margin-bottom:16px;
            box-shadow:0 4px 16px rgba(37,99,235,0.25);">
  <div style="display:flex;align-items:center;gap:14px;">
    <div style="font-size:28px;">✈️</div>
    <div>
      <div style="color:#fff;font-weight:800;font-size:18px;letter-spacing:-0.02em;">Airline Disruption Recovery</div>
      <div style="color:rgba(255,255,255,0.75);font-size:12px;">Aircraft Scheduling Optimization · Winter Storm Alpha</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:28px;">
    <div style="text-align:right;">
      <div style="color:rgba(255,255,255,0.6);font-size:10px;text-transform:uppercase;letter-spacing:.05em;">Last Run</div>
      <div style="color:#fff;font-weight:700;font-size:13px;">{now_str}</div>
    </div>
    <div style="text-align:right;">
      <div style="color:rgba(255,255,255,0.6);font-size:10px;text-transform:uppercase;letter-spacing:.05em;">Solver</div>
      <div style="color:#fff;font-weight:700;font-size:13px;">HiGHS · 4.21s</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;background:rgba(255,255,255,0.2);
                padding:8px 16px;border-radius:24px;border:1px solid rgba(255,255,255,0.3);">
      <div style="width:9px;height:9px;border-radius:50%;background:{sc_color};box-shadow:0 0 8px {sc_color};"></div>
      <span style="color:#fff;font-weight:700;font-size:13px;">{st.session_state.opt_status}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# KPI ROW  — native st.metric inside styled containers
# ══════════════════════════════════════════════════════════════════

results = main()
kpi_cols = st.columns(7)
# kpis = [
#     ("✈️ Flights Scheduled", "284",    "+12 vs baseline",  "#3b82f6"),
#     ("🔄 Flights Recovered",  "47",    "+8 vs baseline",   "#10b981"),
#     ("⚡ Aircraft Util.",      "91.4%", "+3.2% vs baseline","#8b5cf6"),
#     ("⏱️ Delay Min. Saved",   "2,840", "−620 min total",   "#f59e0b"),
#     ("💰 Total Op. Cost",      "$1.24M","−$180K vs baseline","#ef4444"),
#     ("👥 Passenger Impact",   "6,204", "−920 pax affected","#06b6d4"),
#     ("⚙️ Solver Runtime",     "4.2s",  "−1.8s faster",     "#10b981"),
# ]
kpis = [
    ("✈️ Flights Scheduled", results["total_flights"],  "#3b82f6"),
    ("🔄 Flights Recovered",  "47",    "+8 vs baseline",   "#10b981"),
    ("⚡ Aircraft Util.",   results["aircraft_used"],"#8b5cf6"),
    ("⏱️ Delay Min. Saved",   "2,840", "−620 min total",   "#f59e0b"),
    ("💰 Total Op. Cost",      "$1.24M","−$180K vs baseline","#ef4444"),
    ("👥 Passenger Impact", results["total_passengers"], "#06b6d4"),
    ("⚙️ Solver Runtime", round(results["runtime"]), "#10b981"),
] 

    
for col, (label, value, delta, color) in zip(kpi_cols, kpis):
    with col:
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e2e8f0;border-top:3px solid {color};
                    border-radius:10px;padding:14px 12px;text-align:center;
                    box-shadow:0 1px 4px rgba(0,0,0,0.05);height:100px;">
          <div style="font-size:10px;color:#94a3b8;font-weight:600;text-transform:uppercase;
                      letter-spacing:.05em;margin-bottom:6px;">{label}</div>
          <div style="font-size:22px;font-weight:800;color:#0f172a;line-height:1;">{value}</div>
          <div style="font-size:11px;color:{color};font-weight:600;margin-top:5px;">{delta}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📐 Problem Definition",
    "🗂️ Data Management",
    "⚙️ Optimization Engine",
    "🔍 Solution Explorer",
    "📊 Analytics & KPI",
    "🤖 AI Copilot",
])

# ─────────────────────────────────────────────
# TAB 1 — PROBLEM DEFINITION
# ─────────────────────────────────────────────
with tab1:
    st.markdown("#### Business Objectives")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        objectives = [
            ("✈️","Aircraft Assignment","#dbeafe","#2563eb","Optimally assign aircraft to flight legs respecting type, range, and capacity."),
            ("🔄","Flight Recovery","#d1fae5","#059669","Re-route disrupted flights to minimise cascade delays across the network."),
            ("⏱️","Delay Minimisation","#fef3c7","#d97706","Reduce total delay minutes weighted by passenger count and connection criticality."),
            ("❌","Cancellation Minimisation","#fee2e2","#dc2626","Explore all feasible alternatives before cancelling any flight."),
            ("💰","Cost Optimisation","#f3e8ff","#7c3aed","Balance operating, delay, and cancellation costs against service targets."),
        ]
        for icon, title, bg, color, desc in objectives:
            st.markdown(f"""
            <div style="display:flex;gap:12px;padding:12px 14px;background:{bg};
                        border-left:4px solid {color};border-radius:8px;margin-bottom:8px;">
              <span style="font-size:20px;">{icon}</span>
              <div>
                <div style="font-weight:700;font-size:13px;color:{color};">{title}</div>
                <div style="font-size:12px;color:#475569;margin-top:2px;">{desc}</div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("#### Model Assumptions")
        assumptions = pd.DataFrame([
            ("Min turnaround","45 min","Domestic short-haul"),
            ("Max delay","180 min","Beyond → cancellation"),
            ("Delay cost rate","$85/min","Weighted avg pax"),
            ("Cancellation penalty","$12,000","Includes rebooking"),
            ("Aircraft swap cost","$2,500","Repositioning + crew"),
            ("Planning horizon","24 hours","Rolling window"),
            ("Min crew rest","10 hours","FAA Part 117"),
            ("MIP gap","0.01%","Optimality certificate"),
        ], columns=["Parameter","Value","Notes"])
        st.dataframe(assumptions, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("#### Mathematical Model")
        if st.button("📖 Toggle Formulation"):
            st.session_state.show_math = not st.session_state.show_math
        if st.session_state.show_math:
            st.code("""
Sets:  F = {flights},  A = {aircraft}

Variables:
  x(a,f) ∈ {0,1}  — 1 if aircraft a on flight f
  c(f)   ∈ {0,1}  — 1 if flight f cancelled
  d(f)   ≥ 0      — delay minutes for flight f

Objective:
  min  Σ c_op(a,f)·x(a,f)
     + Σ c_d(f)·d(f)
     + Σ c_c(f)·c(f)

Constraints:
  Σ_a x(a,f) + c(f) = 1   ∀f  (coverage)
  continuity, compatibility,
  d(f) ≤ D_max·(1−c(f))   (delay cap)
            """, language="text")

        st.markdown("#### Network Flow")
        fig_net = go.Figure()
        routes = [("JFK","LAX"),("LAX","ORD"),("ORD","DFW"),("DFW","MIA"),
                  ("SEA","SFO"),("SFO","DEN"),("DEN","ATL"),("ATL","JFK"),("ORD","ATL")]
        ap = airport_df.set_index("Code")
        for r in routes:
            if r[0] in ap.index and r[1] in ap.index:
                fig_net.add_trace(go.Scattergeo(
                    lon=[ap.loc[r[0],"Lon"],ap.loc[r[1],"Lon"]],
                    lat=[ap.loc[r[0],"Lat"],ap.loc[r[1],"Lat"]],
                    mode="lines", line=dict(width=2,color="rgba(59,130,246,0.4)"),
                    showlegend=False))
        fig_net.add_trace(go.Scattergeo(
            lon=airport_df.Lon, lat=airport_df.Lat, text=airport_df.Code,
            mode="markers+text",
            marker=dict(size=12,color="#2563eb",line=dict(width=2,color="#fff")),
            textposition="top center", textfont=dict(size=11,color="#1e293b"),
            showlegend=False))
        fig_net.update_layout(
            geo=dict(scope="usa",showland=True,landcolor="#f8faff",
                     showcoastlines=True,coastlinecolor="#e2e8f0",bgcolor="#fff"),
            margin=dict(l=0,r=0,t=0,b=0), height=280, paper_bgcolor="#fff")
        st.plotly_chart(fig_net, use_container_width=True, config={"displayModeBar":False})

# ─────────────────────────────────────────────
# TAB 2 — DATA MANAGEMENT
# ─────────────────────────────────────────────
with tab2:
    c1, c2 = st.columns([1,1.4], gap="large")
    with c1:
        st.markdown("#### Data Upload Center")
        file_configs = [
            ("Flights","✈️","#3b82f6"),("Aircraft","🛫","#8b5cf6"),
            ("Airports","🏢","#06b6d4"),("Crew","👨‍✈️","#10b981"),
            ("Maintenance","🔧","#f59e0b"),("Passenger","👥","#ef4444"),
        ]
        g1, g2 = st.columns(2)
        for i, (name, icon, color) in enumerate(file_configs):
            col = g1 if i % 2 == 0 else g2
            with col:
                loaded = st.session_state.uploaded.get(name, False)
                bg     = f"{color}15" if loaded else "#f8fafc"
                border = f"2px solid {color}" if loaded else "2px dashed #cbd5e1"
                tick   = "✅" if loaded else "📤"
                st.markdown(f"""
                <div style="border:{border};border-radius:10px;padding:12px;
                            background:{bg};margin-bottom:10px;text-align:center;">
                  <div style="font-size:20px;">{tick}</div>
                  <div style="font-weight:700;font-size:12px;color:#1e293b;">{icon} {name}.csv</div>
                  <div style="font-size:11px;color:{'#059669' if loaded else '#94a3b8'};">
                    {'Loaded' if loaded else 'Not uploaded'}
                  </div>
                </div>""", unsafe_allow_html=True)
                if st.button("Reset" if loaded else "Upload", key=f"up_{name}", use_container_width=True):
                    st.session_state.uploaded[name] = not loaded
                    st.rerun()

        st.markdown("#### Validation Report")
        validations = [
            ("✅","No missing values in Flights dataset","#d1fae5","#065f46"),
            ("✅","Aircraft fleet compatibility verified","#d1fae5","#065f46"),
            ("⚠️","3 route conflicts at Slot 14:30","#fef3c7","#92400e"),
            ("⚠️","AA103 turnaround below minimum (38 min)","#fef3c7","#92400e"),
            ("❌","Maintenance overlap: A320-05 at ORD","#fee2e2","#991b1b"),
        ]
        for icon, msg, bg, color in validations:
            st.markdown(f"""
            <div style="background:{bg};border-radius:8px;padding:9px 12px;
                        margin-bottom:6px;font-size:12px;font-weight:500;color:{color};">
              {icon} {msg}
            </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown("#### Flights Dataset")
        def style_status(val):
            m = {"Scheduled":"background:#dbeafe;color:#1d4ed8",
                 "Recovered":"background:#d1fae5;color:#065f46",
                 "Delayed":"background:#fef3c7;color:#92400e",
                 "Cancelled":"background:#fee2e2;color:#991b1b"}
            return m.get(val,"")
        st.dataframe(flight_df.style.map(style_status,subset=["Status"]),
                     use_container_width=True, hide_index=True, height=260)

        st.markdown("#### Airport Delay Index")
        colors_d = ["#ef4444" if d>30 else "#f59e0b" if d>20 else "#10b981"
                    for d in airport_df.AvgDelay]
        fig_ap = go.Figure(go.Bar(x=airport_df.Code, y=airport_df.AvgDelay,
                                   marker_color=colors_d,
                                   text=airport_df.AvgDelay.astype(str)+" min",
                                   textposition="outside"))
        fig_ap.update_layout(margin=dict(l=0,r=0,t=10,b=0),height=180,
                              plot_bgcolor="#fff",paper_bgcolor="#fff",
                              yaxis=dict(gridcolor="#f1f5f9"),showlegend=False)
        st.plotly_chart(fig_ap, use_container_width=True, config={"displayModeBar":False})

        st.markdown("#### Aircraft Fleet")
        st.dataframe(aircraft_df.style.bar(subset=["Util%"],color="#3b82f6"),
                     use_container_width=True, hide_index=True, height=200)

# ─────────────────────────────────────────────
# TAB 3 — OPTIMIZATION ENGINE
# ─────────────────────────────────────────────
with tab3:
    c1, c2, c3 = st.columns([1.1,1.2,0.7], gap="large")

    with c1:
        st.markdown("#### Scenario Parameters")
        st.slider("Delay Penalty ($/min)", 20, 200, 85, 5)
        st.slider("Cancellation Penalty ($)", 5000, 30000, 12000, 500)
        st.slider("Aircraft Swap Cost ($)", 500, 10000, 2500, 250)
        st.slider("Maintenance Buffer (min)", 0, 60, 15, 5)
        st.slider("Passenger Priority Weight", 0.0, 1.0, 0.7, 0.1)
        st.markdown("#### Solver Configuration")
        solver = st.radio("Solver", ["Gurobi","HiGHS","CBC"], horizontal=True, index=1)
        a, b = st.columns(2)
        with a:
            st.number_input("Time Limit (s)", value=300, step=60)
            st.number_input("Threads", value=8, step=1)
        with b:
            st.number_input("MIP Gap (%)", value=0.01, step=0.01, format="%.3f")
            st.selectbox("Presolve", ["Aggressive","Moderate","Off"])

    with c2:
        st.markdown("#### Optimization Monitor")
        log_box   = st.empty()
        prog_box  = st.empty()
        chart_box = st.empty()

        log_lines = [
            "[00:00.1] Building MIP model...",
            "[00:00.4] Variables: 1,248 binary, 312 continuous",
            "[00:00.6] Constraints: 4,892",
            "[00:01.0] Preprocessing: 847 variables eliminated",
            "[00:01.4] Root relaxation: Obj = 1,204,560",
            "[00:01.9] Branch & Bound: Node 0, Obj = 1,189,420",
            "[00:02.3] Cut generation: Gomory, MIR cuts applied",
            "[00:02.8] Node 14, Best bound = 1,162,300 (Gap: 2.1%)",
            "[00:03.4] Node 41, Best bound = 1,241,200 (Gap: 0.8%)",
            "[00:03.9] Optimal solution found!  Obj = 1,238,540",
            "[00:04.2] MIP Gap: 0.0001% ✓  Runtime: 4.21s",
        ]
        obj_vals = [1204560,1189420,1180000,1162300,1250000,1245000,1241200,1239000,1238540]

        def show_log(lines):
            rows = "".join(
                f'<div style="color:{"#34d399" if "✓" in l or "Optimal" in l else "#94a3b8"}">{l}</div>'
                for l in lines)
            log_box.markdown(
                f'<div style="background:#0f172a;border-radius:10px;padding:14px;'
                f'font-family:monospace;font-size:11px;height:180px;overflow-y:auto;">{rows}</div>',
                unsafe_allow_html=True)

        def show_chart(objs):
            fig = go.Figure()
            if objs:
                fig.add_trace(go.Scatter(x=list(range(len(objs))), y=objs,
                    mode="lines+markers",
                    line=dict(color="#2563eb",width=2.5),
                    marker=dict(size=7,color="#2563eb"),
                    fill="tozeroy", fillcolor="rgba(37,99,235,0.08)"))
            fig.update_layout(height=160,margin=dict(l=0,r=0,t=24,b=0),
                plot_bgcolor="#f8faff",paper_bgcolor="#fff",
                title=dict(text="Objective Value Progress",font=dict(size=12),x=0),
                yaxis=dict(gridcolor="#e2e8f0",tickformat="$,.0f"),
                xaxis=dict(title="B&B Nodes",gridcolor="#e2e8f0"),showlegend=False)
            chart_box.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        show_log(["Ready. Press Run Optimization to begin."])
        show_chart([])

    with c3:
        st.markdown("#### Controls")
        if st.button("🧱 Build Model", use_container_width=True):
            show_log(["Building model...", "Loading data..."])
        run = st.button("▶ Run Optimization", use_container_width=True, type="primary")
        st.button("⏹ Stop Solver", use_container_width=True)
        st.button("⬇ Export Solution", use_container_width=True)

        if run:
            st.session_state.opt_status = "Running"
            shown_lines, shown_objs = [], []
            for i, line in enumerate(log_lines):
                shown_lines.append(line)
                show_log(shown_lines)
                if i >= 4 and i < len(obj_vals)+4:
                    shown_objs.append(obj_vals[min(i-4, len(obj_vals)-1)])
                    show_chart(shown_objs)
                prog_box.progress((i+1)/len(log_lines))
                time.sleep(0.35)
            st.session_state.opt_status = "Optimal"
            st.rerun()

        st.markdown("#### Model Stats")
        stats = [("Variables","1,248"),("Constraints","4,892"),
                 ("Non-zeros","18,441"),("Solver",solver),
                 ("MIP Gap","0.0001%"),("Status",st.session_state.opt_status)]
        for k, v in stats:
            color = "#059669" if v=="Optimal" else "#f59e0b" if v=="Running" else "#1e293b"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:7px 0;
                        border-bottom:1px solid #f1f5f9;font-size:12px;">
              <span style="color:#64748b;">{k}</span>
              <span style="font-weight:700;color:{color};">{v}</span>
            </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TAB 4 — SOLUTION EXPLORER
# ─────────────────────────────────────────────
with tab4:
    st.markdown("#### Flight Recovery Summary")
    r1, r2, r3, r4 = st.columns(4)
    for col, label, val, bg, fg in [
        (r1,"Recovered","47","#d1fae5","#065f46"),
        (r2,"Delayed","18","#fef3c7","#92400e"),
        (r3,"Cancelled","3","#fee2e2","#991b1b"),
        (r4,"On-Time","216","#dbeafe","#1d4ed8"),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:{bg};border-radius:12px;padding:20px 18px;
                        border:1px solid {fg}40;margin-bottom:16px;">
              <div style="font-size:11px;font-weight:700;color:{fg};text-transform:uppercase;
                          letter-spacing:.06em;margin-bottom:8px;">{label}</div>
              <div style="font-size:40px;font-weight:800;color:{fg};line-height:1;">{val}</div>
            </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([1.2, 0.8], gap="large")
    with c1:
        st.markdown("#### Aircraft Assignment Table")
        def style_s(v):
            m = {"Scheduled":"background:#dbeafe;color:#1d4ed8",
                 "Recovered":"background:#d1fae5;color:#065f46",
                 "Delayed":"background:#fef3c7;color:#92400e",
                 "Cancelled":"background:#fee2e2;color:#991b1b"}
            return m.get(v,"")
        st.dataframe(flight_df.style.map(style_s,subset=["Status"]),
                     use_container_width=True, hide_index=True, height=240)

        st.markdown("#### Aircraft Rotation Gantt")
        gantt = pd.DataFrame([
            {"Aircraft":"A320-01","Flight":"AA101","Start":6.0,"End":9.0,"Type":"Scheduled"},
            {"Aircraft":"A320-01","Flight":"MX","Start":9.5,"End":10.5,"Type":"Maintenance"},
            {"Aircraft":"A320-01","Flight":"AA109","Start":11.0,"End":14.0,"Type":"Scheduled"},
            {"Aircraft":"B737-03","Flight":"AA102","Start":7.0,"End":10.5,"Type":"Recovered"},
            {"Aircraft":"B737-03","Flight":"AA115","Start":12.0,"End":15.0,"Type":"Scheduled"},
            {"Aircraft":"A321-07","Flight":"AA103","Start":8.0,"End":11.5,"Type":"Delayed"},
            {"Aircraft":"A321-07","Flight":"AA121","Start":13.0,"End":16.0,"Type":"Scheduled"},
            {"Aircraft":"B777-02","Flight":"AA104","Start":5.0,"End":8.0,"Type":"Scheduled"},
            {"Aircraft":"B777-02","Flight":"AA118","Start":10.0,"End":14.0,"Type":"Scheduled"},
            {"Aircraft":"A320-05","Flight":"CNCL","Start":9.0,"End":11.0,"Type":"Cancelled"},
        ])
        cmap = {"Scheduled":"#2563eb","Recovered":"#059669","Delayed":"#f59e0b",
                "Cancelled":"#dc2626","Maintenance":"#7c3aed"}
        base = datetime(2025,1,15)
        fig_g = go.Figure()
        for _, row in gantt.iterrows():
            fig_g.add_trace(go.Bar(
                x=[(row.End-row.Start)], y=[row.Aircraft],
                base=[row.Start], orientation="h",
                marker_color=cmap[row.Type], name=row.Type,
                text=row.Flight, textposition="inside",
                insidetextanchor="middle", textfont=dict(color="#fff",size=10),
                showlegend=False,
                hovertemplate=f"<b>{row.Flight}</b><br>{row.Start:.0f}:00–{row.End:.0f}:00<br>{row.Type}<extra></extra>"))
        for t, c in cmap.items():
            fig_g.add_trace(go.Bar(x=[0],y=[""],orientation="h",
                marker_color=c,name=t,showlegend=True))
        fig_g.update_layout(barmode="stack",height=260,
            margin=dict(l=0,r=0,t=10,b=0),plot_bgcolor="#fff",paper_bgcolor="#fff",
            xaxis=dict(title="Hour of Day",range=[4,18],gridcolor="#f1f5f9",
                tickvals=list(range(5,19)),ticktext=[f"{h}:00" for h in range(5,19)]),
            yaxis=dict(title=""),
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0,font=dict(size=11)))
        st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar":False})

    with c2:
        st.markdown("#### Top Recovery Actions")
        actions = [
            ("AA105 → AA093","Aircraft swap A320-05 → A319-02","Saves 180 min","#10b981"),
            ("AA103 → AA091","Slot reassignment JFK 14:45→15:20","Avoids conflict","#3b82f6"),
            ("AA112 → AA117","Route merge via ORD hub","Saves $8,200","#8b5cf6"),
            ("AA118 → AA122","Delay absorption + pax rebooking","Saves $4,100","#f59e0b"),
        ]
        for flight, action, saving, color in actions:
            st.markdown(f"""
            <div style="padding:12px 14px;border-radius:8px;background:#f8faff;
                        border-left:4px solid {color};margin-bottom:8px;
                        display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-weight:700;font-size:13px;color:#1e293b;">{flight}</div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">{action}</div>
              </div>
              <div style="font-size:12px;color:{color};font-weight:700;margin-left:12px;white-space:nowrap;">{saving}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("#### Route Recovery Map")
        fig_m = go.Figure()
        ap = airport_df.set_index("Code")
        for r in [("JFK","LAX"),("LAX","ORD"),("ORD","DFW"),("SEA","SFO"),("SFO","DEN"),("DEN","ATL")]:
            if r[0] in ap.index and r[1] in ap.index:
                fig_m.add_trace(go.Scattergeo(
                    lon=[ap.loc[r[0],"Lon"],ap.loc[r[1],"Lon"]],
                    lat=[ap.loc[r[0],"Lat"],ap.loc[r[1],"Lat"]],
                    mode="lines",showlegend=False,
                    line=dict(width=2.5,color="rgba(37,99,235,0.45)")))
        dc = ["#ef4444" if d>30 else "#f59e0b" if d>20 else "#10b981"
              for d in airport_df.AvgDelay]
        fig_m.add_trace(go.Scattergeo(
            lon=airport_df.Lon, lat=airport_df.Lat, text=airport_df.Code,
            mode="markers+text",
            marker=dict(size=16,color=dc,line=dict(width=2,color="#fff")),
            textposition="top center", textfont=dict(size=10,color="#1e293b"),
            showlegend=False))
        fig_m.update_layout(
            geo=dict(scope="usa",showland=True,landcolor="#f8faff",
                     showcoastlines=True,coastlinecolor="#e2e8f0",bgcolor="#fff"),
            margin=dict(l=0,r=0,t=0,b=0),height=260,paper_bgcolor="#fff")
        st.plotly_chart(fig_m, use_container_width=True, config={"displayModeBar":False})
        st.caption("🔴 High delay  🟡 Medium  🟢 Low average delay")

# ─────────────────────────────────────────────
# TAB 5 — ANALYTICS & KPI
# ─────────────────────────────────────────────
with tab5:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Cost Waterfall")
        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            x=["Baseline","Op. Cost\nSavings","Delay\nSavings","Canc.\nSavings","Swap\nCosts","Optimized"],
            y=[1440000,-82000,-241000,-36000,12000,1238540],
            measure=["absolute","relative","relative","relative","relative","total"],
            connector=dict(line=dict(color="#e2e8f0")),
            increasing=dict(marker_color="#ef4444"),
            decreasing=dict(marker_color="#10b981"),
            totals=dict(marker_color="#2563eb"),
            text=["$1,440K","−$82K","−$241K","−$36K","+$12K","$1,239K"],
            textposition="outside"))
        fig_wf.update_layout(height=280,margin=dict(l=0,r=0,t=10,b=0),
            plot_bgcolor="#fff",paper_bgcolor="#fff",
            yaxis=dict(gridcolor="#f1f5f9",tickformat="$,.0f"),showlegend=False)
        st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar":False})

        st.markdown("#### Delay by Airport")
        fig_d = px.bar(airport_df.sort_values("AvgDelay",ascending=True),
            x="AvgDelay", y="Code", orientation="h",
            color="AvgDelay", color_continuous_scale=["#10b981","#f59e0b","#ef4444"],
            text="AvgDelay")
        fig_d.update_traces(texttemplate="%{text} min", textposition="outside")
        fig_d.update_layout(height=260,margin=dict(l=0,r=0,t=10,b=0),
            plot_bgcolor="#fff",paper_bgcolor="#fff",coloraxis_showscale=False)
        st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar":False})

    with c2:
        st.markdown("#### Aircraft Utilization")
        uc = ["#10b981" if u>80 else "#f59e0b" if u>60 else "#ef4444" for u in aircraft_df["Util%"]]
        fig_u = go.Figure(go.Bar(x=aircraft_df.Aircraft, y=aircraft_df["Util%"],
            marker_color=uc, text=aircraft_df["Util%"].astype(str)+"%", textposition="outside"))
        fig_u.add_hline(y=80,line_dash="dash",line_color="#64748b",annotation_text="80% target")
        fig_u.update_layout(height=240,margin=dict(l=0,r=0,t=10,b=0),
            plot_bgcolor="#fff",paper_bgcolor="#fff",
            yaxis=dict(range=[0,115],gridcolor="#f1f5f9"),showlegend=False)
        st.plotly_chart(fig_u, use_container_width=True, config={"displayModeBar":False})

        st.markdown("#### Baseline vs Optimized")
        cmp = pd.DataFrame([
            ("Total Cost","$1.44M","$1.24M","−14.0%"),
            ("Delay Minutes","3,460","2,840","−17.9%"),
            ("Cancellations","8","3","−62.5%"),
            ("Aircraft Util.","81.2%","91.4%","+12.6%"),
            ("Recovered Flights","22","47","+113.6%"),
            ("Pax Impacted","7,124","6,204","−12.9%"),
        ], columns=["Metric","Baseline","Optimized","Δ"])
        st.dataframe(cmp.style.map(
            lambda v: "color:#059669;font-weight:700;" if ("+" in str(v) or "−" in str(v)) and "%" in str(v) else "",
            subset=["Δ"]), use_container_width=True, hide_index=True, height=230)

        st.markdown("#### Cost Breakdown")
        fig_p = go.Figure(go.Pie(
            labels=["Operating","Delay","Cancellation","Swap"],
            values=[820000,312000,82000,24540], hole=0.55,
            marker_colors=["#2563eb","#f59e0b","#ef4444","#8b5cf6"]))
        fig_p.update_layout(height=210,margin=dict(l=0,r=0,t=10,b=0),paper_bgcolor="#fff",
            legend=dict(orientation="h",yanchor="bottom",y=-0.3,font=dict(size=11)))
        st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar":False})

# ─────────────────────────────────────────────
# TAB 6 — AI COPILOT
# ─────────────────────────────────────────────
SYSTEM = """You are an AI Copilot embedded in an Airline Disruption Recovery dashboard.
Current results: 284 flights scheduled, 47 recovered, 18 delayed, 3 cancelled.
Aircraft utilization 91.4% (up from 81.2%). Total cost $1.24M (saved $201K vs baseline).
Delay minutes 2,840 (down from 3,460). Solver: HiGHS, 4.21s, MIP gap 0.0001%.
JFK: 42 min avg delay. ORD: 35 min. ATL: 28 min.
AA103 delayed 45 min (maintenance conflict A321-07 at ORD).
AA105 cancelled (A320-05 maintenance overlap), pax rerouted via AA113.
Answer like a senior airline ops analyst. Be concise and specific."""

with tab6:
    c1, c2 = st.columns([1.6, 0.7], gap="large")

    with c1:
        # Chat header
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);padding:14px 18px;
                    border-radius:12px 12px 0 0;display:flex;align-items:center;gap:10px;">
          <span style="font-size:22px;">🤖</span>
          <div>
            <div style="color:#fff;font-weight:700;font-size:14px;">AI Operations Copilot</div>
            <div style="color:rgba(255,255,255,0.7);font-size:11px;">Powered by Claude · Context-aware assistant</div>
          </div>
          <div style="margin-left:auto;display:flex;align-items:center;gap:6px;">
            <div style="width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 6px #10b981;"></div>
            <span style="color:#10b981;font-size:11px;font-weight:600;">Live</span>
          </div>
        </div>""", unsafe_allow_html=True)

        # Chat messages box
        msgs_html = ""
        if not st.session_state.chat_history:
            msgs_html = """
            <div style="display:flex;margin-bottom:12px;">
              <div style="background:#f1f5f9;border:1px solid #e2e8f0;padding:10px 14px;
                          border-radius:12px 12px 12px 4px;font-size:13px;color:#1e293b;
                          max-width:80%;line-height:1.5;">
                Hello! I'm your AI Copilot. Ask me anything about the optimization results,
                flight recovery decisions, or run scenario analyses.
              </div>
            </div>"""
        else:
            for m in st.session_state.chat_history:
                if m["role"] == "user":
                    msgs_html += f"""
                    <div style="display:flex;justify-content:flex-end;margin-bottom:10px;">
                      <div style="background:linear-gradient(135deg,#2563eb,#3b82f6);color:#fff;
                                  padding:10px 14px;border-radius:12px 12px 4px 12px;
                                  font-size:13px;max-width:80%;line-height:1.5;">{m["content"]}</div>
                    </div>"""
                else:
                    msgs_html += f"""
                    <div style="display:flex;margin-bottom:10px;">
                      <div style="background:#f1f5f9;border:1px solid #e2e8f0;padding:10px 14px;
                                  border-radius:12px 12px 12px 4px;font-size:13px;color:#1e293b;
                                  max-width:80%;line-height:1.5;">{m["content"]}</div>
                    </div>"""

        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;
                    border-radius:0 0 0 0;padding:16px;min-height:300px;max-height:380px;overflow-y:auto;">
          {msgs_html}
        </div>""", unsafe_allow_html=True)

        # Input row
        ic, bc = st.columns([5,1])
        with ic:
            user_txt = st.text_input("msg", placeholder="Ask about the optimization...",
                label_visibility="collapsed", key=f"ci_{st.session_state.chat_key}")
        with bc:
            send = st.button("Send ↗", use_container_width=True, type="primary")

        def send_msg(text):
            if not text.strip(): return
            st.session_state.chat_history.append({"role":"user","content":text})
            try:
                import anthropic
                client = anthropic.Anthropic()
                reply = client.messages.create(
                    model="claude-sonnet-4-6", max_tokens=1000,
                    system=SYSTEM,
                    messages=[{"role":m["role"],"content":m["content"]}
                              for m in st.session_state.chat_history]
                ).content[0].text
            except Exception as e:
                reply = f"⚠️ Set ANTHROPIC_API_KEY to enable AI responses. Error: {str(e)[:100]}"
            st.session_state.chat_history.append({"role":"assistant","content":reply})
            st.session_state.chat_key += 1
            st.rerun()

        if send and user_txt:
            send_msg(user_txt)

    with c2:
        st.markdown("#### Suggested Prompts")
        for s in ["Which airport has the highest delays?",
                  "Why was Flight AA103 delayed?",
                  "Why was AA105 cancelled?",
                  "Summarize the recovery plan",
                  "What are the top cost drivers?"]:
            if st.button(s, key=f"s_{s}", use_container_width=True):
                send_msg(s)

        st.markdown("#### Quick Scenarios")
        for s in ["🌩️ Severe weather at JFK",
                  "🔧 Ground A321-07 for emergency MX",
                  "📈 Load factor +20%",
                  "🔄 Re-run with Gurobi"]:
            if st.button(s, key=f"sc_{s}", use_container_width=True):
                send_msg(s)

        st.markdown("#### Session")
        st.markdown(f"""
        <div style="background:#f8faff;border-radius:10px;padding:14px;border:1px solid #e2e8f0;">
          <div style="display:flex;justify-content:space-between;padding:5px 0;
                      border-bottom:1px solid #f1f5f9;font-size:12px;">
            <span style="color:#64748b;">Messages</span>
            <span style="font-weight:700;color:#2563eb;">{len(st.session_state.chat_history)}</span>
          </div>
          <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:12px;">
            <span style="color:#64748b;">Model</span>
            <span style="font-weight:600;">Claude Sonnet 4.6</span>
          </div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()