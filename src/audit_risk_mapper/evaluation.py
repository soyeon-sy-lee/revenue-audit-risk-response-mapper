from __future__ import annotations

from collections import Counter
from pathlib import Path

from .data_io import read_csv, write_json


def summarize_generated_data(root: Path) -> dict:
    scenarios = read_csv(root / "data" / "generated" / "scenarios.csv")
    pairs = read_csv(root / "data" / "generated" / "scenario_procedure_pairs.csv")
    summary = {
        "scenario_count": len(scenarios),
        "pair_count": len(pairs),
        "class_distribution": dict(Counter(row["relation_label"] for row in pairs)),
        "split_distribution": dict(Counter(row["split"] for row in scenarios)),
        "limitations": "합성 규칙 기반 데이터셋의 내부 일관성 요약이며 실제 감사업무 성능이 아닙니다.",
    }
    write_json(root / "data" / "generated" / "metrics.json", summary)
    return summary
