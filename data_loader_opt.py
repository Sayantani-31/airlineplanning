import pandas as pd


def load_data(data_dir="data/inputs"):

    df_current_plan = pd.read_csv(
        f"{data_dir}/flight_rotations.csv"
    )

    df_starting_positions = pd.read_csv(
        f"{data_dir}/starting_positions.csv"
    )

    df_ending_positions = pd.read_csv(
        f"{data_dir}/ending_positions.csv"
    )

    df_itineraries = pd.read_csv(
        f"{data_dir}/flight_iterinaries.csv"
    )

    return {
        "current_plan": df_current_plan,
        "starting_positions": df_starting_positions,
        "ending_positions": df_ending_positions,
        "itineraries": df_itineraries,
    }