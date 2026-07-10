from __future__ import annotations

import argparse
from pathlib import Path

from audit_risk_mapper.data_io import write_json
from audit_risk_mapper.validators import validate_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-scenarios", type=int, default=None)
    parser.add_argument("--expected-pairs", type=int, default=None)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    errors, warnings = validate_dataset(root, args.expected_scenarios, args.expected_pairs)
    report = {"errors": errors, "warnings": warnings, "ok": not errors}
    write_json(root / "data" / "generated" / "validation_report.json", report)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Dataset validation passed")

if __name__ == "__main__":
    main()
