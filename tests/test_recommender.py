from pathlib import Path

from audit_risk_mapper.coverage_checker import check_coverage, detect_risks_from_text, review_risk_coverage
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


def test_text_detection_uses_seed_keywords():
    detected = detect_risks_from_text(
        ROOT / "data" / "seed",
        "결산일 직전 매출과 고객 검수 완료일을 확인해야 합니다.",
    )
    assert "RISK001" in detected
    assert "RISK005" in detected


def test_risk_coverage_separates_assertions_and_core_gaps():
    result = review_risk_coverage(ROOT, ["RISK001"], ["PROC004"])
    assert result["coverage_ratio"] < 1
    assert result["missing_core_procedures"][0]["procedure_id"] == "PROC001"
    assert result["weak_selections"][0]["procedure_id"] == "PROC004"
