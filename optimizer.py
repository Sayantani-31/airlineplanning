import os
import logging
from datetime import datetime
import pandas as pd
import gurobipy as gp
from gurobipy import GRB


class AirlineOptimizer:

    def __init__(self, data):

        self.data = data

        # -----------------------------------------
        # Create logs folder
        # -----------------------------------------

        os.makedirs("logs", exist_ok=True)

        self.log_file = os.path.join(
            "logs",
            f"solver_log.log"
        )

        self.logger = logging.getLogger(
            f"airline_optimizer_{datetime.now().timestamp()}"
        )

        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(self.log_file)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def solve(self, alpha=0.75):

        aircrafts = self.data["aircrafts"]
        airports = self.data["airports"]

        aircraft_flights = self.data["aircraft_flights"]

        flight_arcs_for_each_aircraft = self.data[
            "flight_arcs_for_each_aircraft"
        ]

        deltaplus_flightarcs = self.data[
            "deltaplus_flightarcs"
        ]

        deltaminus_flightarcs = self.data[
            "deltaminus_flightarcs"
        ]

        flight_revenue = self.data["flight_revenue"]

        flight_n_pass = self.data["flight_n_pass"]

        flight_origin = self.data["flight_origin"]

        flight_dest = self.data["flight_dest"]

        logger = self.logger

        logger.info("=" * 100)
        logger.info(f"Starting Optimization | Alpha={alpha}")

        model = gp.Model("airline_disruption")

        x = {}
        y = {}

        # --------------------------------------------------
        # VARIABLES
        # --------------------------------------------------

        for a in aircrafts:

            for f in aircraft_flights[a]:

                x[a, f] = model.addVar(
                    vtype=GRB.BINARY,
                    name=f"x_{a}_{f}"
                )

            for f1, f2 in flight_arcs_for_each_aircraft[a]:

                y[a, f1, f2] = model.addVar(
                    vtype=GRB.BINARY,
                    name=f"y_{a}_{f1}_{f2}"
                )

        model.update()

        logger.info(f"Variables Created : {model.NumVars}")

        # --------------------------------------------------
        # OBJECTIVE
        # --------------------------------------------------

        model.setObjective(
            gp.quicksum(
                (1 - x[a, f]) * flight_revenue[f]
                for a in aircrafts
                for f in aircraft_flights[a]
                if f in flight_revenue
            ),
            GRB.MINIMIZE
        )

        # --------------------------------------------------
        # CONSTRAINTS
        # --------------------------------------------------

        constr_count = 0

        for a in aircrafts:

            source = f"source_{a}"
            sink = f"sink_{a}"

            model.addConstr(
                gp.quicksum(
                    y[a, source, f2]
                    for f2 in deltaplus_flightarcs[a][source]
                ) == 1
            )
            constr_count += 1

            model.addConstr(
                gp.quicksum(
                    y[a, f1, sink]
                    for f1 in deltaminus_flightarcs[a][sink]
                ) == 1
            )
            constr_count += 1

            for f in aircraft_flights[a]:

                if str(f).startswith(("source", "sink")):
                    continue

                model.addConstr(
                    gp.quicksum(
                        y[a, f, f2]
                        for f2 in deltaplus_flightarcs[a][f]
                    )
                    ==
                    gp.quicksum(
                        y[a, f1, f]
                        for f1 in deltaminus_flightarcs[a][f]
                    )
                )

                constr_count += 1

        for a in aircrafts:

            for f in aircraft_flights[a]:

                if str(f).startswith("sink"):
                    continue

                model.addConstr(
                    x[a, f]
                    <=
                    gp.quicksum(
                        y[a, f, f2]
                        for f2 in deltaplus_flightarcs[a][f]
                    )
                )

                constr_count += 1

        for airport in airports:

            total_departures = len([
                f
                for a in aircrafts
                for f in aircraft_flights[a]
                if flight_origin[f] == airport
            ])

            total_arrivals = len([
                f
                for a in aircrafts
                for f in aircraft_flights[a]
                if flight_dest[f] == airport
            ])

            model.addConstr(
                gp.quicksum(
                    x[a, f]
                    for a in aircrafts
                    for f in aircraft_flights[a]
                    if flight_origin[f] == airport
                )
                <= alpha * total_departures
            )

            model.addConstr(
                gp.quicksum(
                    x[a, f]
                    for a in aircrafts
                    for f in aircraft_flights[a]
                    if flight_dest[f] == airport
                )
                <= alpha * total_arrivals
            )

            constr_count += 2

        logger.info(f"Constraints Created : {constr_count}")

        # --------------------------------------------------
        # SOLVER PARAMETERS
        # --------------------------------------------------

        model.setParam("OutputFlag", 1)

        logger.info("Optimization Started")

        model.optimize()

        # --------------------------------------------------
        # RESULTS
        # --------------------------------------------------

        logger.info(f"Status      : {model.Status}")
        logger.info(f"Runtime     : {model.Runtime:.2f}")

        if model.SolCount > 0:

            logger.info(f"Objective   : {model.ObjVal:,.2f}")

            if model.IsMIP:
                logger.info(f"MIP Gap     : {model.MIPGap:.6f}")
                logger.info(f"Node Count  : {model.NodeCount}")
                logger.info(f"Solutions   : {model.SolCount}")

            operated_flights = {

                a: [
                    f
                    for f in aircraft_flights[a]
                    if (
                        not str(f).startswith(("source", "sink"))
                        and x[a, f].X > 0.5
                    )
                ]

                for a in aircrafts
            }

            total_flights = sum(
                len(v)
                for v in operated_flights.values()
            )

            total_passengers = sum(

                flight_n_pass.get(f, 0)

                for a in aircrafts

                for f in aircraft_flights[a]

                if (
                    not str(f).startswith(("source", "sink"))
                    and x[a, f].X > 0.5
                )
            )

            aircraft_used = sum(
                1
                for a in aircrafts
                if len(operated_flights[a]) > 0
            )

            logger.info(f"Flights Served     : {total_flights}")
            logger.info(f"Passengers Served  : {total_passengers}")
            logger.info(f"Aircraft Utilized  : {aircraft_used}")

            logger.info("Operated Flights")

            for a, flights in operated_flights.items():
                logger.info(f"{a}: {flights}")

        model.write("logs/airline_model.lp")

        if model.SolCount > 0:
            model.write("logs/airline_solution.sol")

        print("\nOptimization Completed")
        print(f"Log File : {self.log_file}")


        flight_assignments = []

        for (a, f), var in x.items():

            if (
                var.X > 0.5
                and not str(f).startswith(("source", "sink"))
            ):

                flight_assignments.append({
                    "aircraft": a,
                    "flight": f,
                    "origin": flight_origin.get(f),
                    "destination": flight_dest.get(f),
                    "passengers": flight_n_pass.get(f, 0),
                    "revenue": flight_revenue.get(f, 0)
                })

        df_flight_assignments = pd.DataFrame(
            flight_assignments
        )               
        route_assignments = []

        for (a, f1, f2), var in y.items():

            if var.X > 0.5:

                route_assignments.append({
                    "aircraft": a,
                    "from_node": f1,
                    "to_node": f2
                })
        df_route_assignments = pd.DataFrame(
            route_assignments
        )

        aircraft_summary = []

        for a in aircrafts:

            assigned_flights = len(
                df_flight_assignments[
                    df_flight_assignments["aircraft"] == a
                ]
            )

            passengers = df_flight_assignments[
                df_flight_assignments["aircraft"] == a
            ]["passengers"].sum()

            revenue = df_flight_assignments[
                df_flight_assignments["aircraft"] == a
            ]["revenue"].sum()

            aircraft_summary.append({
                "aircraft": a,
                "assigned_flights": assigned_flights,
                "passengers": passengers,
                "revenue": revenue
            })

        df_aircraft_summary = pd.DataFrame(
            aircraft_summary
        )
        df_flight_assignments.to_csv(
            "data/outputs/flight_assignments.csv",
            index=False
        )

        df_route_assignments.to_csv(
            "data/outputs/route_assignments.csv",
            index=False
        )

        df_aircraft_summary.to_csv(
            "data/outputs/aircraft_summary.csv",
            index=False
        )

        solver_summary = pd.DataFrame([{
            "solver_status": model.Status if model.Status != GRB.OPTIMAL else "Optimal",
            "objective_value": round(model.ObjVal, 2) if model.SolCount > 0 else None,
            "runtime_seconds": round(model.Runtime, 2),
            "mip_gap_percent": round(model.MIPGap * 100, 2) if model.IsMIP else 0,
            "num_variables": model.NumVars,
            "num_constraints": model.NumConstrs,
            "total_operating_cost": round(model.ObjVal, 2) if model.SolCount > 0 else None
        }])

        solver_summary.to_csv(
            "data/outputs/solver_summary.csv",
            index=False
        )

        results = {
            "status": model.Status,
            "objective": model.ObjVal,
            "runtime": model.Runtime,
            "gap": model.MIPGap,
            "total_flights": total_flights,
            "total_passengers": total_passengers,
            "aircraft_used": aircraft_used,
            "operated_flights": operated_flights,
            "flight_assignments": df_flight_assignments,
            "route_assignments": df_route_assignments,
            "aircraft_summary": df_aircraft_summary,
            "model": model
        }

        return results

        # return model