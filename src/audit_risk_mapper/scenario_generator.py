from __future__ import annotations

from collections import Counter
from pathlib import Path
import random

from .data_io import join_multi, parse_multi, read_csv, write_csv, write_json
from .schemas import PAIR_COLUMNS, SCENARIO_COLUMNS, GRADE_TO_LABEL

SPLIT_BY_TEMPLATE_INDEX = {0: "train", 1: "train", 2: "train", 3: "validation", 4: "test"}


def _split_for_template(template_id: str) -> str:
    number = int(template_id.replace("TPL", ""))
    return SPLIT_BY_TEMPLATE_INDEX[number % 5]


def _make_text(template: dict[str, str], risk_names: list[str], rng: random.Random, index: int) -> str:
    modifiers = [
        "기말 전후 거래 기록과 증빙의 시점 차이가 관찰되었습니다",
        "관련 증빙 일부가 누락되어 추가 확인이 필요합니다",
        "후속 회수와 반품 자료를 함께 대조할 필요가 있습니다",
        "특정 거래처와 비표준 조건이 함께 나타났습니다",
    ]
    return f"{template['fact_pattern']} 주요 위험징후는 {', '.join(risk_names)}입니다. 사례 번호 {index + 1:03d}: {modifiers[(index + rng.randrange(0, 4)) % 4]}."


def generate_dataset(root: Path, seed: int = 42, scenario_count: int = 100, pairs_per_scenario: int = 5) -> dict:
    rng = random.Random(seed)
    seed_dir = root / "data" / "seed"
    generated_dir = root / "data" / "generated"
    risks = {row["risk_id"]: row for row in read_csv(seed_dir / "risk_signal_library.csv")}
    procedures = {row["procedure_id"]: row for row in read_csv(seed_dir / "procedure_library.csv")}
    mappings = read_csv(seed_dir / "risk_procedure_mapping.csv")
    templates = read_csv(seed_dir / "scenario_templates.csv")
    mapping_by_risk = {}
    for row in mappings:
        mapping_by_risk.setdefault(row["risk_id"], []).append(row)

    scenarios: list[dict[str, object]] = []
    pairs: list[dict[str, object]] = []
    for i in range(scenario_count):
        template = templates[i % len(templates)]
        risk_ids = parse_multi(template["base_risk_ids"])
        selected_risks = [risks[risk_id] for risk_id in risk_ids]
        primary_assertions = []
        secondary_assertions = []
        risk_tags = []
        information_required = []
        expected_core = []
        expected_conditional = []
        for risk in selected_risks:
            primary_assertions.extend(parse_multi(risk["primary_assertions"]))
            secondary_assertions.extend(parse_multi(risk["secondary_assertions"]))
            risk_tags.extend(parse_multi(risk["risk_tags"]))
            information_required.extend(parse_multi(risk["information_required"]))
            for mapping in mapping_by_risk.get(risk["risk_id"], []):
                if mapping["relation_label"] in {"core", "supporting"}:
                    expected_core.append(mapping["procedure_id"])
                elif mapping["relation_label"] == "conditional":
                    expected_conditional.append(mapping["procedure_id"])
        scenario_id = f"SCN{seed:03d}{i + 1:05d}"
        split = _split_for_template(template["template_id"])
        evidence = ["contract", "invoice", "shipping_document"]
        if i % 3 == 0:
            evidence.append("customer_acceptance")
        if i % 4 == 0:
            evidence.append("cash_receipt")
        scenario = {
            "scenario_id": scenario_id,
            "template_id": template["template_id"],
            "scenario_text_ko": _make_text(template, [r["risk_name_ko"] for r in selected_risks], rng, i),
            "account_cycle": template["account_cycle"],
            "risk_ids": join_multi(risk_ids),
            "risk_tags": join_multi(risk_tags),
            "facts_available": template["variable_slots"],
            "evidence_available": join_multi(evidence),
            "control_context": "controls_not_relied" if i % 2 else "controls_reliance_considered",
            "fraud_risk_indicator": "true" if any(r["fraud_risk_indicator"] == "true" for r in selected_risks) else "false",
            "primary_assertions": join_multi(primary_assertions),
            "secondary_assertions": join_multi(secondary_assertions),
            "information_missing": join_multi(information_required[:3]),
            "expected_core_procedures": join_multi(expected_core),
            "expected_conditional_procedures": join_multi(expected_conditional),
            "generation_seed": seed,
            "synthetic": "true",
            "source_level": "synthetic_variant",
            "review_status": "ai_generated_unreviewed",
            "split": split,
        }
        scenarios.append(scenario)

        relevant = []
        for risk_id in risk_ids:
            relevant.extend(mapping_by_risk.get(risk_id, []))
        relevant = sorted(relevant, key=lambda row: -int(row["relevance_grade"]))
        selected_mappings = []
        used = set()
        for relation in ["core", "supporting", "conditional", "weak_match", "not_applicable"]:
            candidates = [m for m in relevant if m["relation_label"] == relation and m["procedure_id"] not in used]
            if candidates:
                chosen = candidates[0]
                selected_mappings.append(chosen)
                used.add(chosen["procedure_id"])
        fallback = list(procedures)
        rng.shuffle(fallback)
        while len(selected_mappings) < pairs_per_scenario:
            procedure_id = fallback.pop()
            if procedure_id in used:
                continue
            selected_mappings.append({
                "procedure_id": procedure_id,
                "relevance_grade": "0",
                "relation_label": "weak_match",
                "matched_assertions": "",
                "required_conditions": "",
                "rationale_ko": "직접 대응관계가 약한 비교 후보입니다.",
            })
            used.add(procedure_id)

        scenario_assertions = set(parse_multi(scenario["primary_assertions"]))
        scenario_secondary = set(parse_multi(scenario["secondary_assertions"]))
        scenario_tags = set(parse_multi(scenario["risk_tags"]))
        for j, mapping in enumerate(selected_mappings[:pairs_per_scenario], start=1):
            procedure = procedures[mapping["procedure_id"]]
            proc_primary = set(parse_multi(procedure["primary_assertions"]))
            proc_secondary = set(parse_multi(procedure["secondary_assertions"]))
            proc_tags = set(parse_multi(procedure["applicable_risk_tags"]))
            required = set(parse_multi(procedure["required_conditions"]))
            evidence_available = set(parse_multi(scenario["evidence_available"]))
            missing_required = sorted(required - evidence_available)
            exclusion_hit = "manual_entry" in scenario_tags and "automated_only" in parse_multi(procedure["exclusion_conditions"])
            grade = int(mapping["relevance_grade"])
            label = mapping["relation_label"]
            account_match = "1" if scenario["account_cycle"] in parse_multi(procedure["related_accounts"]) else "0"
            if account_match == "0" and label == "core":
                grade = 0
                label = "weak_match"
            if exclusion_hit and grade > 0:
                grade = 0
                label = GRADE_TO_LABEL[grade]
            if missing_required and label == "core":
                grade = 1
                label = "conditional"
            pairs.append({
                "pair_id": f"PAIR{seed:03d}{i + 1:05d}{j:02d}",
                "scenario_id": scenario_id,
                "template_id": template["template_id"],
                "procedure_id": procedure["procedure_id"],
                "account_match": account_match,
                "primary_assertion_overlap": len(scenario_assertions & proc_primary),
                "secondary_assertion_overlap": len(scenario_secondary & proc_secondary),
                "risk_tag_overlap": len(scenario_tags & proc_tags),
                "evidence_match": len(evidence_available & set(parse_multi(procedure["evidence_examples"]))),
                "required_conditions_met": "false" if missing_required else "true",
                "missing_required_conditions": join_multi(missing_required),
                "exclusion_condition_hit": "true" if exclusion_hit else "false",
                "timing_match": "1" if procedure["timing"] in {"interim_and_year_end", "year_end"} else "0",
                "fraud_indicator_match": "1" if scenario["fraud_risk_indicator"] == "true" and "manual_entry" in proc_tags else "0",
                "relevance_grade": grade,
                "relation_label": label,
                "rationale_ko": mapping.get("rationale_ko") or "태그와 주장의 일부가 겹치는 비교 후보입니다.",
                "generation_seed": seed,
                "synthetic": "true",
                "review_status": "ai_generated_unreviewed",
                "split": split,
            })

    write_csv(generated_dir / "scenarios.csv", scenarios, SCENARIO_COLUMNS)
    write_csv(generated_dir / "scenario_procedure_pairs.csv", pairs, PAIR_COLUMNS)
    sample = pairs[: min(200, len(pairs))]
    write_csv(generated_dir / "manual_review_sample.csv", sample, PAIR_COLUMNS)
    report = {
        "mode": "smoke" if scenario_count <= 100 else "custom",
        "seed": seed,
        "scenario_count": len(scenarios),
        "pair_count": len(pairs),
        "pairs_per_scenario": pairs_per_scenario,
        "class_distribution": dict(Counter(row["relation_label"] for row in pairs)),
        "review_status": "ai_generated_unreviewed",
        "limitations": "Synthetic educational data; not expert validated.",
    }
    write_json(generated_dir / "generation_report.json", report)
    return report
