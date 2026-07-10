from __future__ import annotations

from pathlib import Path

from .data_io import read_csv


def load_pair_features(root: Path) -> tuple[list[list[float]], list[str]]:
    rows = read_csv(root / "data" / "generated" / "scenario_procedure_pairs.csv")
    features = []
    labels = []
    for row in rows:
        features.append([
            float(row["account_match"]),
            float(row["primary_assertion_overlap"]),
            float(row["secondary_assertion_overlap"]),
            float(row["risk_tag_overlap"]),
            float(row["evidence_match"]),
            1.0 if row["required_conditions_met"] == "true" else 0.0,
            1.0 if row["exclusion_condition_hit"] == "true" else 0.0,
            float(row["timing_match"]),
            float(row["fraud_indicator_match"]),
        ])
        grade = int(row["relevance_grade"])
        labels.append("recommended" if grade >= 2 else "conditional" if grade == 1 else "weak_match" if grade == 0 else "not_applicable")
    return features, labels
