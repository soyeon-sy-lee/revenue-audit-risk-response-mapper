from __future__ import annotations

from html import escape
import json
from pathlib import Path

import streamlit as st

from audit_risk_mapper.coverage_checker import (
    ASSERTION_LABELS,
    detect_risks_from_text,
    review_risk_coverage,
)
from audit_risk_mapper.data_io import parse_multi, read_csv
from audit_risk_mapper.feedback_store import save_feedback
from audit_risk_mapper.question_generator import questions_for_risks
from audit_risk_mapper.recommender import recommend_for_scenario

ROOT = Path(__file__).resolve().parent
SEED_DIR = ROOT / "data" / "seed"
FEEDBACK_DB = ROOT / "data" / "feedback" / "feedback.sqlite3"

EXAMPLES = {
    "cutoff": "결산일 직전 매출이 집중되었고 일부 계약에는 고객 검수조건이 포함되어 있습니다. 기말 후 반품 및 대변전표 증가 여부도 확인이 필요합니다.",
    "receivable": "장기 미회수 매출채권이 증가했고 후속 현금회수가 부진합니다. 일부 신규 거래처의 큰 채권 잔액도 포함되어 있습니다.",
}
RELATION_LABELS = {
    "core": "core",
    "supporting": "support",
    "conditional": "cond.",
    "weak_match": "weak",
    "not_applicable": "n/a",
}
FEEDBACK_OPTIONS = {
    "도움됨": "helpful",
    "낮은 우선순위": "relevant_but_lower_priority",
    "사례에 부적합": "not_applicable_to_case",
    "정보 필요": "needs_more_information",
}


@st.cache_data
def load_seed() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    return (
        read_csv(SEED_DIR / "risk_signal_library.csv"),
        read_csv(SEED_DIR / "procedure_library.csv"),
    )


def selected_ids(prefix: str, rows: list[dict[str, str]], id_column: str) -> list[str]:
    return [row[id_column] for row in rows if st.session_state.get(f"{prefix}_{row[id_column]}", False)]


def apply_detected_risks(force: bool = False) -> None:
    if not force and not st.session_state.get("auto_detect_enabled", True):
        return
    detected = set(detect_risks_from_text(SEED_DIR, st.session_state.get("risk_narrative", "")))
    for row in read_csv(SEED_DIR / "risk_signal_library.csv"):
        st.session_state[f"risk_{row['risk_id']}"] = row["risk_id"] in detected


def load_example(name: str) -> None:
    st.session_state["risk_narrative"] = EXAMPLES[name]
    apply_detected_risks(force=True)
    st.session_state["show_review"] = True


def safe_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f'<p class="help-text">{escape(empty_text)}</p>'
    return '<ul class="output-list">' + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def render_review_html(result: dict[str, object], procedure_by_id: dict[str, dict[str, str]]) -> str:
    target_assertions = result["target_assertions"]
    coverage_rows = []
    for assertion in target_assertions:
        procedure_ids = result["assertion_procedures"][assertion]
        covered = bool(procedure_ids)
        procedure_names = ", ".join(procedure_by_id[item]["procedure_name_ko"] for item in procedure_ids)
        coverage_rows.append(
            f"""
            <div class="coverage-row">
              <strong>{escape(ASSERTION_LABELS.get(assertion, assertion))}</strong>
              <div class="coverage-track"><div class="coverage-fill {'missing' if not covered else ''}" style="width:{100 if covered else 8}%"></div></div>
              <span>{'대응됨' if covered else '누락 가능'}</span>
            </div>
            {f'<p class="coverage-detail">{escape(procedure_names)}</p>' if procedure_names else ''}
            """
        )

    missing_core = result["missing_core_procedures"]
    weak = result["weak_selections"]
    warning_count = len(missing_core) + len(weak)
    pills = []
    for item in missing_core:
        pills.append(f'<span class="pill warn">핵심 후보 누락 · {escape(item["procedure_name"])}</span>')
    for item in weak:
        pills.append(f'<span class="pill danger">직접 연결 약함 · {escape(item["procedure_name"])}</span>')
    if not pills:
        pills.append('<span class="pill">즉시 표시할 위험·절차 경고 없음</span>')

    recommendations = result["recommendations"][:5]
    procedure_html = []
    for index, item in enumerate(recommendations, start=1):
        selected_badge = '<span class="pill">계획에 선택됨</span>' if item["selected"] else ""
        procedure_html.append(
            f"""
            <div class="procedure-item">
              <div class="procedure-topline">
                <strong>{index}. {escape(str(item['procedure_name']))}</strong>
                <span class="learned-score">{escape(RELATION_LABELS[str(item['relation_label'])])}</span>
              </div>
              <span>{escape(str(item['description']))}</span>
              <span>연결 위험 · {escape(', '.join(item['matched_risk_names']))}</span>
              {selected_badge}
            </div>
            """
        )

    assertion_pills = "".join(
        f'<span class="pill">{escape(ASSERTION_LABELS.get(item, item))}</span>' for item in target_assertions
    ) or '<span class="pill warn">선택된 위험 없음</span>'

    return f"""
      <div class="output-grid">
        <div class="output-card">
          <h3>검토 요약</h3>
          <div class="output-card-content">
            <div class="indicator-grid">
              <div class="indicator"><span>주장 커버리지</span><strong>{result['coverage_ratio']:.0%}</strong><small>선택 절차가 관련 주장을 다루는 비율</small></div>
              <div class="indicator"><span>위험·절차 경고</span><strong>{warning_count}</strong><small>점수와 분리한 직접 대응관계 점검</small></div>
            </div>
            <div class="pill-list">{assertion_pills}</div>
          </div>
        </div>
        <div class="output-card">
          <h3>주장별 대응</h3>
          <div class="output-card-content">{''.join(coverage_rows) or '<p class="help-text">선택된 위험의 관련 주장이 없습니다.</p>'}</div>
        </div>
        <div class="output-card">
          <h3>위험·절차 경고</h3>
          <div class="output-card-content"><div class="pill-list">{''.join(pills)}</div></div>
        </div>
        <div class="output-card">
          <h3>감사절차 후보</h3>
          <div class="output-card-content">{''.join(procedure_html) or '<p class="help-text">연결된 절차 후보가 없습니다.</p>'}</div>
        </div>
      </div>
    """


st.set_page_config(
    page_title="Revenue Audit Risk-Response Mapper",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {
        --ink:#17211b; --muted:#5f6d66; --line:#d8e0da; --paper:#f7f8f4;
        --panel:#ffffff; --green:#2e6f55; --mint:#dceee5; --blue:#305f86;
        --gold:#a5682a; --amber:#f3e5ca; --red:#9c4a43; --rose:#f2dfdd;
        --slate:#40505c; --shadow:0 18px 40px rgba(24,37,30,.10);
      }
      html { scroll-behavior:smooth; }
      .stApp { color:var(--ink); background:var(--paper); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR","Segoe UI",sans-serif; }
      [data-testid="stHeader"], [data-testid="stSidebar"], #MainMenu, footer { display:none !important; }
      .block-container { max-width:1180px; padding:0 1.15rem 3rem; }
      h1,h2,h3 { color:var(--ink); letter-spacing:-.025em; }
      p { line-height:1.55; }

      .topbar { position:sticky; top:0; z-index:50; display:flex; align-items:center; justify-content:space-between; gap:20px; min-height:64px; margin:0 -1.15rem 0; padding:12px 1.15rem; background:rgba(247,248,244,.94); border-bottom:1px solid var(--line); backdrop-filter:blur(14px); }
      .brand { display:flex; align-items:center; gap:12px; min-width:220px; font-weight:800; }
      .brand-mark { display:grid; place-items:center; width:36px; height:36px; color:#fff; background:var(--green); border-radius:8px; font-size:18px; font-weight:900; }
      .topnav { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:6px; }
      .topnav span { padding:8px 10px; border-radius:7px; color:var(--muted); font-size:14px; font-weight:700; }

      .section-head { display:grid; grid-template-columns:minmax(0,.85fr) minmax(280px,1.15fr); gap:32px; align-items:end; padding:44px 0 26px; }
      .section-head h1 { margin:0; font-size:clamp(34px,5vw,58px); line-height:1; }
      .section-head p { margin:0; color:var(--muted); font-size:16px; }
      .eyebrow { margin:0 0 10px; color:var(--green); font-size:13px; font-weight:800; text-transform:uppercase; }

      div[data-testid="stVerticalBlockBorderWrapper"] { border:1px solid var(--line); border-radius:10px; background:var(--panel); box-shadow:var(--shadow); overflow:hidden; }
      div[data-testid="stVerticalBlockBorderWrapper"] > div { padding:0; }
      .workbench-header { display:flex; align-items:center; justify-content:space-between; gap:16px; margin:-1rem -1rem .8rem; padding:12px 16px; background:#eef2ed; border-bottom:1px solid var(--line); font-size:13px; font-weight:900; }
      .status { display:inline-flex; align-items:center; min-height:26px; padding:4px 8px; border-radius:999px; background:var(--amber); color:var(--gold); font-size:11px; font-weight:900; text-transform:uppercase; }
      .status.ok { background:var(--mint); color:var(--green); }
      .field-note { margin:-.35rem 0 .4rem; padding:10px 12px; border:1px solid var(--line); border-radius:8px; background:#f4f7f1; color:var(--muted); font-size:13px; }
      .field-note strong { color:var(--green); }

      [data-testid="stTextArea"] label, [data-testid="stSelectbox"] label { color:var(--ink) !important; font-size:14px !important; font-weight:900 !important; }
      [data-testid="stTextArea"] textarea, [data-baseweb="select"] > div { border-color:var(--line) !important; border-radius:8px !important; background:#fff !important; }
      [data-testid="stCheckbox"] { min-height:42px; padding:8px 10px; border:1px solid var(--line); border-radius:8px; background:#fbfcf9; }
      [data-testid="stCheckbox"]:has(input:checked) { border-color:#9bc3ad; background:var(--mint); }
      [data-testid="stCheckbox"] label p { color:#34443c; font-size:13px; font-weight:700; }
      [data-testid="stCheckbox"] [data-testid="stMarkdownContainer"] { line-height:1.25; }
      [data-testid="stToggle"] label p { color:#34443c; font-size:13px; font-weight:800; }

      .stButton > button { min-height:42px; border:1px solid var(--line); border-radius:7px; background:#fff; color:var(--ink); font-weight:800; box-shadow:none; }
      .stButton > button:hover { border-color:#9bc3ad; background:var(--mint); color:var(--green); }
      .stButton > button[kind="primary"] { border-color:var(--green); background:var(--green); color:#fff; }
      .stButton > button[kind="primary"]:hover { background:#255d47; color:#fff; }

      .output-grid { display:grid; gap:14px; }
      .output-card { border:1px solid var(--line); border-radius:8px; background:#fbfcf9; overflow:hidden; }
      .output-card h3 { margin:0; padding:12px 14px; border-bottom:1px solid var(--line); background:#f4f7f1; font-size:15px; }
      .output-card-content { padding:14px; }
      .indicator-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
      .indicator { padding:12px; border:1px solid var(--line); border-radius:8px; background:#fff; }
      .indicator span { display:block; color:var(--muted); font-size:12px; font-weight:900; }
      .indicator strong { display:block; margin-top:5px; font-size:22px; line-height:1; }
      .indicator small { display:block; margin-top:7px; color:var(--muted); font-size:12px; }
      .coverage-row { display:grid; grid-template-columns:82px minmax(0,1fr) 72px; gap:10px; align-items:center; margin:9px 0; font-size:13px; }
      .coverage-track { height:12px; border-radius:99px; background:#e9eee9; overflow:hidden; }
      .coverage-fill { height:100%; border-radius:99px; background:var(--green); }
      .coverage-fill.missing { background:var(--red); }
      .coverage-detail { margin:-5px 0 9px 92px; color:var(--muted); font-size:11px; }
      .pill-list { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
      .pill { display:inline-flex; align-items:center; min-height:28px; padding:4px 9px; border-radius:7px; background:var(--mint); color:var(--green); font-size:12px; font-weight:900; }
      .pill.warn { background:var(--amber); color:var(--gold); }
      .pill.danger { background:var(--rose); color:var(--red); }
      .procedure-item { display:grid; gap:5px; padding:11px 0; border-bottom:1px solid var(--line); }
      .procedure-item:last-child { border-bottom:0; }
      .procedure-item strong { font-size:14px; }
      .procedure-item span { color:var(--muted); font-size:13px; }
      .procedure-topline { display:flex; align-items:center; justify-content:space-between; gap:10px; }
      .procedure-topline .learned-score { color:var(--blue); font-size:12px; font-weight:900; }
      .help-text { margin:0; color:var(--muted); font-size:13px; }
      .output-list { margin:0; padding-left:18px; color:#35443c; }
      .output-list li { margin:8px 0; }

      [data-testid="stExpander"] { border:1px solid var(--line) !important; border-radius:0 !important; background:#eef2ed; }
      [data-testid="stExpander"] summary { padding:16px 18px; font-weight:900; }
      .hero-inner { display:grid; grid-template-columns:minmax(0,1.02fr) minmax(320px,.98fr); gap:48px; align-items:center; padding:34px 0; }
      .hero-title { margin:0; font-size:clamp(42px,7vw,76px); line-height:.98; letter-spacing:-.035em; }
      .subtitle { color:var(--muted); font-size:19px; }
      .hero-proof { border:1px solid var(--line); border-radius:10px; background:var(--panel); box-shadow:var(--shadow); overflow:hidden; }
      .mock-header { display:flex; justify-content:space-between; padding:12px 16px; background:#eef2ed; border-bottom:1px solid var(--line); color:var(--muted); font-size:12px; font-weight:800; }
      .mock-body { padding:16px; }
      .case-text { margin:0 0 12px; color:var(--muted); font-size:14px; }
      .recommendation { display:grid; grid-template-columns:40px minmax(0,1fr) auto; gap:10px; align-items:center; padding:12px 0; border-top:1px solid var(--line); }
      .rank { display:grid; place-items:center; width:32px; height:32px; border-radius:8px; background:var(--mint); color:var(--green); font-weight:900; }
      .recommendation h3 { margin:0; font-size:14px; }
      .recommendation p { margin:3px 0 0; color:var(--muted); font-size:12px; }
      .score { color:var(--blue); font-size:12px; }
      .metrics-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:18px 0 30px; }
      .metric { padding:18px; border:1px solid var(--line); border-radius:8px; background:#fff; }
      .metric span,.metric small { display:block; color:var(--muted); font-size:12px; font-weight:800; }
      .metric strong { display:block; margin:8px 0 5px; font-size:28px; }
      .pipeline { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin:18px 0 30px; }
      .pipe-step { padding:16px; border:1px solid var(--line); border-radius:8px; background:#fff; }
      .step-no { display:grid; place-items:center; width:28px; height:28px; border-radius:7px; background:var(--mint); color:var(--green); font-weight:900; }
      .pipe-step h3 { margin:12px 0 5px; font-size:15px; }
      .pipe-step p { margin:0; color:var(--muted); font-size:12px; }
      .limits { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; padding:22px 0; }
      .limit { padding:18px; border:1px solid var(--line); border-radius:8px; background:#fff; }
      .limit h3 { margin:0 0 8px; font-size:16px; }
      .limit p { margin:0; color:var(--muted); font-size:14px; }
      .footer-bar { display:flex; justify-content:space-between; gap:20px; flex-wrap:wrap; margin:30px -1.15rem -3rem; padding:28px 1.15rem; color:var(--muted); background:#eef2ed; font-size:14px; }

      @media(max-width:900px) {
        .section-head,.hero-inner { grid-template-columns:1fr; }
        .metrics-grid,.limits { grid-template-columns:1fr 1fr; }
        .pipeline { grid-template-columns:1fr 1fr; }
      }
      @media(max-width:620px) {
        .topbar { align-items:flex-start; flex-direction:column; }
        .section-head { padding-top:30px; }
        .metrics-grid,.limits,.pipeline,.indicator-grid { grid-template-columns:1fr; }
        .coverage-row { grid-template-columns:1fr; }
        .coverage-detail { margin-left:0; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

risks, procedures = load_seed()
risk_by_id = {row["risk_id"]: row for row in risks}
procedure_by_id = {row["procedure_id"]: row for row in procedures}

st.markdown(
    """
    <header class="topbar">
      <div class="brand"><span class="brand-mark">R</span><span>Risk-Response Mapper</span></div>
      <nav class="topnav"><span>커버리지 점검</span><span>프로젝트 설명</span><span>한계</span></nav>
    </header>
    <section class="section-head">
      <div><p class="eyebrow">Educational audit analytics prototype</p><h1>커버리지 점검 도구</h1></div>
      <p>위험상황, 검증대상, 수행하려는 절차를 입력하면 주장별 대응 여부와 누락 가능성이 있는 절차를 실제 Seed 지식베이스와 Python 규칙으로 검토합니다.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

if "risk_narrative" not in st.session_state:
    st.session_state["risk_narrative"] = EXAMPLES["cutoff"]
if "auto_detect_enabled" not in st.session_state:
    st.session_state["auto_detect_enabled"] = True
if "risk_widgets_initialized" not in st.session_state:
    apply_detected_risks(force=True)
    st.session_state["risk_widgets_initialized"] = True
if "procedure_widgets_initialized" not in st.session_state:
    for procedure in procedures:
        st.session_state[f"proc_{procedure['procedure_id']}"] = procedure["procedure_id"] == "PROC001"
    st.session_state["procedure_widgets_initialized"] = True
if "show_review" not in st.session_state:
    st.session_state["show_review"] = False

input_col, output_col = st.columns(2, gap="large")

with input_col:
    with st.container(border=True):
        st.markdown('<div class="workbench-header"><span>입력창</span><span class="status">education only</span></div>', unsafe_allow_html=True)
        st.text_area("위험상황", key="risk_narrative", height=126, on_change=apply_detected_risks)
        st.caption("자유문장과 아래 체크 항목을 함께 사용합니다.")
        st.toggle("기본 위험징후 자동 체크 사용", key="auto_detect_enabled")
        detected_risk_ids = detect_risks_from_text(SEED_DIR, st.session_state["risk_narrative"])
        detected_risk_names = [risk_by_id[risk_id]["risk_name_ko"] for risk_id in detected_risk_ids]
        if st.session_state["auto_detect_enabled"]:
            auto_suggestion = ", ".join(detected_risk_names) if detected_risk_names else "탐지된 위험징후 없음"
            st.markdown(
                f'<div class="field-note"><strong>자동 제안:</strong> {escape(auto_suggestion)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="field-note"><strong>자동 제안:</strong> 사용 안 함<br>아래에서 위험징후를 직접 선택할 수 있습니다.</div>',
                unsafe_allow_html=True,
            )
        account_cycle = st.selectbox(
            "검증대상",
            ["revenue", "accounts_receivable", "both"],
            format_func=lambda value: {"revenue": "매출 거래", "accounts_receivable": "매출채권 잔액", "both": "매출 및 매출채권"}[value],
        )

        st.markdown("**위험징후**")
        risk_columns = st.columns(2, gap="small")
        for index, risk in enumerate(risks):
            with risk_columns[index % 2]:
                st.checkbox(risk["risk_name_ko"], key=f"risk_{risk['risk_id']}")

        st.markdown("**수행하려는 절차**")
        procedure_columns = st.columns(2, gap="small")
        for index, procedure in enumerate(procedures):
            with procedure_columns[index % 2]:
                st.checkbox(procedure["procedure_name_ko"], key=f"proc_{procedure['procedure_id']}")

        action_one, action_two = st.columns(2)
        with action_one:
            if st.button("커버리지 검토", type="primary", use_container_width=True):
                st.session_state["show_review"] = True
        with action_two:
            st.button("텍스트로 위험징후 체크", on_click=apply_detected_risks, kwargs={"force": True}, use_container_width=True)
        example_one, example_two = st.columns(2)
        with example_one:
            st.button("기말 매출 예시", on_click=load_example, args=("cutoff",), use_container_width=True)
        with example_two:
            st.button("채권 회수 예시", on_click=load_example, args=("receivable",), use_container_width=True)

selected_risk_ids = selected_ids("risk", risks, "risk_id")
planned_procedure_ids = selected_ids("proc", procedures, "procedure_id")

with output_col:
    with st.container(border=True):
        state_label = "review" if st.session_state["show_review"] else "ready"
        st.markdown(f'<div class="workbench-header"><span>출력창</span><span class="status ok">{state_label}</span></div>', unsafe_allow_html=True)
        if not st.session_state["show_review"]:
            st.markdown(
                '<div class="output-card"><h3>검토 결과</h3><div class="output-card-content"><p class="help-text">왼쪽 입력값을 조정한 뒤 <strong>커버리지 검토</strong>를 누르면 결과가 표시됩니다.</p></div></div>',
                unsafe_allow_html=True,
            )
        elif not selected_risk_ids:
            st.warning("검토할 위험징후를 하나 이상 선택해주세요.")
        else:
            result = review_risk_coverage(ROOT, selected_risk_ids, planned_procedure_ids)
            # The review contains nested cards and rows. Rendering it through Markdown can
            # terminate raw-HTML blocks at blank lines and expose tags as text, so use the
            # dedicated HTML element instead.
            st.html(render_review_html(result, procedure_by_id))

            questions = questions_for_risks(SEED_DIR, selected_risk_ids)
            with st.expander("추가 확인 질문", expanded=False):
                st.markdown(safe_list(questions, "현재 선택 항목만으로 추가 질문이 생성되지 않았습니다."), unsafe_allow_html=True)

            missing_core = result["missing_core_procedures"]
            with st.expander("경고 상세", expanded=False):
                details = [f"{item['risk_name']} → {item['procedure_name']}: {item['gap']}" for item in missing_core]
                details.extend(f"{item['procedure_name']}: {item['reason']}" for item in result["weak_selections"])
                details.extend(result["warnings"])
                st.markdown(safe_list(details, "현재 Seed 규칙에서 즉시 표시할 상세 경고가 없습니다."), unsafe_allow_html=True)

            with st.expander("절차 후보 평가", expanded=False):
                st.caption("평가는 로컬 SQLite에 저장되며 Seed 정의를 자동 변경하지 않습니다.")
                for item in result["recommendations"][:5]:
                    st.markdown(f"**{item['procedure_name']}** · {RELATION_LABELS[item['relation_label']]}")
                    feedback_columns = st.columns(4, gap="small")
                    for column, (label, feedback_type) in zip(feedback_columns, FEEDBACK_OPTIONS.items()):
                        with column:
                            if st.button(label, key=f"feedback_{item['procedure_id']}_{feedback_type}", use_container_width=True):
                                save_feedback(
                                    FEEDBACK_DB,
                                    "CUSTOM_REVIEW",
                                    str(item["procedure_id"]),
                                    feedback_type,
                                    input_snapshot={
                                        "narrative": st.session_state["risk_narrative"],
                                        "risk_ids": selected_risk_ids,
                                        "account_cycle": account_cycle,
                                    },
                                    model_version="seed-rules-v1",
                                )
                                st.toast("평가를 로컬 SQLite에 저장했습니다.")
                    st.divider()

with st.expander("프로젝트 설명 보기 · 요약, 생성 구조, 검증 결과, 데모 흐름", expanded=False):
    report_path = ROOT / "data" / "generated" / "generation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    st.markdown(
        """
        <div class="hero-inner">
          <div>
            <p class="eyebrow">Educational audit analytics prototype</p>
            <h2 class="hero-title">Revenue Audit Risk-Response Mapper</h2>
            <p class="subtitle">매출·매출채권 위험징후를 가능한 왜곡 양상, 경영진 주장, 추가 확인 질문, 감사절차 후보와 연결하는 교육용 검토 도구입니다.</p>
          </div>
          <aside class="hero-proof">
            <div class="mock-header"><span>SCN04200001</span><span>태그·규칙 기반 적합도</span></div>
            <div class="mock-body">
              <p class="case-text">결산일 직전 매출 집중과 고객 검수조건 사례에서 기간귀속, 발생사실, 정확성 주장을 중심으로 절차 후보를 점검합니다.</p>
              <div class="recommendation"><span class="rank">1</span><div><h3>기말 전후 매출 컷오프 검사</h3><p>출고일, 인수일, 수익인식일 비교</p></div><strong class="score">core</strong></div>
              <div class="recommendation"><span class="rank">2</span><div><h3>계약서 주요 조건 검사</h3><p>검수조건과 비표준 조건 확인</p></div><strong class="score">support</strong></div>
              <div class="recommendation"><span class="rank">3</span><div><h3>기말 후 반품·대변전표 검사</h3><p>증거 이용 가능성에 따라 조건부 후보</p></div><strong class="score">cond.</strong></div>
            </div>
          </aside>
        </div>
        """,
        unsafe_allow_html=True,
    )
    scenario_count = report.get("scenario_count", "-")
    pair_count = report.get("pair_count", "-")
    seed = report.get("seed", "-")
    st.markdown(
        f"""
        <h2>Phase 1 결과 요약</h2>
        <div class="metrics-grid">
          <div class="metric"><span>합성 시나리오</span><strong>{scenario_count}</strong><small>seed {seed}, smoke mode</small></div>
          <div class="metric"><span>시나리오-절차 후보쌍</span><strong>{pair_count}</strong><small>시나리오당 5개 후보</small></div>
          <div class="metric"><span>Seed 위험징후</span><strong>{len(risks)}</strong><small>사람이 검토 가능한 지식베이스</small></div>
          <div class="metric"><span>Seed 감사절차</span><strong>{len(procedures)}</strong><small>Python 규칙에서 직접 사용</small></div>
        </div>
        <h2>데이터 생성 구조</h2>
        <div class="pipeline">
          <div class="pipe-step"><span class="step-no">1</span><h3>Seed KB</h3><p>태그, 위험징후, 감사절차와 매핑</p></div>
          <div class="pipe-step"><span class="step-no">2</span><h3>Templates</h3><p>위험 조합과 사실관계 시나리오 틀</p></div>
          <div class="pipe-step"><span class="step-no">3</span><h3>Generator</h3><p>재현 가능한 합성 사례와 후보쌍</p></div>
          <div class="pipe-step"><span class="step-no">4</span><h3>Validator</h3><p>외래키, 중복, 주장과 split 검사</p></div>
          <div class="pipe-step"><span class="step-no">5</span><h3>Review UI</h3><p>추천 근거와 누락 가능성 확인</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

scenarios_path = ROOT / "data" / "generated" / "scenarios.csv"
pairs_path = ROOT / "data" / "generated" / "scenario_procedure_pairs.csv"
if scenarios_path.exists() and pairs_path.exists():
    st.markdown("## 합성 사례 탐색")
    scenarios = read_csv(scenarios_path)
    selected_scenario = st.selectbox(
        "합성 사례",
        scenarios,
        format_func=lambda row: f"{row['scenario_id']} · {row['scenario_text_ko'][:64]}",
    )
    st.info(selected_scenario["scenario_text_ko"])
    for item in recommend_for_scenario(ROOT, selected_scenario["scenario_id"]):
        with st.expander(f"{item['procedure_name']} · 적합도 {item['fit_score']:.0%}"):
            st.write(item["audit_objective"])
            st.write(item["recommendation_reason"])
else:
    st.info("합성 사례 탐색을 사용하려면 먼저 smoke 데이터 생성 명령을 실행하세요.")

with st.expander("한계와 다음 단계 보기 · 전문적 판단 대체 금지, 합성 데이터 한계", expanded=False):
    st.markdown(
        """
        <div class="limits">
          <div class="limit"><h3>전문적 판단 대체 아님</h3><p>감사의견, 중요성, 표본크기, 감사시간, 충분한 감사증거 확보 결론을 산출하지 않습니다.</p></div>
          <div class="limit"><h3>합성 교육 데이터</h3><p>현재 생성 행과 키워드 Seed는 실무자 검토 전이며 기본 상태는 ai_generated_unreviewed입니다.</p></div>
          <div class="limit"><h3>다음 단계</h3><p>실무자 검토를 통해 Seed의 위험–주장–절차 연결과 키워드 오탐을 보완해야 합니다.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="footer-bar"><span>Revenue Audit Risk-Response Mapper</span><span>Dynamic Streamlit app · Seed-backed Python rules</span></div>',
    unsafe_allow_html=True,
)
