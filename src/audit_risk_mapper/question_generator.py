from __future__ import annotations

from .data_io import parse_multi, read_csv

QUESTION_TEXT = {
    "cutoff_evidence": "출고일, 인수일, 수익인식일을 비교할 자료가 있습니까?",
    "customer_acceptance": "고객 검수 또는 인수 조건이 존재하며 완료일을 확인할 수 있습니까?",
    "post_period_returns": "기말 후 반품, 취소 또는 대변전표가 증가했습니까?",
    "cash_collection": "후속 현금회수 내역이 매출채권 증가와 일관됩니까?",
    "contract_terms": "계약서에 비표준 조건, 반품권 또는 취소권이 포함되어 있습니까?",
    "manual_journal": "수기 매출전표나 비경상 분개가 포함되어 있습니까?",
    "related_party": "특수관계자 여부와 거래조건을 확인했습니까?",
}


def questions_for_risks(seed_dir, risk_ids: list[str]) -> list[str]:
    risks = {row["risk_id"]: row for row in read_csv(seed_dir / "risk_signal_library.csv")}
    questions: list[str] = []
    for risk_id in risk_ids:
        for key in parse_multi(risks[risk_id]["information_required"]):
            question = QUESTION_TEXT.get(key)
            if question and question not in questions:
                questions.append(question)
    return questions
