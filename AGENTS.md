# Agent Notes

- 목적: 매출·매출채권 감사위험, 경영진 주장, 감사절차 후보의 연결을 교육용으로 검토한다.
- 기술: Python, pandas, numpy, scikit-learn, Streamlit, SQLite, pytest.
- `data/seed/`는 사람이 검토 가능한 핵심 지식베이스다.
- `data/generated/` 산출물은 생성 코드로 재생성하며 직접 수정하지 않는다.
- 모든 생성 행의 기본 `review_status`는 `ai_generated_unreviewed`다.
- 정확한 감사기준 문단 번호를 추측하지 않는다.
- 실제 감사 판단, 감사의견, 중요성, 표본크기, 감사시간을 자동화한다고 표현하지 않는다.
- 기존 영화 추천 프로젝트의 데이터와 감사 도메인 데이터를 섞지 않는다.
- 생성: `python -m scripts.generate_dataset --mode smoke --seed 42 --scenario-count 100 --pairs-per-scenario 5`
- 검증: `python -m scripts.validate_dataset --expected-scenarios 100 --expected-pairs 500`
- 테스트: `pytest -q`
- 앱: `streamlit run app.py`
