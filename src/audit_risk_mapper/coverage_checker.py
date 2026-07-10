from __future__ import annotations

from pathlib import Path

from .data_io import parse_multi, read_csv


def check_coverage(root: Path, scenario_id: str, planned_procedure_ids: list[str]) -> dict[str, object]:
    scenarios = {row["scenario_id"]: row for row in read_csv(root / "data" / "generated" / "scenarios.csv")}
    procedures = {row["procedure_id"]: row for row in read_csv(root / "data" / "seed" / "procedure_library.csv")}
    scenario = scenarios[scenario_id]
    target_assertions = set(parse_multi(scenario["primary_assertions"]))
    covered = set()
    warnings = []
    for procedure_id in planned_procedure_ids:
        procedure = procedures.get(procedure_id)
        if not procedure:
            warnings.append(f"알 수 없는 절차 ID입니다: {procedure_id}")
            continue
        covered.update(target_assertions & set(parse_multi(procedure["primary_assertions"])))
    missing = sorted(target_assertions - covered)
    for assertion in missing:
        warnings.append(f"{assertion}: 직접 대응 절차가 선택되지 않았는지 검토가 필요합니다.")
    return {"covered_assertions": sorted(covered), "missing_assertions": missing, "warnings": warnings}
