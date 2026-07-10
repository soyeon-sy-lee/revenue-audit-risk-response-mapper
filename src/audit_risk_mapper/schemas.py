TAG_COLUMNS = [
    "tag_id", "tag_category", "tag_code", "tag_name_ko", "description_ko",
    "allowed_for", "conflicts_with", "source_level", "review_status",
]

RISK_COLUMNS = [
    "risk_id", "risk_name_ko", "account_cycle", "risk_description_ko",
    "misstatement_hypothesis_ko", "primary_assertions", "secondary_assertions",
    "risk_tags", "fraud_risk_indicator", "information_required",
    "applicable_business_context", "limitations", "source_reference",
    "source_level", "review_status",
]

PROCEDURE_COLUMNS = [
    "procedure_id", "procedure_name_ko", "audit_objective_ko",
    "procedure_description_ko", "related_accounts", "primary_assertions",
    "secondary_assertions", "applicable_risk_tags", "procedure_type", "timing",
    "required_conditions", "exclusion_conditions", "evidence_examples",
    "limitations", "source_reference", "source_level", "review_status",
]

MAPPING_COLUMNS = [
    "mapping_id", "risk_id", "procedure_id", "relevance_grade", "relation_label",
    "matched_assertions", "required_conditions", "rationale_ko", "gap_if_omitted_ko",
    "contraindication_ko", "source_reference", "source_level", "review_status",
]

TEMPLATE_COLUMNS = [
    "template_id", "template_name_ko", "base_risk_ids", "account_cycle", "fact_pattern",
    "variable_slots", "possible_assertions", "required_information",
    "allowed_procedure_relations", "prohibited_combinations", "source_level", "review_status",
]

SCENARIO_COLUMNS = [
    "scenario_id", "template_id", "scenario_text_ko", "account_cycle", "risk_ids", "risk_tags",
    "facts_available", "evidence_available", "control_context", "fraud_risk_indicator",
    "primary_assertions", "secondary_assertions", "information_missing",
    "expected_core_procedures", "expected_conditional_procedures", "generation_seed",
    "synthetic", "source_level", "review_status", "split",
]

PAIR_COLUMNS = [
    "pair_id", "scenario_id", "template_id", "procedure_id", "account_match",
    "primary_assertion_overlap", "secondary_assertion_overlap", "risk_tag_overlap", "evidence_match",
    "required_conditions_met", "missing_required_conditions", "exclusion_condition_hit",
    "timing_match", "fraud_indicator_match", "relevance_grade", "relation_label", "rationale_ko",
    "generation_seed", "synthetic", "review_status", "split",
]

VALID_ASSERTIONS = {
    "occurrence", "completeness", "accuracy", "cutoff", "classification",
    "presentation", "existence", "rights_and_obligations", "valuation",
}

VALID_RELATION_LABELS = {"core", "supporting", "conditional", "weak_match", "not_applicable"}
GRADE_TO_LABEL = {3: "core", 2: "supporting", 1: "conditional", 0: "weak_match", -1: "not_applicable"}
VALID_REVIEW_STATUS = {"ai_generated_unreviewed", "self_reviewed", "cpa_reviewed", "expert_validated"}
VALID_SOURCE_LEVEL = {
    "standard_direct", "standard_derived", "public_education_derived",
    "educational_inference", "synthetic_variant",
}
