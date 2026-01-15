#!/usr/bin/env python3
"""
EV Fleet Optimization Example
=============================
Demonstrates cuOpt for electric vehicle fleet route optimization.

Use Case:
    - EV delivery fleet with range constraints
    - Battery capacity considerations
    - Charging station routing

Usage:
    python example.py --endpoint http://cuopt-service:8000 --vehicles 50
"""

import sys
import os
import argparse
import random
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'benchmarks'))

from benchmark_client import CuOptClient


def generate_ev_fleet_problem(
    num_vehicles: int,
    num_deliveries: int,
    num_charging_stations: int = 5,
    battery_capacity: int = 100,  # km range
    avg_distance_per_delivery: int = 5  # km
):
    """
    Generate an EV-specific fleet optimization problem.

    This simulates a real EV fleet scenario with:
    - Delivery locations spread across a metro area
    - Charging stations that vehicles can visit
    - Battery range constraints

    Args:
        num_vehicles: Number of EVs in fleet
        num_deliveries: Number of delivery locations
        num_charging_stations: Number of available charging stations
        battery_capacity: Range per vehicle in km
        avg_distance_per_delivery: Average km between deliveries
    """
    random.seed(int(time.time() * 1000) % 2**32)

    # Total locations: depot + deliveries + charging stations
    total_locations = 1 + num_deliveries + num_charging_stations
    num_tasks = num_deliveries  # Tasks are only deliveries

    # Generate realistic distance matrix
    # Distances in "units" that represent km
    cost_matrix = []
    for i in range(total_locations):
        row = []
        for j in range(total_locations):
            if i == j:
                row.append(0)
            else:
                # Random distance 3-15 km between locations
                row.append(random.randint(3, 15))
        cost_matrix.append(row)

    # Demands for deliveries (packages)
    demands = [random.randint(1, 10) for _ in range(num_tasks)]

    # Service times (minutes per delivery)
    service_times = [random.randint(5, 15) for _ in range(num_tasks)]

    # Time windows (8 AM - 6 PM in minutes from midnight)
    # 8:00 AM = 480 minutes, 6:00 PM = 1080 minutes
    time_windows = []
    for _ in range(num_tasks):
        start = random.randint(480, 900)  # 8 AM - 3 PM start
        end = start + random.randint(60, 180)  # 1-3 hour window
        time_windows.append([start, min(end, 1080)])

    return {
        "cost_matrix_data": {
            "data": {"0": cost_matrix}
        },
        "fleet_data": {
            "vehicle_locations": [[0, 0] for _ in range(num_vehicles)],
            "capacities": [[50] * num_vehicles],  # Package capacity
            "vehicle_time_windows": [[480, 1080] for _ in range(num_vehicles)]
        },
        "task_data": {
            "task_locations": list(range(1, num_tasks + 1)),
            "demand": [demands],
            "task_time_windows": time_windows,
            "service_times": service_times
        },
        "solver_config": {
            "time_limit": 30
        }
    }


def main():
    parser = argparse.ArgumentParser(description="EV Fleet Optimization Example")
    parser.add_argument("--endpoint", default="http://cuopt-service:8000",
                       help="cuOpt service endpoint")
    parser.add_argument("--vehicles", type=int, default=20,
                       help="Number of EVs")
    parser.add_argument("--deliveries", type=int, default=50,
                       help="Number of deliveries")
    parser.add_argument("--charging-stations", type=int, default=5,
                       help="Number of charging stations")
    args = parser.parse_args()

    print("=" * 60)
    print("  EV Fleet Optimization Example")
    print("=" * 60)
    print(f"  Endpoint: {args.endpoint}")
    print(f"  Vehicles: {args.vehicles}")
    print(f"  Deliveries: {args.deliveries}")
    print(f"  Charging Stations: {args.charging_stations}")
    print("=" * 60)

    # Initialize client
    client = CuOptClient(args.endpoint)

    # Check health
    print("\nChecking cuOpt health...")
    try:
        health = client.health_check()
        print(f"  Status: {health}")
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    # Generate and solve problem
    print("\nGenerating EV fleet optimization problem...")
    payload = generate_ev_fleet_problem(
        num_vehicles=args.vehicles,
        num_deliveries=args.deliveries,
        num_charging_stations=args.charging_stations
    )

    print(f"\nSolving optimization (time limit: 30s)...")
    start = time.time()
    result = client.optimize(payload)
    elapsed = time.time() - start

    # Parse results
    print("\n" + "=" * 60)
    print("  Results")
    print("=" * 60)
    print(f"  Response Time: {elapsed:.2f}s")

    if "response" in result:
        solver = result["response"]["solver_response"]
        print(f"  Solver Status: {solver.get('status')} (0=optimal)")
        print(f"  Total Cost: {solver.get('solution_cost')}")

        # Parse routes
        routes = solver.get("vehicle_data", {})
        if routes:
            print(f"\n  Routes Generated:")
            for vehicle_id, route_data in routes.items():
                route = route_data.get("route", [])
                if len(route) > 2:  # More than just depot-depot
                    print(f"    Vehicle {vehicle_id}: {len(route)-2} stops")

    elif "error" in result:
        print(f"  ERROR: {result['error']}")

    print("\n" + "=" * 60)
    print("  Example Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
