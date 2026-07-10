from pathlib import Path

from audit_risk_mapper.coverage_checker import check_coverage
from audit_risk_mapper.question_generator import questions_for_risks
from audit_risk_mapper.recommender import recommend_for_scenario
from audit_risk_mapper.scenario_generator import generate_dataset

ROOT = Path(__file__).resolve().parents[1]


def test_recommendations_and_questions():
    generate_dataset(ROOT, seed=42, scenario_count=5, pairs_per_scenario=5)
    recs = recommend_for_scenario(ROOT, "SCN04200001")
    assert len(recs) == 5
    assert recs[0]["fit_score"] >= recs[-1]["fit_score"]
    questions = questions_for_risks(ROOT / "data" / "seed", ["RISK001"])
    assert questions


def test_coverage_checker_warns_missing_assertions():
    generate_dataset(ROOT, seed=42, scenario_count=5, pairs_per_scenario=5)
    result = check_coverage(ROOT, "SCN04200001", ["PROC004"])
    assert "warnings" in result
