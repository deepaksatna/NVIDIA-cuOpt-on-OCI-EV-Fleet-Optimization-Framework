#!/usr/bin/env python3
"""
cuOpt Benchmark Client
======================
Python client for benchmarking NVIDIA cuOpt on OCI.

Usage:
    from benchmark_client import CuOptClient

    client = CuOptClient("http://cuopt-service:8000")
    result = client.optimize_fleet(num_vehicles=50, num_locations=100)
"""

import os
import json
import time
import random
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any


class CuOptClient:
    """Client for interacting with cuOpt optimization service."""

    def __init__(self, endpoint: str = None):
        """
        Initialize the cuOpt client.

        Args:
            endpoint: cuOpt service endpoint URL
        """
        self.endpoint = endpoint or os.environ.get("CUOPT_ENDPOINT", "http://cuopt-service:8000")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def health_check(self) -> Dict:
        """Check cuOpt service health."""
        response = self.session.get(f"{self.endpoint}/cuopt/health", timeout=30)
        return response.json()

    def generate_cost_matrix(self, num_locations: int, seed: int = None) -> List[List[int]]:
        """
        Generate a random cost/distance matrix.

        Args:
            num_locations: Number of locations including depot
            seed: Random seed for reproducibility

        Returns:
            Square cost matrix
        """
        if seed:
            random.seed(seed)
        else:
            random.seed(int(time.time() * 1000) % 2**32)

        matrix = []
        for i in range(num_locations):
            row = []
            for j in range(num_locations):
                if i == j:
                    row.append(0)
                else:
                    row.append(random.randint(5, 100))
            matrix.append(row)
        return matrix

    def build_vrp_payload(
        self,
        num_vehicles: int,
        num_locations: int,
        vehicle_capacity: int = 100,
        time_limit: int = 30,
        time_windows: Optional[List[List[int]]] = None,
        demands: Optional[List[int]] = None,
        service_times: Optional[List[int]] = None
    ) -> Dict:
        """
        Build a VRP optimization payload.

        Args:
            num_vehicles: Number of vehicles
            num_locations: Total locations including depot
            vehicle_capacity: Capacity per vehicle
            time_limit: Solver time limit in seconds
            time_windows: Optional time windows for tasks
            demands: Optional demand per task
            service_times: Optional service time per task

        Returns:
            cuOpt API payload
        """
        cost_matrix = self.generate_cost_matrix(num_locations)
        num_tasks = num_locations - 1  # Exclude depot

        # Default demands if not provided
        if demands is None:
            demands = [random.randint(5, 20) for _ in range(num_tasks)]

        # Default service times if not provided
        if service_times is None:
            service_times = [random.randint(5, 15) for _ in range(num_tasks)]

        # Default time windows if not provided (8 AM - 6 PM)
        if time_windows is None:
            time_windows = [[0, 480] for _ in range(num_tasks)]

        return {
            "cost_matrix_data": {
                "data": {"0": cost_matrix}
            },
            "fleet_data": {
                "vehicle_locations": [[0, 0] for _ in range(num_vehicles)],
                "capacities": [[vehicle_capacity] * num_vehicles],
                "vehicle_time_windows": [[0, 480] for _ in range(num_vehicles)]
            },
            "task_data": {
                "task_locations": list(range(1, num_locations)),
                "demand": [demands],
                "task_time_windows": time_windows,
                "service_times": service_times
            },
            "solver_config": {
                "time_limit": time_limit
            }
        }

    def optimize(self, payload: Dict, timeout: int = None) -> Dict:
        """
        Send optimization request to cuOpt.

        Args:
            payload: cuOpt API payload
            timeout: Request timeout in seconds

        Returns:
            Optimization result
        """
        if timeout is None:
            timeout = payload.get("solver_config", {}).get("time_limit", 30) + 120

        start = time.time()
        response = self.session.post(
            f"{self.endpoint}/cuopt/cuopt",
            json=payload,
            timeout=timeout
        )
        elapsed = time.time() - start

        result = response.json()
        result["_metadata"] = {
            "response_time_seconds": elapsed,
            "status_code": response.status_code
        }

        return result

    def optimize_fleet(
        self,
        num_vehicles: int,
        num_locations: int,
        vehicle_capacity: int = 100,
        time_limit: int = 30,
        **kwargs
    ) -> Dict:
        """
        Optimize a fleet routing problem.

        Args:
            num_vehicles: Number of vehicles
            num_locations: Total locations including depot
            vehicle_capacity: Capacity per vehicle
            time_limit: Solver time limit
            **kwargs: Additional arguments for build_vrp_payload

        Returns:
            Optimization result with routes
        """
        payload = self.build_vrp_payload(
            num_vehicles=num_vehicles,
            num_locations=num_locations,
            vehicle_capacity=vehicle_capacity,
            time_limit=time_limit,
            **kwargs
        )
        return self.optimize(payload)

    def run_benchmark(
        self,
        scenarios: List[Dict],
        iterations_per_scenario: int = 5
    ) -> Dict:
        """
        Run benchmark across multiple scenarios.

        Args:
            scenarios: List of scenario configurations
            iterations_per_scenario: Number of iterations per scenario

        Returns:
            Benchmark results
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": self.endpoint,
            "scenarios": {}
        }

        for scenario in scenarios:
            name = scenario.get("name", f"scenario_{len(results['scenarios'])}")
            print(f"\nRunning: {name}")
            print(f"  Vehicles: {scenario['num_vehicles']}, Locations: {scenario['num_locations']}")

            scenario_results = []
            for i in range(iterations_per_scenario):
                result = self.optimize_fleet(**scenario)
                scenario_results.append({
                    "iteration": i + 1,
                    "response_time": result["_metadata"]["response_time_seconds"],
                    "success": "response" in result
                })
                print(f"  [{i+1}/{iterations_per_scenario}] {result['_metadata']['response_time_seconds']:.2f}s")

            results["scenarios"][name] = {
                "config": scenario,
                "results": scenario_results
            }

        return results


def main():
    """Example usage of the benchmark client."""
    import argparse

    parser = argparse.ArgumentParser(description="cuOpt Benchmark Client")
    parser.add_argument("--endpoint", default=None, help="cuOpt endpoint URL")
    parser.add_argument("--vehicles", type=int, default=10, help="Number of vehicles")
    parser.add_argument("--locations", type=int, default=20, help="Number of locations")
    parser.add_argument("--time-limit", type=int, default=30, help="Solver time limit")
    args = parser.parse_args()

    client = CuOptClient(args.endpoint)

    print("Checking health...")
    print(client.health_check())

    print(f"\nOptimizing {args.vehicles} vehicles, {args.locations} locations...")
    result = client.optimize_fleet(
        num_vehicles=args.vehicles,
        num_locations=args.locations,
        time_limit=args.time_limit
    )

    print(f"\nResponse time: {result['_metadata']['response_time_seconds']:.2f}s")
    if "response" in result:
        solver = result["response"]["solver_response"]
        print(f"Status: {solver.get('status')}")
        print(f"Cost: {solver.get('solution_cost')}")


if __name__ == "__main__":
    main()
