from __future__ import annotations

from pathlib import Path

from .data_io import parse_multi, read_csv


def recommend_for_scenario(root: Path, scenario_id: str, top_n: int = 5) -> list[dict[str, object]]:
    generated = root / "data" / "generated"
    seed = root / "data" / "seed"
    scenarios = {row["scenario_id"]: row for row in read_csv(generated / "scenarios.csv")}
    procedures = {row["procedure_id"]: row for row in read_csv(seed / "procedure_library.csv")}
    pairs = [row for row in read_csv(generated / "scenario_procedure_pairs.csv") if row["scenario_id"] == scenario_id]
    if scenario_id not in scenarios:
        raise KeyError(f"Unknown scenario_id: {scenario_id}")
    ranked = sorted(pairs, key=lambda row: (int(row["relevance_grade"]), int(row["risk_tag_overlap"])), reverse=True)
    result = []
    for row in ranked[:top_n]:
        procedure = procedures[row["procedure_id"]]
        score = max(0.0, min(1.0, 0.45 + int(row["relevance_grade"]) * 0.15 + int(row["risk_tag_overlap"]) * 0.03))
        result.append({
            "procedure_id": row["procedure_id"],
            "procedure_name": procedure["procedure_name_ko"],
            "audit_objective": procedure["audit_objective_ko"],
            "fit_score": round(score, 3),
            "matched_assertions": parse_multi(procedure["primary_assertions"]),
            "matched_tags": parse_multi(procedure["applicable_risk_tags"]),
            "unmet_conditions": parse_multi(row["missing_required_conditions"]),
            "recommendation_reason": row["rationale_ko"],
            "limitations": procedure["limitations"],
            "relation_type": row["relation_label"],
        })
    return result
