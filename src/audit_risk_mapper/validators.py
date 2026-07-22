from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re

from .data_io import parse_multi, read_csv
from .schemas import (
    GRADE_TO_LABEL,
    MAPPING_COLUMNS,
    PAIR_COLUMNS,
    PROCEDURE_COLUMNS,
    RISK_COLUMNS,
    RISK_KEYWORD_COLUMNS,
    SCENARIO_COLUMNS,
    TAG_COLUMNS,
    TEMPLATE_COLUMNS,
    VALID_ASSERTIONS,
    VALID_RELATION_LABELS,
    VALID_REVIEW_STATUS,
)

REQUIRED = {
    "tag_dictionary.csv": TAG_COLUMNS,
    "risk_signal_library.csv": RISK_COLUMNS,
    "risk_keyword_library.csv": RISK_KEYWORD_COLUMNS,
    "procedure_library.csv": PROCEDURE_COLUMNS,
    "risk_procedure_mapping.csv": MAPPING_COLUMNS,
    "scenario_templates.csv": TEMPLATE_COLUMNS,
    "scenarios.csv": SCENARIO_COLUMNS,
    "scenario_procedure_pairs.csv": PAIR_COLUMNS,
}


def _missing_columns(rows: list[dict[str, str]], required: list[str]) -> list[str]:
    actual = set(rows[0].keys()) if rows else set()
    return [col for col in required if col not in actual]


def _assertions(rows: list[dict[str, str]], columns: list[str]) -> list[str]:
    errors = []
    for row in rows:
        for col in columns:
            invalid = set(parse_multi(row.get(col))) - VALID_ASSERTIONS
            if invalid:
                errors.append(f"{row.get('risk_id') or row.get('procedure_id') or row.get('scenario_id')}: invalid {col} {sorted(invalid)}")
    return errors


def validate_dataset(root: Path, expected_scenarios: int | None = None, expected_pairs: int | None = None) -> tuple[list[str], list[str]]:
    seed = root / "data" / "seed"
    generated = root / "data" / "generated"
    errors: list[str] = []
    warnings: list[str] = []

    tags = read_csv(seed / "tag_dictionary.csv")
    risks = read_csv(seed / "risk_signal_library.csv")
    risk_keywords = read_csv(seed / "risk_keyword_library.csv")
    procedures = read_csv(seed / "procedure_library.csv")
    mappings = read_csv(seed / "risk_procedure_mapping.csv")
    templates = read_csv(seed / "scenario_templates.csv")
    scenarios = read_csv(generated / "scenarios.csv") if (generated / "scenarios.csv").exists() else []
    pairs = read_csv(generated / "scenario_procedure_pairs.csv") if (generated / "scenario_procedure_pairs.csv").exists() else []

    file_rows = {
        "tag_dictionary.csv": tags,
        "risk_signal_library.csv": risks,
        "risk_keyword_library.csv": risk_keywords,
        "procedure_library.csv": procedures,
        "risk_procedure_mapping.csv": mappings,
        "scenario_templates.csv": templates,
        "scenarios.csv": scenarios,
        "scenario_procedure_pairs.csv": pairs,
    }
    for filename, required in REQUIRED.items():
        rows = file_rows[filename]
        if not rows:
            errors.append(f"{filename}: no rows")
            continue
        missing = _missing_columns(rows, required)
        if missing:
            errors.append(f"{filename}: missing columns {missing}")

    for name, rows, key in [
        ("tags", tags, "tag_id"), ("risks", risks, "risk_id"),
        ("risk keywords", risk_keywords, "risk_id"), ("procedures", procedures, "procedure_id"),
        ("mappings", mappings, "mapping_id"), ("templates", templates, "template_id"),
        ("scenarios", scenarios, "scenario_id"), ("pairs", pairs, "pair_id"),
    ]:
        counts = Counter(row.get(key, "") for row in rows)
        dupes = [value for value, count in counts.items() if value and count > 1]
        if dupes:
            errors.append(f"{name}: duplicate {key} {dupes[:5]}")

    tag_codes = {row["tag_code"] for row in tags}
    risk_ids = {row["risk_id"] for row in risks}
    procedure_ids = {row["procedure_id"] for row in procedures}
    template_ids = {row["template_id"] for row in templates}
    scenario_ids = {row["scenario_id"] for row in scenarios}

    errors.extend(_assertions(risks, ["primary_assertions", "secondary_assertions"]))
    errors.extend(_assertions(procedures, ["primary_assertions", "secondary_assertions"]))
    errors.extend(_assertions(scenarios, ["primary_assertions", "secondary_assertions"]))

    for row in tags + risks + risk_keywords + procedures + mappings + templates + scenarios + pairs:
        status = row.get("review_status")
        if status and status not in VALID_REVIEW_STATUS:
            errors.append(f"invalid review_status {status}")

    for row in risks:
        invalid_tags = set(parse_multi(row.get("risk_tags"))) - tag_codes
        if invalid_tags:
            errors.append(f"{row['risk_id']}: unknown risk_tags {sorted(invalid_tags)}")
    for row in risk_keywords:
        if row["risk_id"] not in risk_ids:
            errors.append(f"risk keywords: missing risk {row['risk_id']}")
        if not parse_multi(row["keywords_ko"]):
            errors.append(f"risk keywords: no keywords for {row['risk_id']}")
    for row in procedures:
        invalid_tags = set(parse_multi(row.get("applicable_risk_tags"))) - tag_codes
        if invalid_tags:
            errors.append(f"{row['procedure_id']}: unknown applicable_risk_tags {sorted(invalid_tags)}")
    for row in mappings:
        if row["risk_id"] not in risk_ids:
            errors.append(f"{row['mapping_id']}: missing risk {row['risk_id']}")
        if row["procedure_id"] not in procedure_ids:
            errors.append(f"{row['mapping_id']}: missing procedure {row['procedure_id']}")
        grade = int(row["relevance_grade"])
        if row["relation_label"] != GRADE_TO_LABEL[grade]:
            errors.append(f"{row['mapping_id']}: grade/label mismatch")
    for row in templates:
        missing_risks = set(parse_multi(row["base_risk_ids"])) - risk_ids
        if missing_risks:
            errors.append(f"{row['template_id']}: missing base risks {sorted(missing_risks)}")
    for row in scenarios:
        if row["template_id"] not in template_ids:
            errors.append(f"{row['scenario_id']}: missing template {row['template_id']}")
    for row in pairs:
        if row["scenario_id"] not in scenario_ids:
            errors.append(f"{row['pair_id']}: missing scenario {row['scenario_id']}")
        if row["procedure_id"] not in procedure_ids:
            errors.append(f"{row['pair_id']}: missing procedure {row['procedure_id']}")
        if row["relation_label"] not in VALID_RELATION_LABELS:
            errors.append(f"{row['pair_id']}: invalid relation_label")
        if row["relation_label"] == "core" and row["primary_assertion_overlap"] == "0":
            errors.append(f"{row['pair_id']}: core without primary assertion overlap")
        if row["relation_label"] == "core" and row["account_match"] != "1":
            errors.append(f"{row['pair_id']}: core without account match")

    pair_keys = Counter((row["scenario_id"], row["procedure_id"]) for row in pairs)
    if any(count > 1 for count in pair_keys.values()):
        errors.append("duplicate scenario_id/procedure_id pair")

    by_scenario = Counter(row["scenario_id"] for row in pairs)
    bad_counts = [sid for sid, count in by_scenario.items() if count != 5]
    if bad_counts:
        errors.append(f"scenarios without exactly 5 pairs: {bad_counts[:5]}")

    split_templates: dict[str, set[str]] = defaultdict(set)
    for row in scenarios:
        split_templates[row["template_id"]].add(row["split"])
    leaked = [tid for tid, splits in split_templates.items() if len(splits) > 1]
    if leaked:
        errors.append(f"template split leakage: {leaked[:5]}")

    texts = Counter(row["scenario_text_ko"].strip() for row in scenarios)
    duplicated_texts = [text for text, count in texts.items() if text and count > 1]
    if duplicated_texts:
        errors.append(f"duplicate scenario_text_ko: {duplicated_texts[:3]}")

    for row in mappings + risks + procedures:
        ref = row.get("source_reference", "")
        if re.search(r"문단\s*\d+|ISA\s*\d+\.\d+", ref):
            warnings.append(f"possible unsupported paragraph reference: {ref}")

    if expected_scenarios is not None and len(scenarios) != expected_scenarios:
        errors.append(f"expected {expected_scenarios} scenarios, got {len(scenarios)}")
    if expected_pairs is not None and len(pairs) != expected_pairs:
        errors.append(f"expected {expected_pairs} pairs, got {len(pairs)}")
    if any(not row.get("rationale_ko", "").strip() for row in pairs):
        warnings.append("empty rationale found in generated pairs")

    return errors, warnings
