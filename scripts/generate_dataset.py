from __future__ import annotations

import argparse
from pathlib import Path

from audit_risk_mapper.scenario_generator import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario-count", type=int, default=None)
    parser.add_argument("--pairs-per-scenario", type=int, default=5)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    scenario_count = args.scenario_count if args.scenario_count is not None else (100 if args.mode == "smoke" else 2000)
    report = generate_dataset(root, seed=args.seed, scenario_count=scenario_count, pairs_per_scenario=args.pairs_per_scenario)
    print(report)

if __name__ == "__main__":
    main()
