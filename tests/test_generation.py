from pathlib import Path

from audit_risk_mapper.scenario_generator import generate_dataset
from audit_risk_mapper.validators import validate_dataset

ROOT = Path(__file__).resolve().parents[1]


def test_smoke_generation_is_valid():
    report = generate_dataset(ROOT, seed=42, scenario_count=20, pairs_per_scenario=5)
    assert report["scenario_count"] == 20
    assert report["pair_count"] == 100
    errors, _ = validate_dataset(ROOT, expected_scenarios=20, expected_pairs=100)
    assert errors == []


def test_generation_reproducible():
    first = generate_dataset(ROOT, seed=42, scenario_count=10, pairs_per_scenario=5)
    second = generate_dataset(ROOT, seed=42, scenario_count=10, pairs_per_scenario=5)
    assert first["class_distribution"] == second["class_distribution"]
