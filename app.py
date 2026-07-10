from pathlib import Path

import streamlit as st

from audit_risk_mapper.data_io import parse_multi, read_csv
from audit_risk_mapper.question_generator import questions_for_risks
from audit_risk_mapper.recommender import recommend_for_scenario

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Revenue Audit Risk-Response Mapper", layout="wide")
st.title("매출 감사위험 대응 매핑 검토 도구")
st.caption("교육용 의사결정 지원 도구이며 감사인의 전문적 판단을 대체하지 않습니다.")

page = st.sidebar.radio("페이지", ["프로젝트 안내", "위험 사례 입력", "데이터 요약"])

if page == "프로젝트 안내":
    st.subheader("목적")
    st.write("위험징후에서 가능한 왜곡 양상, 관련 주장, 추가 질문, 감사절차 후보로 이어지는 연결을 학습합니다.")
    st.warning("현재 데이터는 ai_generated_unreviewed 상태의 합성 교육 데이터입니다. 감사의견, 중요성, 표본크기 또는 감사 결론을 산출하지 않습니다.")
elif page == "위험 사례 입력":
    scenarios_path = ROOT / "data" / "generated" / "scenarios.csv"
    if not scenarios_path.exists():
        st.info("먼저 `python -m scripts.generate_dataset --mode smoke --seed 42 --scenario-count 100 --pairs-per-scenario 5`를 실행하세요.")
    else:
        scenarios = read_csv(scenarios_path)
        selected = st.selectbox("합성 사례", scenarios, format_func=lambda row: f"{row['scenario_id']} - {row['scenario_text_ko'][:60]}")
        st.write(selected["scenario_text_ko"])
        st.write("관련 주장:", ", ".join(parse_multi(selected["primary_assertions"])))
        questions = questions_for_risks(ROOT / "data" / "seed", parse_multi(selected["risk_ids"]))
        st.subheader("추가 질문")
        for question in questions:
            st.write(f"- {question}")
        st.subheader("감사절차 후보")
        for item in recommend_for_scenario(ROOT, selected["scenario_id"]):
            with st.expander(f"{item['procedure_id']} · {item['procedure_name']} · {item['fit_score']}"):
                st.write(item["audit_objective"])
                st.write(item["recommendation_reason"])
                if item["unmet_conditions"]:
                    st.warning("미충족 조건: " + ", ".join(item["unmet_conditions"]))
else:
    report_path = ROOT / "data" / "generated" / "generation_report.json"
    if report_path.exists():
        st.json(report_path.read_text(encoding="utf-8"))
    else:
        st.info("생성된 데이터가 아직 없습니다.")
