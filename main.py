from data_loader_opt import load_data
from data_processor import process_data
from optimizer import AirlineOptimizer


def main():

    print("=" * 60)
    print("AIRLINE DISRUPTION OPTIMIZATION")
    print("=" * 60)

    # -------------------------------------
    # Load Data
    # -------------------------------------

    raw_data = load_data("data/inputs")

    # -------------------------------------
    # Process Data
    # -------------------------------------

    processed_data = process_data(
        raw_data,
        n_airports=4
    )

    print(
        f"Flights   : {len(processed_data['flights'])}"
    )

    print(
        f"Aircrafts : {len(processed_data['aircrafts'])}"
    )

    print(
        f"Airports  : {len(processed_data['airports'])}"
    )

    # -------------------------------------
    # Run Optimizer
    # -------------------------------------

    alpha = 0.75

    optimizer = AirlineOptimizer(
        processed_data
    )

    # model = optimizer.solve(alpha)

    # print(
    #     f"\nOptimization Status: {model.Status}"
    # )
    results = optimizer.solve(alpha=0.75)

    print(f"Objective: {results['objective']:,.2f}")
    print(f"Flights Served: {results['total_flights']}")
    print(f"Aircraft Used: {results['aircraft_used']}")
    print(f"Total Flights : {results['total_flights']}")
    print(f"Total Passengers: {results['total_passengers']}")
    print("\nFlight Assignments")
    print(results["flight_assignments"])
    print("\nAircraft Summary")
    print(results["aircraft_summary"])

    return results


if __name__ == "__main__":
    results=main()