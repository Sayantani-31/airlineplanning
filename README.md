# ✈️ Airline Fleet Assignment & Rotation Dashboard

A comprehensive Streamlit dashboard for visualizing and optimizing airline fleet assignment and aircraft rotation management. This application integrates powerful optimization algorithms with an intuitive UI, featuring interactive charts, real-time analytics, and an AI-powered chat assistant for intelligent insights.

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Dashboard Tabs](#dashboard-tabs)
- [Demo & Screenshots](#demo--screenshots)
- [Data Format](#data-format)

---

## ✨ Features

- 📊 **Interactive Dashboards** — 6 comprehensive tabs with real-time data visualization
- 🤖 **AI Chat Assistant** — Groq-powered intelligent Q&A about optimization results
- ✈️ **Fleet Optimization** — Aircraft assignment and rotation scheduling
- 📈 **Advanced Analytics** — KPIs, route analysis, network graphs, and constraint validation
- 🔍 **Detailed Tracking** — Flight assignments, aircraft utilization, and operational metrics
- 📊 **Solver Diagnostics** — MIP optimization status, runtime, and gap analysis

---

## 📁 Project Structure

```
airlineplanning/
├── app.py                          # Main Streamlit application (entry point)
├── data_loader.py                  # Data loading & KPI computation
├── data_loader_opt.py              # Optimization data loading
├── data_processor.py               # Data processing utilities
├── optimizer.py                    # Optimization engine
├── main.py                         # Backend core logic
├── streamlit.py                    # Streamlit configuration
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── data/
│   ├── inputs/                     # Input files for optimization
│   │   ├── flight_rotations.csv
│   │   ├── flight_iterinaries.csv
│   │   ├── starting_positions.csv
│   │   └── ending_positions.csv
│   ├── outputs/                    # Optimization results
│   │   ├── aircraft_summary.csv
│   │   ├── flight_assignments.csv
│   │   ├── route_assignments.csv
│   │   └── solver_summary.csv
│   └── logs/                       # Solver logs and models
│       ├── airline_model.lp
│       └── airline_solution.sol
│
└── image/                          # Visual assets & demo
  ├── chat_boat_demo.mp4          # Interactive demo video
  ├── flight_schedule.png         # Flight assignments view
  ├── aircraft_timing.png         # Aircraft rotation Gantt chart
  ├── aircraft_trafic.png         # Aircraft traffic analysis
  ├── flight_distribution.png     # Flight distribution analytics
  ├── flight_status.png           # Flight operational status
  ├── passenger.png               # Passenger analytics
  ├── reveneuby_aircraft.png      # Revenue by aircraft
  ├── network_graph.png           # Airport network visualization
  ├── optimizer_log.png           # Optimization logs & diagnostics
  └── constraints_validation.png  # Constraint validation results
```

```
airline_app/
├── app.py              # Main Streamlit app (6 tabs)
├── data_loader.py       # Data loading, KPI computation, constraint validation
├── requirements.txt
├── data/
│   ├── flight_rotations.csv      (input)
│   ├── starting_positions.csv    (input)
│   ├── ending_positions.csv      (input)
│   ├── flight_iterinaries.csv    (input)
│   ├── aircraft_summary.csv      (output)
│   ├── flight_assignments.csv    (output)
│   ├── route_assignments.csv     (output)
│   ├── solver_summary.csv        (optional, see below)
│   └── solver_log.txt            (optional, see below)
└── .streamlit/
    └── secrets.toml.example
```

---

## 🚀 Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Step 1: Clone or Download the Project

```bash
cd airlineplanning
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### Add Your Real Data

The `data/` folder currently contains **sample/demo data** transcribed from
your screenshots so the app runs out-of-the-box. Replace these 7 files with
your full real exports, keeping the **exact same filenames and column
names**:

| File | Type | Required Columns |
|---|---|---|
| `flight_rotations.csv` | **Input** | flight, date, aircraft, ori, des, start_time, end_time, duration |
| `starting_positions.csv` | **Input** | aircraft, airport |
| `ending_positions.csv` | **Input** | aircraft, airport |
| `flight_iterinaries.csv` | **Input** | cost, n_pass, flight, total_cost |
| `aircraft_summary.csv` | **Output** | aircraft, assigned_flights, passengers, revenue |
| `flight_assignments.csv` | **Output** | aircraft, flight, origin, destination, passengers, revenue |
| `route_assignments.csv` | **Output** | aircraft, from_node, to_node |

**Note:** A flight present in `flight_rotations.csv` but absent from
`flight_assignments.csv` is automatically treated as **Cancelled**.

### Optional: Solver Diagnostics

None of your 7 exported files contained solver diagnostics (objective value,
runtime, MIP gap, variable/constraint counts), so Tab 5 reads them from two
optional files — if missing, the dashboard shows "N/A" and a note instead of
crashing:

**`data/solver_summary.csv`** (single row):
```csv
solver_status,objective_value,runtime_seconds,mip_gap_percent,num_variables,num_constraints,total_operating_cost
Optimal,612937.5,184.6,0.42,5320,3870,287450
```

**`data/solver_log.txt`** — plain text, shown verbatim in an expandable "Logs"
section (e.g. your solver's branch-and-cut / iteration log).

### Set up the Groq API Key (for Chat Assistant)

You have two options — the key is never hardcoded into the app:

- **Easiest:** paste your key directly into the password field in the
  sidebar when the app is running.
- **Persistent:** set an environment variable before launching:
  ```bash
  export GROQ_API_KEY="your-key-here"
  ```
  Or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and
  fill in your key.

Get a free key at https://console.groq.com.

---

## 💻 Usage

### Run the Application

```bash
streamlit run app.py
```

The app will be available at: **http://localhost:8501**

---

## 📊 Dashboard Tabs

### 1️⃣ **Overview**

Main dashboard providing a high-level summary of operations:

- **KPI Cards** — 12 key performance indicators including:
  - Total flights, active aircraft, total passengers
  - Revenue metrics, cancellation rates
  - Solver performance (status, runtime, optimality gap)
- **Operated vs Cancelled** — Visual comparison of flight execution
- **Demand vs Served** — Passenger capacity utilization analysis
- Color-coded thresholds for quick health assessment

**Screenshot:** Overview dashboard with KPI cards and operational metrics

---

### 2️⃣ **Flight Schedule**

Detailed flight-to-aircraft assignment view with interactive filtering:

- **Searchable/Filterable Table** — Find flights by aircraft, route, date, or status
- **Cancelled Flight Highlighting** — Easily identify unassigned flights
- **Export Functionality** — Download filtered results as CSV
- **Columns Include:**
  - Aircraft assignment, origin/destination
  - Departure/arrival times, passengers, revenue
  - Flight status (operated/cancelled)

**Screenshot:** ![Flight Schedule](image/flight_schedule.png)
*Interactive flight assignment table with detailed operational information*

---

### 3️⃣ **Aircraft Rotations**

Visual representation of daily aircraft utilization and scheduling:

- **Gantt Chart Visualization** — Interactive timeline of each aircraft's day
  - Flight segments shown with duration and status
  - Idle time clearly marked between rotations
- **Utilization Metrics Table** — Per-aircraft performance:
  - Total flight hours, duty time, idle time
  - Number of legs, average block time
- **Rotation Analysis** — Identify bottlenecks and optimization opportunities

**Screenshot:** ![Aircraft Timing](image/aircraft_timing.png)
*Gantt chart showing aircraft daily rotation and utilization patterns*

---

### 4️⃣ **Network Analysis**

Airport and route-level operational insights:

- **Airport Hub Analysis:**
  - Departures/arrivals per airport
  - Passenger volume heatmap
  - Hub identification (degree centrality)
- **Top Routes Analysis:**
  - Most frequently operated routes
  - Revenue contribution by route
  - Route cost breakdown
- **Interactive Network Graph:**
  - Visual airport connectivity
  - In-degree/out-degree analysis
  - Airport importance visualization

**Screenshots:**
- ![Network Graph](image/network_graph.png) - *Airport network connectivity visualization*
- ![Aircraft Traffic](image/aircraft_trafic.png) - *Traffic flow analysis by airport*

---

### 5️⃣ **Optimization Results**

Detailed solver performance and constraint validation:

- **Solver Diagnostics:**
  - Optimization status (Optimal, Feasible, etc.)
  - Objective value (total operating cost)
  - Runtime and optimality gap (MIP gap %)
  - Variable and constraint counts
- **Scheduling Summary:**
  - Aircraft assignment statistics
  - Flight coverage analysis
  - Utilization vs capacity
- **Constraint Validation:**
  - Computed from actual data (not hardcoded)
  - Aircraft availability windows
  - Maintenance slots
  - Turnaround time compliance
- **Expandable Solver Log:**
  - Branch-and-cut iteration details
  - Solution quality progression
  - Diagnostic messages

**Screenshots:**
- ![Optimizer Log](image/optimizer_log.png) - *Solver diagnostics and performance metrics*
- ![Constraints Validation](image/constraints_validation.png) - *Constraint satisfaction verification*

---

### 6️⃣ **Chat Assistant (AI-Powered)**

Intelligent Q&A powered by Groq's language model:

- **Natural Language Queries** — Ask questions about your optimization results in plain English
- **Context-Aware Responses** — Assistant understands your fleet, routes, and assignments
- **Real-Time Analysis** — Get on-demand insights without manual drilling
- **Example Questions:**
  - "Which aircraft has the highest utilization?"
  - "What's the most profitable route?"
  - "How many flights are cancelled due to aircraft unavailability?"
  - "Show me the busiest airport by passenger volume"

**Demo:** See the chat assistant in action in the video below!

---

## 🎬 Demo & Screenshots

### Interactive Demo Video

Watch the AI chat assistant and full dashboard in action:

**[▶️ Watch Demo Video](image/chat_boat_demo.mp4)**

*Duration: ~2 minutes | Shows chat interactions, dashboard navigation, and real-time analytics*

---

### Key Dashboard Views

#### Flight Distribution & Status
![Flight Distribution](image/flight_distribution.png)
*Distribution of flights across the network with operational status breakdown*

![Flight Status](image/flight_status.png)
*Detailed flight status dashboard with cancellation and delay analysis*

#### Financial Analytics
![Revenue by Aircraft](image/reveneuby_aircraft.png)
*Revenue contribution analysis by aircraft in your fleet*

![Passenger Analytics](image/passenger.png)
*Passenger volume and capacity utilization across flights and aircraft*

---

## 📝 Data Format Details

### Input Data Format

**flight_rotations.csv** — Available flights to schedule
- Defines the universe of flights the optimizer can assign to aircraft

**starting_positions.csv** — Initial aircraft locations
- Airport where each aircraft begins its day

**ending_positions.csv** — Final aircraft destinations
- Airport where each aircraft must end its day (for next-day continuity)

**flight_iterinaries.csv** — Flight economics
- Operating cost per flight, passenger demand, total cost per rotation

### Output Data Format

**aircraft_summary.csv** — Fleet-level results
- Flights assigned, total passengers, revenue per aircraft

**flight_assignments.csv** — Individual flight allocations
- Which aircraft is assigned to each flight
- Passenger count and revenue impact

**route_assignments.csv** — Network routing
- Arc-based representation (from_node → to_node) of aircraft movements

---

## 🔧 Troubleshooting

**Issue:** App crashes when loading data
- **Solution:** Verify column names match exactly (case-sensitive)

**Issue:** Chat assistant not responding
- **Solution:** Ensure Groq API key is set and has available credits

**Issue:** Slow performance with large datasets
- **Solution:** Consider filtering data or increasing server resources

---

## 📞 Support & Contribution

For issues, feature requests, or contributions, please check the project documentation or reach out to the development team.

---

**Last Updated:** June 2026 | **Status:** Production Ready ✅
- **Chat Assistant** — ask natural-language questions about the loaded results; powered by Groq (`llama-3.3-70b-versatile` by default).

## Notes

- All computations (KPIs, utilization, constraint checks, network stats) are derived live from whatever CSVs are in `data/` — swap in new data and everything recalculates automatically.
- Constraint validation actually checks the data (aircraft continuity through the time-space network, no double-booked flights, time overlaps, start/end base matching) rather than always reporting "Satisfied".
