from datetime import datetime
import networkx as nx
import pandas as pd


def process_data(data, n_airports=4):

    df_current_plan = data["current_plan"].copy()
    df_starting_positions = data["starting_positions"]
    df_ending_positions = data["ending_positions"]
    df_itineraries = data["itineraries"]

    # ---------------------------------
    # Convert Times
    # ---------------------------------
    print(df_current_plan["start_time"].head())
    print(df_current_plan["start_time"].dtype)


    # for col in ["start_time", "end_time", "duration"]:

    #     df_current_plan[col] = (
    #         pd.to_datetime(
    #             df_current_plan[col],
    #             format="%H:%M"
    #         )
    #         .dt.time
    #     )
    for col in ["start_time", "end_time", "duration"]:
        df_current_plan[col] = pd.to_datetime(
            df_current_plan[col]
        ).dt.time

    # ---------------------------------
    # Network Reduction
    # ---------------------------------

    arcs = list(
        df_current_plan[
            ["ori", "des"]
        ].itertuples(index=False, name=None)
    )

    G = nx.MultiDiGraph()
    G.add_edges_from(arcs)

    top_airports = [
        i
        for i, j in sorted(
            G.degree,
            key=lambda x: x[1],
            reverse=True
        )[:n_airports]
    ]

    df_current_plan = df_current_plan[
        df_current_plan["ori"].isin(top_airports)
    ]

    df_current_plan = df_current_plan[
        df_current_plan["des"].isin(top_airports)
    ]

    # ---------------------------------
    # Basic Sets
    # ---------------------------------

    flights = df_current_plan["flight"].unique()

    aircrafts = df_current_plan["aircraft"].unique()

    airports = set(
        df_current_plan["ori"].unique()
    ).union(
        set(df_current_plan["des"].unique())
    )

    # ---------------------------------
    # Flight Dictionaries
    # ---------------------------------

    flight_origin = (
        df_current_plan
        .set_index("flight")["ori"]
        .to_dict()
    )

    flight_dest = (
        df_current_plan
        .set_index("flight")["des"]
        .to_dict()
    )

    flight_start_time = (
        df_current_plan
        .set_index("flight")["start_time"]
        .to_dict()
    )

    flight_end_time = (
        df_current_plan
        .set_index("flight")["end_time"]
        .to_dict()
    )

    # ---------------------------------
    # Aircraft Positions
    # ---------------------------------

    aircraft_start = (
        df_starting_positions
        .set_index("aircraft")["airport"]
        .to_dict()
    )

    aircraft_end = (
        df_ending_positions
        .set_index("aircraft")["airport"]
        .to_dict()
    )

    # ---------------------------------
    # Revenue
    # ---------------------------------

    df_itineraries["total_cost"] = (
        df_itineraries["cost"]
        * df_itineraries["n_pass"]
    )

    flight_revenue = (
        df_itineraries
        .groupby("flight")["total_cost"]
        .sum()
        .to_dict()
    )

    flight_n_pass = (
        df_itineraries
        .groupby("flight")["n_pass"]
        .sum()
        .to_dict()
    )

    # ---------------------------------
    # Aircraft Flight Lists
    # ---------------------------------

    aircraft_flights = (
        df_current_plan
        .groupby("aircraft")["flight"]
        .apply(list)
        .to_dict()
    )

    flight_arcs_for_each_aircraft = {}
    deltaplus_flightarcs = {}
    deltaminus_flightarcs = {}

    for a in aircraft_flights:

        aircraft_flights[a] += [
            f"source_{a}",
            f"sink_{a}"
        ]

        flight_origin[f"source_{a}"] = aircraft_end[a]
        flight_dest[f"source_{a}"] = aircraft_start[a]

        flight_origin[f"sink_{a}"] = aircraft_end[a]
        flight_dest[f"sink_{a}"] = aircraft_start[a]

        flight_start_time[f"source_{a}"] = (
            datetime.strptime(
                "00:00",
                "%H:%M"
            ).time()
        )

        flight_end_time[f"source_{a}"] = (
            datetime.strptime(
                "00:00",
                "%H:%M"
            ).time()
        )

        flight_start_time[f"sink_{a}"] = (
            datetime.strptime(
                "23:59",
                "%H:%M"
            ).time()
        )

        flight_end_time[f"sink_{a}"] = (
            datetime.strptime(
                "23:59",
                "%H:%M"
            ).time()
        )

        flight_arcs_for_each_aircraft[a] = []

        deltaplus_flightarcs[a] = {
            f: []
            for f in aircraft_flights[a]
        }

        deltaminus_flightarcs[a] = {
            f: []
            for f in aircraft_flights[a]
        }

        for f1 in aircraft_flights[a]:

            for f2 in aircraft_flights[a]:

                if (
                    f1 != f2
                    and flight_end_time[f1]
                    < flight_start_time[f2]
                    and flight_dest[f1]
                    == flight_origin[f2]
                ):

                    flight_arcs_for_each_aircraft[a].append(
                        (f1, f2)
                    )

                    deltaplus_flightarcs[a][f1].append(
                        f2
                    )

                    deltaminus_flightarcs[a][f2].append(
                        f1
                    )

                elif (
                    str(f1).startswith("source")
                    and str(f2).startswith("sink")
                ):

                    flight_arcs_for_each_aircraft[a].append(
                        (f1, f2)
                    )

                    deltaplus_flightarcs[a][f1].append(
                        f2
                    )

                    deltaminus_flightarcs[a][f2].append(
                        f1
                    )

    return {
        "flights": flights,
        "aircrafts": aircrafts,
        "airports": airports,
        "flight_origin": flight_origin,
        "flight_dest": flight_dest,
        "flight_start_time": flight_start_time,
        "flight_end_time": flight_end_time,
        "flight_revenue": flight_revenue,
        "flight_n_pass": flight_n_pass,
        "aircraft_flights": aircraft_flights,
        "flight_arcs_for_each_aircraft": flight_arcs_for_each_aircraft,
        "deltaplus_flightarcs": deltaplus_flightarcs,
        "deltaminus_flightarcs": deltaminus_flightarcs,
    }