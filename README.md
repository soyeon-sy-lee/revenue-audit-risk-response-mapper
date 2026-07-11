# Revenue Audit Risk-Response Mapper

매출 감사위험 대응 매핑 검토 도구입니다. 공개된 감사 개념을 교육용으로 구조화하여 위험징후, 가능한 왜곡 양상, 관련 경영진 주장, 추가 확인 정보, 감사절차 후보, 현재 계획의 누락 가능성을 함께 검토합니다.

이 프로젝트는 감사인의 전문적 판단을 자동화하거나 대체하지 않습니다. 감사의견, 중요성 금액, 표본크기, 감사시간, 충분하고 적합한 감사증거 확보 여부를 산출하지 않습니다.

## 현재 범위

초기 repository는 Phase 1 작은 수직 시제품을 만들기 위한 구조를 포함합니다.

- 통제된 태그 사전 seed
- 위험징후 seed
- 감사절차 seed
- 위험-절차 매핑 seed
- 시나리오 템플릿 seed
- 합성 시나리오 및 후보 쌍 생성기
- 데이터 검증 스크립트
- 규칙 기반 추천/질문/커버리지 기본 모듈
- 로컬 SQLite 피드백 저장소
- pytest smoke tests
- Streamlit 앱 시작점

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 작은 수직 시제품 생성

```bash
python -m scripts.generate_dataset --mode smoke --seed 42 --scenario-count 100 --pairs-per-scenario 5
python -m scripts.validate_dataset --expected-scenarios 100 --expected-pairs 500
```

## 테스트

```bash
pytest -q
```

## 앱 실행

```bash
streamlit run app.py
```

## 결과물 웹페이지

공개 URL: https://soyeon-sy-lee.github.io/revenue-audit-risk-response-mapper/index.html

브라우저에서 `index.html`을 직접 열면 프로젝트 결과 요약 페이지를 볼 수 있습니다. 이 페이지는 smoke 데이터 생성 결과, 클래스 분포, 검증 통과 항목, 데모 흐름과 한계를 정리합니다.
위험상황 텍스트를 입력하면 키워드 기반으로 기본 위험징후를 자동 체크할 수 있으며, 자동 체크 옵션을 끄면 회계사가 모든 위험징후를 직접 선택할 수 있습니다.
커버리지 점검 도구에서는 사용자가 절차 후보를 평가할 수 있고, 해당 평가는 브라우저 로컬 저장소에 보관되어 다음 추천 정렬에 제한적으로 반영됩니다. 감사 주장 매핑과 절차 정의는 자동 변경하지 않습니다.

## 영화 추천 프로젝트에서 참고한 점

기존 `movie-recommender`의 태그 기반 추천, 유사도 점수, 로컬 피드백이라는 제품 아이디어를 참고합니다. 영화 데이터, 영화 태그, 정적 UI 코드는 이 프로젝트에 섞지 않습니다.

## 데이터 한계

현재 seed 및 generated 데이터는 `ai_generated_unreviewed` 상태입니다. 실무자 검토 전 데이터를 전문가 검증 데이터처럼 표현하지 않습니다. 정확한 감사기준 문단 번호는 사용자가 제공한 공식 출처가 없는 한 추측하지 않습니다.
