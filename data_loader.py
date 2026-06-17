"""
data_loader.py
----------------
Centralised loading, cleaning and computation logic for the Airline
Planning & Optimization Dashboard.

All raw input/output tables (produced by the optimization model) are
expected to live as CSV files inside the ``data/`` folder, next to this
file. The expected filenames are listed in FILES below -- these match the
sheet names seen in the original Excel workbook.

Every loader function degrades gracefully (returns ``None`` / empty
DataFrame) when a file is missing, so the dashboard never crashes -- it
just shows "no data available" in the relevant widget.
"""

from __future__ import annotations

import os
import datetime as dt
from typing import Optional

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

FILES = {
    "flight_rotations": "inputs/flight_rotations.csv",        # input: full candidate flight timetable
    "starting_positions": "inputs/starting_positions.csv",     # input: fleet start-of-day airport
    "ending_positions": "inputs/ending_positions.csv",         # input: fleet end-of-day airport
    "flight_itineraries": "inputs/flight_iterinaries.csv",     # input: passenger demand / fares per flight
    "aircraft_summary": "outputs/aircraft_summary.csv",         # output: per-aircraft utilization summary
    "flight_assignments": "outputs/flight_assignments.csv",     # output: final flight -> aircraft assignment
    "route_assignments": "outputs/route_assignments.csv",       # output: time-space network flow per aircraft
}

SOLVER_SUMMARY_FILE = "outputs/solver_summary.csv"
SOLVER_LOG_FILE = "logs/solver_log.txt"


# --------------------------------------------------------------------------- #
# Low level readers
# --------------------------------------------------------------------------- #
def _read_csv(filename: str) -> Optional[pd.DataFrame]:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    # Drop the leftover pandas index column ("Unnamed: 0") that shows up
    # when the source workbook was exported with index=True.
    if len(df.columns) and str(df.columns[0]).lower().startswith("unnamed"):
        df = df.drop(columns=[df.columns[0]])
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _to_timedelta(series: pd.Series) -> pd.Series:
    """Parse HH:MM:SS strings into a timedelta, tolerant of bad/missing values."""
    return pd.to_timedelta(series.astype(str), errors="coerce")


@st.cache_data(show_spinner=False)
def load_all() -> dict:
    """Load every raw table once, cached for the session."""
    data = {key: _read_csv(fname) for key, fname in FILES.items()}

    rot = data.get("flight_rotations")
    if rot is not None and not rot.empty:
        for col in ("start_time", "end_time", "duration"):
            if col in rot.columns:
                rot[col + "_td"] = _to_timedelta(rot[col])
        if "date" in rot.columns:
            rot["date"] = pd.to_datetime(rot["date"], format="%d-%m-%Y", errors="coerce")
        data["flight_rotations"] = rot

    return data


@st.cache_data(show_spinner=False)
def load_solver_summary() -> dict:
    """Load optional solver diagnostics. Returns sensible defaults if absent."""
    defaults = {
        "solver_status": "Not available",
        "objective_value": None,
        "runtime_seconds": None,
        "mip_gap_percent": None,
        "num_variables": None,
        "num_constraints": None,
        "total_operating_cost": None,
    }
    path = os.path.join(DATA_DIR, SOLVER_SUMMARY_FILE)
    if not os.path.exists(path):
        return defaults
    try:
        df = pd.read_csv(path)
        if df.empty:
            return defaults
        row = df.iloc[0].to_dict()
        defaults.update({k: v for k, v in row.items() if k in defaults})
        return defaults
    except Exception:
        return defaults


@st.cache_data(show_spinner=False)
def load_solver_log() -> Optional[str]:
    path = os.path.join(DATA_DIR, SOLVER_LOG_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Derived / merged tables
# --------------------------------------------------------------------------- #
def build_master_schedule(data: dict) -> pd.DataFrame:
    """
    Merge the candidate flight timetable (flight_rotations) with the final
    optimizer assignment (flight_assignments) to get one row per planned
    flight, flagged Operated / Cancelled, with the assigned aircraft,
    times, passengers and revenue all in one place.
    """
    rot = data.get("flight_rotations")
    assign = data.get("flight_assignments")

    if rot is None or rot.empty:
        return pd.DataFrame()

    base = rot.copy()
    base = base.rename(columns={"aircraft": "scheduled_aircraft", "ori": "origin", "des": "destination"})

    if assign is not None and not assign.empty:
        a = assign.copy()
        keep_cols = [c for c in ["flight", "aircraft", "passengers", "revenue"] if c in a.columns]
        a = a[keep_cols].rename(columns={"aircraft": "assigned_aircraft"})
        # a flight can only appear once in the final assignment in this model
        a = a.drop_duplicates(subset=["flight"])
        merged = base.merge(a, on="flight", how="left")
    else:
        merged = base.copy()
        merged["assigned_aircraft"] = None
        merged["passengers"] = None
        merged["revenue"] = None

    merged["status"] = merged["assigned_aircraft"].apply(lambda x: "Operated" if pd.notna(x) else "Cancelled")
    merged["aircraft"] = merged["assigned_aircraft"].fillna(merged["scheduled_aircraft"])
    merged["passengers"] = merged["passengers"].fillna(0)
    merged["revenue"] = merged["revenue"].fillna(0)

    for col in ("start_time", "end_time", "duration"):
        if col not in merged.columns:
            merged[col] = None

    return merged


# --------------------------------------------------------------------------- #
# KPIs
# --------------------------------------------------------------------------- #
def compute_kpis(data: dict, solver: dict) -> dict:
    rot = data.get("flight_rotations")
    assign = data.get("flight_assignments")
    starting = data.get("starting_positions")
    summary = data.get("aircraft_summary")
    itin = data.get("flight_itineraries")

    total_flights = int(rot["flight"].nunique()) if rot is not None and not rot.empty else 0
    operated_flights = int(assign["flight"].nunique()) if assign is not None and not assign.empty else 0
    cancelled_flights = max(total_flights - operated_flights, 0)

    total_aircraft = int(starting["aircraft"].nunique()) if starting is not None and not starting.empty else 0

    aircraft_used = 0
    if summary is not None and not summary.empty:
        flight_col = next((c for c in summary.columns if "assign" in c.lower() or "flight" in c.lower()), None)
        if flight_col is not None:
            aircraft_used = int((pd.to_numeric(summary[flight_col], errors="coerce").fillna(0) > 0).sum())
    elif assign is not None and not assign.empty and "aircraft" in assign.columns:
        aircraft_used = int(assign["aircraft"].nunique())

    fleet_utilization = (aircraft_used / total_aircraft * 100) if total_aircraft else 0.0

    total_passengers = float(pd.to_numeric(itin["n_pass"], errors="coerce").sum()) if itin is not None and not itin.empty and "n_pass" in itin.columns else 0.0
    passengers_served = float(pd.to_numeric(assign["passengers"], errors="coerce").sum()) if assign is not None and not assign.empty and "passengers" in assign.columns else 0.0
    passenger_coverage = (passengers_served / total_passengers * 100) if total_passengers else 0.0

    total_revenue = float(pd.to_numeric(assign["revenue"], errors="coerce").sum()) if assign is not None and not assign.empty and "revenue" in assign.columns else 0.0

    aircraft_pax = summary[
        summary["passengers"] > 0
    ][["aircraft", "passengers"]]
    
    aircraft_rev = (
        summary[summary["revenue"] > 0]
        .sort_values("revenue", ascending=False)
    )
    dest_counts = (
        assign
        .groupby("destination")
        .size()
        .reset_index(name="flights")
        .sort_values("flights", ascending=False)
    )

    origin_pax = (
        assign
        .groupby("origin")["passengers"]
        .sum()
        .reset_index()
        .sort_values("passengers", ascending=False)
    )


    return {
        "total_flights": total_flights,
        "operated_flights": operated_flights,
        "cancelled_flights": cancelled_flights,
        "total_aircraft": total_aircraft,
        "aircraft_used": aircraft_used,
        "fleet_utilization": fleet_utilization,
        "total_passengers": total_passengers,
        "passengers_served": passengers_served,
        "passenger_coverage": passenger_coverage,
        "total_revenue": total_revenue,
        "objective_value": solver.get("objective_value"),
        "runtime_seconds": solver.get("runtime_seconds"),
        "mip_gap_percent": solver.get("mip_gap_percent"),
        "total_operating_cost": solver.get("total_operating_cost"),
        "solver_status": solver.get("solver_status"),
        "aircraft_pax": aircraft_pax,
        "aircraft_rev": aircraft_rev,
        "origin_pax": origin_pax,
        "dest_counts": dest_counts,
    }


# --------------------------------------------------------------------------- #
# Constraint validation (computed from the actual data, not hard-coded)
# --------------------------------------------------------------------------- #
def parse_hms(value) -> Optional[dt.timedelta]:
    """Parse an 'HH:MM:SS' string into a timedelta. Returns None on bad input."""
    if pd.isna(value):
        return None
    try:
        h, m, s = str(value).split(":")
        return dt.timedelta(hours=int(h), minutes=int(m), seconds=int(s))
    except Exception:
        return None


# kept for internal backward-compatible calls within this module
_parse_hms = parse_hms


def validate_aircraft_continuity(route_assignments: Optional[pd.DataFrame]) -> tuple[str, str]:
    """For every aircraft, the from/to node chain must form a single path
    from its source node to its sink node with no broken links."""
    if route_assignments is None or route_assignments.empty:
        return "No data", "route_assignments.csv not found"

    broken = []
    for aircraft, grp in route_assignments.groupby("aircraft"):
        edges = list(zip(grp["from_node"].astype(str), grp["to_node"].astype(str)))
        starts = {f for f, t in edges}
        ends = {t for f, t in edges}
        sources = [n for n in starts if n.startswith("source")]
        sinks = [n for n in ends if n.startswith("sink")]
        if len(sources) != 1 or len(sinks) != 1:
            broken.append(aircraft)
            continue
        # walk the chain
        nxt = {f: t for f, t in edges}
        node = sources[0]
        visited = 0
        while node in nxt and visited <= len(edges) + 1:
            node = nxt[node]
            visited += 1
        if not node.startswith("sink"):
            broken.append(aircraft)

    if broken:
        return "Violated", f"{len(broken)} aircraft with a broken rotation chain: {', '.join(map(str, broken[:5]))}"
    return "Satisfied", f"All {route_assignments['aircraft'].nunique()} aircraft rotations form a single source→sink path"


def validate_fleet_availability(assign: Optional[pd.DataFrame], summary: Optional[pd.DataFrame]) -> tuple[str, str]:
    if assign is None or assign.empty:
        return "No data", "flight_assignments.csv not found"
    dup = assign["flight"].duplicated().sum() if "flight" in assign.columns else 0
    if dup:
        return "Violated", f"{dup} flight(s) assigned to more than one aircraft"
    return "Satisfied", "Every operated flight is assigned to exactly one aircraft"


def validate_time_feasibility(master: pd.DataFrame) -> tuple[str, str]:
    """For each aircraft, consecutive operated flights must not overlap in time."""
    op = master[master["status"] == "Operated"].copy()
    if op.empty:
        return "No data", "No operated flights to check"

    op["start_td"] = op["start_time"].apply(_parse_hms)
    op["end_td"] = op["end_time"].apply(_parse_hms)
    op = op.dropna(subset=["start_td", "end_td"])

    overlaps = 0
    for aircraft, grp in op.groupby("aircraft"):
        grp = grp.sort_values("start_td")
        prev_end = None
        for _, row in grp.iterrows():
            if prev_end is not None and row["start_td"] < prev_end:
                overlaps += 1
            prev_end = row["end_td"]

    if overlaps:
        return "Violated", f"{overlaps} overlapping flight pair(s) detected across the fleet"
    return "Satisfied", "No aircraft has two overlapping flights in its schedule"


def validate_airport_balance(starting: Optional[pd.DataFrame], ending: Optional[pd.DataFrame],
                               master: pd.DataFrame) -> tuple[str, str]:
    """Check that, for every aircraft with at least one operated flight, the
    first departure airport matches its starting position and the last
    arrival airport matches its ending position."""
    if starting is None or ending is None or starting.empty or ending.empty:
        return "No data", "starting_positions.csv / ending_positions.csv not found"

    op = master[master["status"] == "Operated"].copy()
    if op.empty:
        return "No data", "No operated flights to check"

    op["start_td"] = op["start_time"].apply(_parse_hms)
    start_map = starting.set_index("aircraft")["airport"].to_dict()
    end_map = ending.set_index("aircraft")["airport"].to_dict()

    mismatches = 0
    checked = 0
    for aircraft, grp in op.groupby("aircraft"):
        grp = grp.sort_values("start_td")
        first_origin = grp.iloc[0]["origin"]
        last_dest = grp.iloc[-1]["destination"]
        expected_start = start_map.get(aircraft)
        expected_end = end_map.get(aircraft)
        checked += 1
        if expected_start is not None and first_origin != expected_start:
            mismatches += 1
        elif expected_end is not None and last_dest != expected_end:
            mismatches += 1

    if checked == 0:
        return "No data", "No matching aircraft between assignments and fleet position files"
    if mismatches:
        return "Violated", f"{mismatches} of {checked} aircraft don't connect to their planned start/end airport"
    return "Satisfied", f"All {checked} active aircraft start and end at their planned airports"


def run_constraint_validation(data: dict, master: pd.DataFrame) -> pd.DataFrame:
    checks = []

    status, detail = validate_aircraft_continuity(data.get("route_assignments"))
    checks.append(("Aircraft Continuity", status, detail))

    status, detail = validate_fleet_availability(data.get("flight_assignments"), data.get("aircraft_summary"))
    checks.append(("Fleet Availability", status, detail))

    status, detail = validate_airport_balance(data.get("starting_positions"), data.get("ending_positions"), master)
    checks.append(("Airport Balance", status, detail))

    status, detail = validate_time_feasibility(master)
    checks.append(("Time Feasibility", status, detail))

    return pd.DataFrame(checks, columns=["Constraint", "Status", "Detail"])
