"""
Airline Planning & Optimization Dashboard
==========================================
A Streamlit dashboard for an airline fleet-assignment / tail-rotation
optimization problem.

Tabs:
  1. Overview              - executive KPIs
  2. Flight Schedule       - searchable / filterable assignment table
  3. Aircraft Rotations    - interactive Gantt chart per aircraft
  4. Network Analysis      - airport / route charts + network graph
  5. Optimization Results  - solver diagnostics + constraint validation
  6. Chat Assistant         - Groq-powered Q&A about the problem & results

Run with:
    streamlit run app.py
"""

import os
import datetime as dt

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx

import data_loader as dl

# --------------------------------------------------------------------------- #
# Page config & light styling
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Airline Planning & Optimization Dashboard",
    page_icon="✈️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem;}
    div[data-testid="stMetric"] {
        background: rgba(135,135,135,0.06);
        border: 1px solid rgba(135,135,135,0.18);
        border-radius: 10px;
        padding: 0.6rem 0.8rem 0.4rem 0.8rem;
    }
    div[data-testid="stMetricLabel"] { font-size: 0.82rem; opacity: 0.85; }
    .status-ok   { color: #1a7f37; font-weight: 600; }
    .status-bad  { color: #c62828; font-weight: 600; }
    .status-warn { color: #b06b00; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
<style>

.kpi-card{
    border-radius:12px;
    padding:10px;
    text-align:center;
    height:85px;
    color:white;
    box-shadow:0 4px 12px rgba(0,0,0,0.25);
}

/* Sweet colors */
.blue    {background:#2563EB;}
.purple  {background:#9333EA;}
.green   {background:#10B981;}
.orange  {background:#F59E0B;}
.red     {background:#F43F5E;}
.cyan    {background:#06B6D4;}
.pink    {background:#EC4899;}
.teal    {background:#14B8A6;}
.indigo  {background:#6366F1;}
.amber   {background:#FBBF24; color:#111827;}

.kpi-title{
    font-size:11px;
    font-weight:500;
    opacity:0.85;
}

.kpi-value{
    font-size:22px;
    font-weight:700;
    margin-top:5px;
}

.kpi-sub{
    font-size:10px;
    opacity:0.9;
}

</style>
""", unsafe_allow_html=True)
# --------------------------------------------------------------------------- #
# Load data once (cached)
# --------------------------------------------------------------------------- #
data = dl.load_all()
solver = dl.load_solver_summary()
kpis = dl.compute_kpis(data, solver)
master = dl.build_master_schedule(data)
validation_df = dl.run_constraint_validation(data, master)

st.title("✈️ Airline Planning & Optimization Dashboard")
st.caption(
    "Fleet assignment & tail rotation results — data loaded from the `data/` folder. "
    "Replace the sample CSVs with your own files (same names/columns) to see your model's results."
)

tab_overview, tab_schedule, tab_rotations, tab_network, tab_opt, tab_chat = st.tabs(
    [
        "📊 Overview",
        "🗓️ Flight Schedule",
        "🛫 Aircraft Rotations",
        "🌐 Network Analysis",
        "🧮 Optimization Results",
        "💬 Chat Assistant",
    ]
)


# =========================================================================== #
# TAB 1 — OVERVIEW
# =========================================================================== #
def fmt_money(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    return f"€{value:,.0f}"


def fmt_num(value, decimals=0):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    return f"{value:,.{decimals}f}"


with tab_overview:
    st.subheader("Executive Summary")

    operated_pct = (kpis["operated_flights"] / kpis["total_flights"] * 100) if kpis["total_flights"] else 0
    util = kpis["fleet_utilization"]

    cards = [
        ("Flights", fmt_num(kpis["total_flights"]), ""),
        ("Operated", fmt_num(kpis["operated_flights"]), f"{operated_pct:.1f}%"),
        ("Aircraft Used", fmt_num(kpis["aircraft_used"]), f" out of {kpis['total_aircraft']}"),
        ("Passengers", fmt_num(kpis["passengers_served"]), f"{kpis['passenger_coverage']:.1f}%"),
        ("Utilization", f"{util:.1f}%", ""),
        ("Objective", fmt_money(kpis["objective_value"]), ""),
        ("Runtime", f"{kpis['runtime_seconds']:.1f}s", ""),
        ("Cost", fmt_money(kpis["total_operating_cost"]), ""),
    ]

    cols = st.columns(len(cards))
    colors = [
        "blue",
        "purple",
        "green",
        "indigo",
        "red",
        "cyan",
        "pink",
        "teal"
    ]

    for col, (title, value, sub), color in zip(cols, cards, colors):
        with col:
            st.markdown(
                f"""
                <div class="kpi-card {color}">
                    <div class="kpi-title">{title}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True
            ) 

              
    st.divider()

    c1, c2, c3= st.columns(3)

    with c1:
        st.markdown("##### Flight Status Breakdown")

        status_counts = pd.DataFrame({
            "Status": ["Operated", "Cancelled"],
            "Flights": [
                kpis["operated_flights"],
                kpis["cancelled_flights"]
            ]
        })

        fig = px.bar(
            status_counts,
            x="Status",
            y="Flights",
            color="Status",
            text="Flights",
            color_discrete_map={
                "Operated": "#06B6D4",   # Cyan
                "Cancelled": "#F43F5E"  # Rose Red
            }
        )

        fig.update_traces(
            textposition="outside",
            textfont_size=14,
            marker_line_width=0
        )

        fig.update_layout(
            paper_bgcolor="#0B1120",
            plot_bgcolor="#0B1120",
            font_color="white",
            showlegend=False,
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(
                title="",
                showgrid=False
            ),
            yaxis=dict(
                title="Flights",
                gridcolor="rgba(255,255,255,0.08)"
            )
        )

        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown("##### Revenue Distribution by Aircraft")

        aircraft_rev = kpis["aircraft_rev"]

        # Remove aircraft with zero revenue
        aircraft_rev = aircraft_rev[
            aircraft_rev["revenue"] > 0
        ]

        fig = px.pie(
            aircraft_rev,
            names="aircraft",
            values="revenue",
            hole=0
        )

        # fig.update_traces(
        #     textinfo="label+percent",
        #     textfont_size=12,
        #     hovertemplate=
        #     "<b>%{label}</b><br>" +
        #     "Revenue: $%{value:,.0f}<br>" +
        #     "Share: %{percent}<extra></extra>"
        # )

        fig.update_layout(
            paper_bgcolor="#0B1120",
            plot_bgcolor="#0B1120",
            font_color="white",
            height=250,
            margin=dict(l=10, r=10, t=10, b=10),
            legend_title="Aircraft",
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(color="white")
            )
        )

        st.plotly_chart(fig, width="stretch")

    with c3:
        st.markdown("##### Passenger Demand vs Served")

        pax_df = pd.DataFrame({
            "Metric": ["Total Demand", "Passengers Served"],
            "Passengers": [kpis["total_passengers"], kpis["passengers_served"]]
        })

        fig2 = px.bar(
            pax_df,
            x="Metric",
            y="Passengers",
            color="Metric",
            text="Passengers",
            color_discrete_map={
                "Total Demand": "#6366F1",       # Indigo
                "Passengers Served": "#06B6D4"  # Cyan
            }
        )

        fig2.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside"
        )

        fig2.update_layout(
            paper_bgcolor="#0B1120",
            plot_bgcolor="#0B1120",
            font_color="white",
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=300,
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)")
        )

        st.plotly_chart(fig2, width="stretch")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Aircraft Utilization")

        aircraft_df = pd.DataFrame({
            "Aircraft": ["Available Aircraft", "Aircraft Used"],
            "Count": [
                kpis["total_aircraft"],
                kpis["aircraft_used"]
            ]
        })

        fig = px.bar(
            aircraft_df,
            x="Aircraft",
            y="Count",
            color="Aircraft",
            text="Count",
            color_discrete_map={
                "Available Aircraft": "#6366F1",   # Indigo
                "Aircraft Used": "#10B981"         # Emerald
            }
        )

        fig.update_traces(
            textposition="outside",
            textfont_size=14
        )

        fig.update_layout(
            paper_bgcolor="#0B1120",
            plot_bgcolor="#0B1120",
            font_color="white",
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=350,
            xaxis=dict(showgrid=False),
            yaxis=dict(
                title="Aircraft Count",
                gridcolor="rgba(255,255,255,0.08)"
            )
        )

        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown("##### Passenger Distribution by Aircraft")

        # Keep only aircraft that carried passengers
        aircraft_pax = kpis["aircraft_pax"]

        fig = px.pie(
            aircraft_pax,
            names="aircraft",
            values="passengers",
            hole=0.35,
        )

        fig.update_traces(
            textinfo="label+value+percent",
            textfont_size=12
        )

        fig.update_layout(
            paper_bgcolor="#0B1120",
            plot_bgcolor="#0B1120",
            font_color="white",
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            legend_title="Aircraft"
        )

        st.plotly_chart(fig, width="stretch")
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.markdown("##### Flights by Destination Airport")

        dest_counts = kpis["dest_counts"]
        fig = px.bar(
            dest_counts,
            x="destination",
            y="flights",
            color="destination",
            text="flights"
        )

        fig.update_traces(textposition="outside")

        fig.update_layout(
            paper_bgcolor="#0B1120",
            plot_bgcolor="#0B1120",
            font_color="white",
            showlegend=False,
            height=400
        )

        st.plotly_chart(fig, width="stretch")

    
    with c2:
        st.markdown("##### Passenger Flow by Origin")

        origin_pax = kpis["origin_pax"]
        fig = px.pie(
            origin_pax,
            names="origin",
            values="passengers",
            hole=0.55
        )

        fig.update_layout(
            paper_bgcolor="#0B1120",
            font_color="white",
            height=400
        )

        st.plotly_chart(fig, width="stretch")



# =========================================================================== #
# TAB 2 — FLIGHT SCHEDULE
# =========================================================================== #
with tab_schedule:
    st.subheader("Flight Schedule & Assignment")

    if master.empty:
        st.warning("No flight schedule data found. Make sure `flight_rotations.csv` exists in `data/`.")
    else:
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search = st.text_input("🔍 Search (flight ID, aircraft, or airport)", "")
        with f2:
            aircraft_opts = ["All"] + sorted(master["aircraft"].dropna().astype(str).unique().tolist())
            aircraft_filter = st.selectbox("Aircraft filter", aircraft_opts)
        with f3:
            airports = sorted(set(master["origin"].dropna()) | set(master["destination"].dropna()))
            airport_filter = st.selectbox("Airport filter", ["All"] + airports)

        filtered = master.copy()
        if search:
            s = search.lower()
            mask = (
                filtered["flight"].astype(str).str.lower().str.contains(s)
                | filtered["aircraft"].astype(str).str.lower().str.contains(s)
                | filtered["origin"].astype(str).str.lower().str.contains(s)
                | filtered["destination"].astype(str).str.lower().str.contains(s)
            )
            filtered = filtered[mask]
        if aircraft_filter != "All":
            filtered = filtered[filtered["aircraft"].astype(str) == aircraft_filter]
        if airport_filter != "All":
            filtered = filtered[(filtered["origin"] == airport_filter) | (filtered["destination"] == airport_filter)]

        display_cols = ["flight", "aircraft", "origin", "destination", "start_time", "end_time", "duration", "status"]
        display_df = filtered[display_cols].rename(
            columns={
                "flight": "Flight ID",
                "aircraft": "Assigned Aircraft",
                "origin": "Origin",
                "destination": "Destination",
                "start_time": "Departure Time",
                "end_time": "Arrival Time",
                "duration": "Duration",
                "status": "Status",
            }
        ).sort_values("Departure Time")

        def highlight_cancelled(row):
            if row["Status"] == "Cancelled":
                return ["background-color: rgba(198,40,40,0.14); color:#7a1212"] * len(row)
            return [""] * len(row)

        st.dataframe(
            display_df.style.apply(highlight_cancelled, axis=1),
            width='stretch',
            height=460,
        )
        st.caption(f"Showing {len(display_df):,} of {len(master):,} scheduled flights")

        csv_bytes = display_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv_bytes, "flight_schedule.csv", "text/csv")


# =========================================================================== #
# TAB 3 — AIRCRAFT ROTATIONS
# =========================================================================== #
with tab_rotations:
    st.subheader("Aircraft Rotations — Daily Gantt Chart")

    operated = master[master["status"] == "Operated"].copy() if not master.empty else pd.DataFrame()

    if operated.empty:
        st.warning("No operated flights found to build rotations.")
    else:
        if "date" in operated.columns and operated["date"].notna().any():
            base_date = pd.to_datetime(operated["date"].dropna().min())
        else:
            base_date = pd.Timestamp("2006-01-07")

        def combine(t):
            td = dl.parse_hms(t)
            return base_date + td if td is not None else None

        operated["start_dt"] = operated["start_time"].apply(combine)
        operated["end_dt"] = operated["end_time"].apply(combine)
        operated.loc[operated["end_dt"] < operated["start_dt"], "end_dt"] += pd.Timedelta(days=1)
        operated = operated.dropna(subset=["start_dt", "end_dt"])

        fig = px.timeline(
            operated.sort_values("aircraft"),
            x_start="start_dt",
            x_end="end_dt",
            y="aircraft",
            color="aircraft",
            custom_data=["flight", "origin", "destination", "start_time", "end_time"],
        )
        fig.update_traces(
            hovertemplate=(
                "<b>Flight %{customdata[0]}</b><br>"
                "Origin: %{customdata[1]}<br>"
                "Destination: %{customdata[2]}<br>"
                "Start: %{customdata[3]}<br>"
                "End: %{customdata[4]}<extra></extra>"
            )
        )
        fig.update_yaxes(autorange="reversed", title="Aircraft")
        fig.update_xaxes(title="Time of day")
        fig.update_layout(showlegend=False, height=max(420, 30 * operated["aircraft"].nunique()))
        st.plotly_chart(fig, width='stretch')

        st.markdown("##### Per-Aircraft Utilization")

        def total_hours(durations):
            total = dt.timedelta()
            for d in durations:
                td = dl.parse_hms(d)
                if td is not None:
                    total += td
            return total.total_seconds() / 3600

        rows = []
        for aircraft, grp in operated.groupby("aircraft"):
            grp_sorted = grp.sort_values("start_dt")
            flying_hours = total_hours(grp_sorted["duration"])
            span_hours = (grp_sorted["end_dt"].max() - grp_sorted["start_dt"].min()).total_seconds() / 3600
            idle_hours = max(span_hours - flying_hours, 0)
            rows.append(
                {
                    "Aircraft": aircraft,
                    "Number of Flights": grp_sorted["flight"].nunique(),
                    "Utilization Hours": round(flying_hours, 2),
                    "Operating Span (hrs)": round(span_hours, 2),
                    "Idle Time (hrs)": round(idle_hours, 2),
                    "Passengers Carried": int(pd.to_numeric(grp_sorted["passengers"], errors="coerce").sum()),
                    "Revenue": round(float(pd.to_numeric(grp_sorted["revenue"], errors="coerce").sum()), 2),
                }
            )
        util_df = pd.DataFrame(rows).sort_values("Utilization Hours", ascending=False)
        st.dataframe(util_df, width='stretch', height=320)


# =========================================================================== #
# TAB 4 — NETWORK ANALYSIS
# =========================================================================== #
with tab_network:
    st.subheader("Network Analysis")

    operated = master[master["status"] == "Operated"].copy() if not master.empty else pd.DataFrame()

    if operated.empty:
        st.warning("No operated flights found to analyze the network.")
    else:
        st.markdown("##### Airport Traffic")
        n1, n2, n3 = st.columns(3)
        with n1:
            dep = operated.groupby("origin")["flight"].nunique().reset_index(name="Departures").sort_values(
                "Departures", ascending=False
            )
            fig = px.bar(dep.head(15), x="origin", y="Departures", color="Departures",
                         color_continuous_scale="Blues", title="Departures by Airport")
            fig.update_layout(coloraxis_showscale=False, height=340, xaxis_title="Airport")
            st.plotly_chart(fig, width='stretch')
        with n2:
            arr = operated.groupby("destination")["flight"].nunique().reset_index(name="Arrivals").sort_values(
                "Arrivals", ascending=False
            )
            fig = px.bar(arr.head(15), x="destination", y="Arrivals", color="Arrivals",
                         color_continuous_scale="Greens", title="Arrivals by Airport")
            fig.update_layout(coloraxis_showscale=False, height=340, xaxis_title="Airport")
            st.plotly_chart(fig, width='stretch')
        with n3:
            pax_o = operated.groupby("origin")["passengers"].sum()
            pax_d = operated.groupby("destination")["passengers"].sum()
            pax_vol = (pax_o.add(pax_d, fill_value=0)).reset_index()
            pax_vol.columns = ["airport", "passengers"]
            pax_vol = pax_vol.sort_values("passengers", ascending=False)
            fig = px.bar(pax_vol.head(15), x="airport", y="passengers", color="passengers",
                         color_continuous_scale="Oranges", title="Passenger Volume by Airport")
            fig.update_layout(coloraxis_showscale=False, height=340, xaxis_title="Airport")
            st.plotly_chart(fig, width='stretch')

        st.divider()
        st.markdown("##### Route Analysis")
        operated["route"] = operated["origin"].astype(str) + " → " + operated["destination"].astype(str)
        route_stats = operated.groupby("route").agg(
            Frequency=("flight", "nunique"),
            Passengers=("passengers", "sum"),
            Revenue=("revenue", "sum"),
        ).reset_index()

        itin = data.get("flight_itineraries")
        if itin is not None and not itin.empty and "flight" in itin.columns and "cost" in itin.columns:
            flight_route = operated[["flight", "route"]].drop_duplicates()
            itin_route = itin.merge(flight_route, on="flight", how="inner")
            route_cost = itin_route.groupby("route")["cost"].mean().reset_index(name="Avg Fare Cost")
            route_stats = route_stats.merge(route_cost, on="route", how="left")
        else:
            route_stats["Avg Fare Cost"] = None

        route_stats = route_stats.sort_values("Frequency", ascending=False)

        r1, r2 = st.columns(2)
        with r1:
            fig = px.bar(route_stats.head(10), x="route", y="Frequency", color="Frequency",
                         color_continuous_scale="Purples", title="Top Routes (by Frequency)")
            fig.update_layout(coloraxis_showscale=False, height=340, xaxis_title="Route")
            st.plotly_chart(fig, width='stretch')
        with r2:
            if route_stats["Avg Fare Cost"].notna().any():
                fig = px.bar(route_stats.head(10), x="route", y="Avg Fare Cost", color="Avg Fare Cost",
                             color_continuous_scale="Reds", title="Route Costs (Avg Fare)")
                fig.update_layout(coloraxis_showscale=False, height=340, xaxis_title="Route")
                st.plotly_chart(fig, width='stretch')
            else:
                fig = px.bar(route_stats.head(10), x="route", y="Revenue", color="Revenue",
                             color_continuous_scale="Reds", title="Route Revenue")
                fig.update_layout(coloraxis_showscale=False, height=340, xaxis_title="Route")
                st.plotly_chart(fig, width='stretch')

        st.dataframe(route_stats.rename(columns={"route": "Route"}), width='stretch', height=280)

        st.divider()
        st.markdown("##### Network Map")

        G = nx.DiGraph()
        for _, row in operated.iterrows():
            G.add_edge(row["origin"], row["destination"])

        if G.number_of_nodes() == 0:
            st.info("Not enough data to build a network map.")
        else:
            pos = nx.spring_layout(G, seed=42, k=1.0)
            in_deg = dict(G.in_degree())
            out_deg = dict(G.out_degree())
            centrality = nx.degree_centrality(G)

            edge_x, edge_y = [], []
            for u, v in G.edges():
                edge_x += [pos[u][0], pos[v][0], None]
                edge_y += [pos[u][1], pos[v][1], None]
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y, mode="lines",
                line=dict(width=1, color="rgba(120,120,120,0.45)"),
                hoverinfo="none",
            )

            node_x, node_y, node_text, node_size, node_color = [], [], [], [], []
            for node in G.nodes():
                node_x.append(pos[node][0])
                node_y.append(pos[node][1])
                deg_in = in_deg.get(node, 0)
                deg_out = out_deg.get(node, 0)
                cent = centrality.get(node, 0)
                node_text.append(
                    f"<b>{node}</b><br>Incoming flights: {deg_in}<br>Outgoing flights: {deg_out}"
                    f"<br>Degree centrality: {cent:.3f}"
                )
                node_size.append(14 + (deg_in + deg_out) * 4)
                node_color.append(deg_in + deg_out)

            node_trace = go.Scatter(
                x=node_x, y=node_y, mode="markers+text",
                text=list(G.nodes()), textposition="top center",
                hovertext=node_text, hoverinfo="text",
                marker=dict(size=node_size, color=node_color, colorscale="Viridis",
                            showscale=True, colorbar=dict(title="Traffic"), line_width=1),
            )

            fig = go.Figure(data=[edge_trace, node_trace])
            fig.update_layout(
                showlegend=False, height=560,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, width='stretch')

            airport_stats = pd.DataFrame(
                {
                    "Airport": list(G.nodes()),
                    "Incoming Flights": [in_deg.get(n, 0) for n in G.nodes()],
                    "Outgoing Flights": [out_deg.get(n, 0) for n in G.nodes()],
                    "Degree Centrality": [round(centrality.get(n, 0), 3) for n in G.nodes()],
                }
            ).sort_values("Degree Centrality", ascending=False)
            st.dataframe(airport_stats, width='stretch', height=260)


# =========================================================================== #
# TAB 5 — OPTIMIZATION RESULTS
# =========================================================================== #
with tab_opt:
    st.subheader("Optimization Diagnostics")

    st.markdown("##### Solver Information")
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    with s1:
        st.metric("Solver Status", solver.get("solver_status") or "N/A")
    with s2:
        st.metric("Objective Value", fmt_money(solver.get("objective_value")))
    with s3:
        rt = solver.get("runtime_seconds")
        st.metric("Runtime", f"{rt:.1f}s" if rt is not None and not pd.isna(rt) else "N/A")
    with s4:
        gap = solver.get("mip_gap_percent")
        st.metric("MIP Gap", f"{gap:.2f}%" if gap is not None and not pd.isna(gap) else "N/A")
    with s5:
        st.metric("Variables", fmt_num(solver.get("num_variables")))
    with s6:
        st.metric("Constraints", fmt_num(solver.get("num_constraints")))

    if solver.get("objective_value") is None:
        st.info(
            "No `solver_summary.csv` found in `data/`. Add one with columns "
            "`solver_status, objective_value, runtime_seconds, mip_gap_percent, "
            "num_variables, num_constraints, total_operating_cost` to populate this section "
            "with your model's real diagnostics."
        )

    st.divider()
    st.markdown("##### Optimization Summary")
    o1, o2, o3, o4 = st.columns(4)
    with o1:
        st.metric("Flights Scheduled", fmt_num(kpis["operated_flights"]))
    with o2:
        st.metric("Flights Cancelled", fmt_num(kpis["cancelled_flights"]))
    with o3:
        st.metric("Aircraft Utilized", fmt_num(kpis["aircraft_used"]))
    with o4:
        st.metric("Passenger Coverage %", f"{kpis['passenger_coverage']:.1f}%")

    st.divider()
    st.markdown("##### Constraint Validation")

    def status_badge(s):
        if s == "Satisfied":
            return "✅ Satisfied"
        if s == "Violated":
            return "❌ Violated"
        return "⚠️ " + s

    show_df = validation_df.copy()
    show_df["Status"] = show_df["Status"].apply(status_badge)
    st.dataframe(show_df, width='stretch', hide_index=True)

    st.divider()

    with st.expander("📜 Optimization Logs"):

        log_file = "data/logs/solver_log.log"

        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log_text = f.read()

            st.code(log_text, language="text")

        else:
            st.info(f"File not found: {log_file}")


# =========================================================================== #
# TAB 6 — CHAT ASSISTANT (Groq)
# =========================================================================== #
with tab_chat:
    st.subheader("💬 Chat Assistant")
    st.caption(
        "Ask questions about the flight schedule, fleet assignment, aircraft rotations, or optimization results."
    )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    MODEL_NAME = "llama-3.3-70b-versatile"

    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    except Exception:
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    # ------------------------------------------------------------------
    # Clear chat
    # ------------------------------------------------------------------
    if st.button("🗑️ Clear Chat History"):
        st.session_state["chat_messages"] = []
        st.rerun()


    def build_context_summary() -> str:
        top_routes_txt = "N/A"
        if not master.empty:
            op = master[master["status"] == "Operated"].copy()
            if not op.empty:
                op["route"] = op["origin"].astype(str) + "-" + op["destination"].astype(str)
                top_routes = op["route"].value_counts().head(5)
                top_routes_txt = ", ".join(f"{r} ({c} flights)" for r, c in top_routes.items())

        validation_txt = "; ".join(
            f"{row.Constraint}: {row.Status}" for row in validation_df.itertuples()
        )

        operated_pct_txt = (
            f"{kpis['operated_flights'] / kpis['total_flights'] * 100:.1f}%"
            if kpis["total_flights"] > 0
            else "N/A"
        )

        return f"""
You are an assistant embedded in an Airline Fleet Assignment & Aircraft Rotation
optimization dashboard. The underlying problem: given a flight timetable
(candidate flights with origin/destination/times), an available fleet of
aircraft (with start-of-day and end-of-day base airports), and passenger
demand/fares per flight, the optimizer decides which flights to operate,
which aircraft operates each flight, and the rotation (sequence of flights)
each aircraft flies, while respecting aircraft continuity (each aircraft's
rotation is a single path from its source to its sink in a time-space
network), fleet availability, airport balance (start/end at the right base),
and time feasibility (no overlapping flights), in order to maximize revenue
(or minimize cost) subject to those constraints.

Current solved instance summary:
- Total flights in candidate schedule: {kpis['total_flights']}
- Operated flights: {kpis['operated_flights']} ({operated_pct_txt})
- Cancelled flights: {kpis['cancelled_flights']}
- Total aircraft in fleet: {kpis['total_aircraft']}
- Aircraft actually used: {kpis['aircraft_used']}
- Fleet utilization: {kpis['fleet_utilization']:.1f}%
- Total passenger demand: {kpis['total_passengers']:.0f}
- Passengers served: {kpis['passengers_served']:.0f} ({kpis['passenger_coverage']:.1f}% coverage)
- Total revenue from operated flights: {kpis['total_revenue']:.0f}
- Solver status: {solver.get('solver_status')}
- Objective value: {solver.get('objective_value')}
- Runtime: {solver.get('runtime_seconds')} seconds
- MIP gap: {solver.get('mip_gap_percent')}%
- Top routes by frequency: {top_routes_txt}
- Constraint validation results: {validation_txt}

Answer the user's questions about this problem and these results clearly and
concisely. If asked something the data above cannot answer, say so honestly
rather than inventing numbers. You may explain general airline scheduling /
fleet assignment optimization concepts (time-space networks, MIP formulations,
revenue management) when relevant.
""".strip()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # ------------------------------------------------------------------
    # Display History
    # ------------------------------------------------------------------
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ------------------------------------------------------------------
    # User Input
    # ------------------------------------------------------------------
    prompt = st.chat_input(
        "Ask about flights, aircraft, passengers, routes, revenue, or optimization..."
    )

    if prompt:

        st.session_state.chat_messages.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        try:

            from groq import Groq

            client = Groq(api_key=GROQ_API_KEY)

            messages = [
                {
                    "role": "system",
                    "content": build_context_summary(),
                }
            ]

            messages.extend(
                {
                    "role": m["role"],
                    "content": m["content"],
                }
                for m in st.session_state.chat_messages
            )

            with st.chat_message("assistant"):

                stream = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=0.3,
                    stream=True,
                )

                def response_stream():
                    for chunk in stream:
                        delta = chunk.choices[0].delta.content
                        if delta:
                            yield delta

                answer = st.write_stream(response_stream())

            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

        except Exception as e:
            st.error(f"Groq Error: {str(e)}")
