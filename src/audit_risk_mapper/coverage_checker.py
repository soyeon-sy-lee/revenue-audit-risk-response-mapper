from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .data_io import parse_multi, read_csv


ASSERTION_LABELS = {
    "occurrence": "발생사실",
    "completeness": "완전성",
    "accuracy": "정확성",
    "cutoff": "기간귀속",
    "classification": "분류",
    "presentation": "표시",
    "existence": "실재성",
    "rights_and_obligations": "권리와 의무",
    "valuation": "평가",
}


def detect_risks_from_text(seed_dir: Path, narrative: str) -> list[str]:
    """Return risk IDs whose curated Korean keywords occur in the narrative."""
    text = narrative.casefold().strip()
    if not text:
        return []
    keyword_path = seed_dir / "risk_keyword_library.csv"
    if not keyword_path.exists():
        return []
    return [
        row["risk_id"]
        for row in read_csv(keyword_path)
        if any(keyword.casefold() in text for keyword in parse_multi(row["keywords_ko"]))
    ]


def review_risk_coverage(root: Path, risk_ids: list[str], planned_procedure_ids: list[str]) -> dict[str, object]:
    """Review assertion coverage and risk-to-procedure gaps from the seed knowledge base."""
    seed = root / "data" / "seed"
    risks = {row["risk_id"]: row for row in read_csv(seed / "risk_signal_library.csv")}
    procedures = {row["procedure_id"]: row for row in read_csv(seed / "procedure_library.csv")}
    mappings = read_csv(seed / "risk_procedure_mapping.csv")

    unknown_risks = sorted(set(risk_ids) - risks.keys())
    unknown_procedures = sorted(set(planned_procedure_ids) - procedures.keys())
    selected_risks = [risks[risk_id] for risk_id in risk_ids if risk_id in risks]
    selected_procedures = [procedures[procedure_id] for procedure_id in planned_procedure_ids if procedure_id in procedures]

    target_assertions = sorted({
        assertion
        for risk in selected_risks
        for assertion in parse_multi(risk["primary_assertions"])
    })
    assertion_procedures: dict[str, list[str]] = {}
    for assertion in target_assertions:
        assertion_procedures[assertion] = [
            procedure["procedure_id"]
            for procedure in selected_procedures
            if assertion in set(parse_multi(procedure["primary_assertions"]) + parse_multi(procedure["secondary_assertions"]))
        ]
    covered = sorted(assertion for assertion, ids in assertion_procedures.items() if ids)
    missing = sorted(set(target_assertions) - set(covered))

    relevant_mappings = [row for row in mappings if row["risk_id"] in risk_ids]
    by_risk: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_procedure: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in relevant_mappings:
        by_risk[row["risk_id"]].append(row)
        by_procedure[row["procedure_id"]].append(row)

    missing_core: list[dict[str, str]] = []
    for risk_id in risk_ids:
        for row in by_risk[risk_id]:
            if row["relation_label"] == "core" and row["procedure_id"] not in planned_procedure_ids:
                missing_core.append({
                    "risk_id": risk_id,
                    "risk_name": risks[risk_id]["risk_name_ko"],
                    "procedure_id": row["procedure_id"],
                    "procedure_name": procedures[row["procedure_id"]]["procedure_name_ko"],
                    "gap": row["gap_if_omitted_ko"],
                })

    weak_selections: list[dict[str, str]] = []
    for procedure_id in planned_procedure_ids:
        if procedure_id not in procedures:
            continue
        grades = [int(row["relevance_grade"]) for row in by_procedure.get(procedure_id, [])]
        if not grades or max(grades) <= 0:
            weak_selections.append({
                "procedure_id": procedure_id,
                "procedure_name": procedures[procedure_id]["procedure_name_ko"],
                "reason": "선택한 위험과의 직접 대응관계가 약하거나 Seed 매핑에 없습니다.",
            })

    recommendations: list[dict[str, object]] = []
    for procedure_id, rows in by_procedure.items():
        best_grade = max(int(row["relevance_grade"]) for row in rows)
        if best_grade < 1:
            continue
        best_rows = [row for row in rows if int(row["relevance_grade"]) == best_grade]
        matched_risk_ids = sorted({row["risk_id"] for row in rows if int(row["relevance_grade"]) >= 1})
        recommendations.append({
            "procedure_id": procedure_id,
            "procedure_name": procedures[procedure_id]["procedure_name_ko"],
            "audit_objective": procedures[procedure_id]["audit_objective_ko"],
            "description": procedures[procedure_id]["procedure_description_ko"],
            "limitations": procedures[procedure_id]["limitations"],
            "relation_label": best_rows[0]["relation_label"],
            "relevance_grade": best_grade,
            "matched_risk_ids": matched_risk_ids,
            "matched_risk_names": [risks[risk_id]["risk_name_ko"] for risk_id in matched_risk_ids],
            "reason": best_rows[0]["rationale_ko"],
            "selected": procedure_id in planned_procedure_ids,
        })
    recommendations.sort(key=lambda item: (-int(item["relevance_grade"]), not bool(item["selected"]), str(item["procedure_id"])))

    warnings = [f"알 수 없는 위험 ID입니다: {risk_id}" for risk_id in unknown_risks]
    warnings.extend(f"알 수 없는 절차 ID입니다: {procedure_id}" for procedure_id in unknown_procedures)
    warnings.extend(
        f"{ASSERTION_LABELS.get(assertion, assertion)} 주장에 대응하는 절차가 선택되지 않았습니다."
        for assertion in missing
    )

    return {
        "target_assertions": target_assertions,
        "covered_assertions": covered,
        "missing_assertions": missing,
        "assertion_procedures": assertion_procedures,
        "coverage_ratio": len(covered) / len(target_assertions) if target_assertions else 0.0,
        "missing_core_procedures": missing_core,
        "weak_selections": weak_selections,
        "recommendations": recommendations,
        "warnings": warnings,
    }


def check_coverage(root: Path, scenario_id: str, planned_procedure_ids: list[str]) -> dict[str, object]:
    scenarios = {row["scenario_id"]: row for row in read_csv(root / "data" / "generated" / "scenarios.csv")}
    scenario = scenarios[scenario_id]
    return review_risk_coverage(root, parse_multi(scenario["risk_ids"]), planned_procedure_ids)
