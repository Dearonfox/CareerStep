# Antigravity 작업 지시 프롬프트 — Gap 분석기 구현

> 대상 툴: Antigravity (Agent Coding) · 모델: Gemini 3.1 Pro
> 사용법: 아래 `=== 프롬프트 시작 ===` 부터 `=== 프롬프트 끝 ===` 까지를 그대로 복사해 Antigravity에 붙여넣으세요.
> 리포지토리: `CareerStep` · 작업 디렉터리: `backend/ai-api/`

---

=== 프롬프트 시작 ===

## 역할 / 목표

너는 CareerStep 프로젝트의 백엔드 엔지니어다. `backend/ai-api` 모듈에 **Gap 분석기(Gap Analyzer)** 를 구현한다.

Gap 분석기는 **사용자의 보유 스킬**을, 이미 구현된 **시장 수요 분포**(직군별로 어떤 기술이 공고의 몇 %에서 요구되는지)와 비교하여, 그 사용자가 목표 직군에 대해 **무엇을 갖췄고(보유), 무엇이 부족하며(부족·우선순위), 어떤 강점이 있는지**를 정량적으로 산출하는 순수 로직이다.

핵심 제약: **LLM 호출 금지, 외부 네트워크/DB 호출 금지, 새로운 pip 의존성 추가 금지.** 표준 라이브러리와 기존 `app/` 모듈만 사용한다. 결정론적 순수 함수로 구현하여 단위 테스트가 쉽게 한다.

## 작업 전 반드시 읽을 파일 (컨텍스트 파악)

순서대로 읽고 데이터 구조와 코드 컨벤션을 파악한 뒤 시작하라.

1. `docs/matching-engine-design.md` — 특히 **§4.5(시장 수요 집계)** 와 **§11(작업 분해)**. 이 프로젝트가 "합격 후기" 대신 "시장 수요 공고 집계"를 벤치마크로 쓴다는 핵심 전환을 이해할 것.
2. `app/services/demand_aggregator.py` — Gap 분석기의 입력이 되는 수요 분포를 만드는 모듈. 출력 구조를 정확히 파악할 것.
3. `app/services/alias_dict.py` — `normalize_text(text)` 스킬 표면형 정규화 함수. **스킬 비교 시 반드시 재사용**할 것 ("파이썬"="python" 등).
4. `app/services/router.py` — `ROLE_KEYWORDS`(26개 표준 직군 키와 키워드 셋). 직군명 해석에 재사용.
5. `app/schemas.py` — `ProfileInput`(사용자 프로필 스키마).
6. `tests/conftest.py`, `tests/test_router.py`, `pyproject.toml` — 테스트 컨벤션(`smoke`/`full` 마커, 커버리지 하한 60%).

## 입력 데이터 구조 (정확히 이 형태)

### 1) 시장 수요 분포 — `demand_aggregator.aggregate_demand()` 의 반환값
```json
{
  "meta": {"job_count": 148, "position_count": 210, "rank1_only": false},
  "roles": {
    "백엔드개발자": {
      "position_count": 24,
      "tech_stack": [
        {"skill": "java", "count": 18, "pct": 0.75},
        {"skill": "spring", "count": 14, "pct": 0.583},
        {"skill": "aws", "count": 12, "pct": 0.5}
      ],
      "experience_level": {"경력": 16, "신입": 8}
    }
  }
}
```
- `roles` 의 키는 26개 표준 직군명(또는 `"기타/비개발"`).
- 각 직군의 `tech_stack` 은 이미 `pct`(수요 점유율, 0~1) 내림차순 정렬돼 있음.
- `skill` 값은 이미 `normalize_text` 로 정규화된 소문자 표준형.

### 2) 사용자 프로필 — `ProfileInput` 형태
```python
{
  "desired_role": "백엔드 개발자",   # 자유 입력 텍스트 (정규화 안 됨)
  "skills": ["Java", "스프링부트", "MySQL"],  # 표면형 다양, 정규화 필요
  "certificates": ["정보처리기사"],
  "projects": ["쇼핑몰 백엔드 API 개발"]
}
```

## 구현할 파일

### A. `app/services/gap_analyzer.py` (핵심)

다음 함수들을 구현한다. 모두 동기(sync) 순수 함수, 한국어 docstring, 타입 힌트 필수.

#### A-1. `resolve_role(desired_role: str, demand: dict) -> str | None`
자유 입력 `desired_role` 을 표준 직군 키로 해석한다.
- 절차: `normalize_text` 적용 → (1) `demand["roles"]` 키와 직접 일치 시 그 키 반환 → (2) 불일치 시 `router.ROLE_KEYWORDS` 를 활용해 `desired_role` 토큰이 어떤 직군 키워드 셋과 가장 많이 겹치는지 점수화하여 최고 직군 반환 → (3) 그래도 매칭 0이면 `None`.
- 예: `"백엔드 개발자"`, `"백엔드"`, `"서버개발자"` → `"백엔드개발자"`.

#### A-2. `analyze_gap(profile: dict, demand: dict, role: str | None = None) -> dict`
핵심 함수. 사용자 프로필과 수요 분포를 비교해 Gap 리포트를 만든다.
- `role` 이 None이면 `resolve_role(profile["desired_role"], demand)` 로 결정.
- 사용자 스킬을 `normalize_text` 로 정규화하고 **중복 제거**.
- 대상 직군의 `tech_stack`(수요 스킬 목록)과 비교하여 다음을 계산:
  - `matched_skills`: (사용자 보유 ∩ 수요) — 각 항목 `{"skill", "pct"}`, **pct 내림차순**.
  - `missing_skills`: (수요 − 사용자 보유) — `{"skill", "pct"}`, **pct 내림차순** (= 학습 우선순위).
  - `extra_skills`: (사용자 보유 − 수요) — 문자열 리스트. 이 직군 수요엔 없지만 보유한 스킬(타 직군 전이 가능성/노이즈).
  - `readiness_score`: **가중 커버리지**. `sum(matched 의 pct) / sum(전체 수요 tech_stack 의 pct)`, 소수 3자리 반올림(0~1). 수요 합이 0이면 0.0.
  - `top_strengths`: `matched_skills` 중 `pct >= 0.3` 인 항목(보유한 고수요 스킬 = 강점). 비어 있을 수 있음.
- 반환 스키마:
```json
{
  "role": "백엔드개발자",
  "role_resolved": true,
  "position_count": 24,
  "readiness_score": 0.62,
  "matched_skills": [{"skill": "java", "pct": 0.75}, {"skill": "spring", "pct": 0.583}],
  "missing_skills": [{"skill": "aws", "pct": 0.5}],
  "extra_skills": ["mysql"],
  "top_strengths": [{"skill": "java", "pct": 0.75}],
  "notes": []
}
```
- 엣지 케이스(반드시 처리, 예외 던지지 말 것):
  - 직군 해석 실패(`resolve_role` → None) → `role_resolved: false`, 빈 결과, `notes` 에 안내 메시지("희망 직군을 표준 직군으로 해석하지 못했습니다") 추가. 가능하면 `rank_roles_by_fit` 상위 3개를 `notes` 로 제안.
  - 해석된 직군이 `demand["roles"]` 에 없음(수요 데이터 없음) → 동일하게 graceful 처리, `notes` 에 "해당 직군의 수요 데이터가 없습니다".
  - 사용자 스킬 빈 배열 → matched 빈 배열, missing = 전체 수요, readiness 0.0.

#### A-3. `rank_roles_by_fit(profile: dict, demand: dict, top_n: int = 5) -> list[dict]`
보너스. 모든 직군에 대해 `readiness_score` 를 계산해 적합도 높은 순으로 정렬해 반환 → `[{"role", "readiness_score", "position_count"}]`. "당신은 사실 이 직군에 더 잘 맞습니다" 인사이트용. `position_count` 가 너무 적은 직군(예: < 3)은 신뢰도 낮으니 제외하거나 후순위.

#### A-4. `render_markdown(report: dict) -> str`
`analyze_gap` 결과를 사람이 읽는 마크다운으로 변환. `demand_aggregator.render_markdown` 의 스타일(퍼센트 + 막대바)을 참고해 일관성 있게. 보유/부족/강점 섹션을 구분해 표시.

### B. `run_gap_analysis.py` (리포지토리 루트 `backend/ai-api/` 에 위치)
CLI 데모 스크립트. `demand_aggregator` 의 `run_demand_agg.py` 스타일을 따른다.
- `demand_profiles.json`(이미 생성돼 있다고 가정, 없으면 `--source samples` 로 `summarized_samples/` 를 즉석 집계해 생성) 을 로드.
- 데모용 샘플 프로필 2~3개를 코드 내 상수 또는 `sample_profiles.json` 로 정의(예: 백엔드 지망생, 데이터 지망생).
- 각 프로필에 대해 `analyze_gap` 실행 후 `render_markdown` 결과를 콘솔에 출력하고 `gap_report.md` 로 저장.
- Windows 콘솔 인코딩 대응: `sys.stdout.reconfigure(encoding="utf-8")`.

### C. `tests/test_gap_analyzer.py`
기존 `tests/test_router.py` 컨벤션을 그대로 따른다(평범한 함수, `pytest.mark.smoke`/`full` 마커, DB·LLM 의존 없음). 테스트는 **인라인 fixture 수요 dict** 를 직접 만들어 결정론적으로 검증한다(실제 demand_profiles.json 의존 금지).

최소 포함 케이스:
- `@pytest.mark.smoke` `test_analyze_gap_basic`: 알려진 수요 + 프로필 → matched/missing 가 기대대로 분리되고 missing 이 pct 내림차순인지.
- `@pytest.mark.full` `test_readiness_score`: 위 예시(java0.75, spring0.583, aws0.5; 보유 java,spring) → readiness ≈ 0.715 (= (0.75+0.583)/(0.75+0.583+0.5)) 검증(허용오차 0.01).
- `@pytest.mark.full` `test_resolve_role_aliases`: "백엔드", "백엔드 개발자", "서버개발자" → "백엔드개발자".
- `@pytest.mark.full` `test_unknown_role_graceful`: 해석 불가 직군 → `role_resolved False`, 예외 없음, notes 존재.
- `@pytest.mark.full` `test_empty_skills`: 빈 스킬 → readiness 0.0, missing = 전체 수요.
- `@pytest.mark.full` `test_rank_roles_by_fit`: 여러 직군 수요에서 보유 스킬이 가장 겹치는 직군이 1위.

## 코드 컨벤션 (엄수)
- 한국어 docstring + 타입 힌트.
- `normalize_text` 재사용(스킬 비교는 반드시 정규화 후). 직접 lower()/replace() 로 중복 구현하지 말 것.
- 새 pip 패키지 추가 금지. `collections`, `typing` 등 표준 라이브러리만.
- `analyze_gap` 내부에서 파일 입출력/네트워크/DB/LLM 호출 금지(순수 함수). I/O는 `run_gap_analysis.py` 에만.
- 기존 파일 수정 최소화. 단 `app/services/demand_aggregator.py` 의 `demand_for_role()` 같은 기존 헬퍼가 있으면 재사용.

## 완료 기준 (Definition of Done)
1. `pytest -m smoke -v` 통과.
2. `pytest tests/test_gap_analyzer.py -v` 전체 통과, 전체 커버리지 60% 하한 유지.
3. `python run_gap_analysis.py --source samples` 실행 시 에러 없이 `gap_report.md` 생성되고, 콘솔에 보유/부족/강점이 사람이 읽을 수 있게 출력됨.
4. 새 의존성 0개, LLM/네트워크 호출 0개.
5. 변경 요약(어떤 파일을 왜 추가/수정했는지)을 마지막에 한국어로 보고.

## 작업 순서 권장
(1) 컨텍스트 파일 읽기 → (2) `gap_analyzer.py` 의 `resolve_role` → `analyze_gap` → `rank_roles_by_fit` → `render_markdown` 순 구현 → (3) 테스트 작성·통과 → (4) `run_gap_analysis.py` 데모 → (5) 샘플로 실행 검증 → (6) 보고.

=== 프롬프트 끝 ===

---

## 참고: 이 프롬프트의 설계 의도 (Antigravity에 붙여넣지 않아도 됨)

- **왜 결정론(LLM 금지)인가**: Gap = "수요에 있는데 내가 없는 스킬"이라는 집합 연산. LLM 없이 정확·무료·즉시 검증 가능. LLM은 이후 단계(근거 문장·로드맵 생성)에서만 사용(설계문서 §5, §10 Phase 1).
- **왜 `readiness_score` 를 단순 개수가 아닌 pct 가중인가**: "공고의 75%가 요구하는 Java"를 가진 것이 "5%가 요구하는 희귀 툴"을 가진 것보다 가치 크다. 수요 빈도로 가중해야 시장 적합도를 제대로 반영.
- **`rank_roles_by_fit` 의 가치**: 사용자가 적은 희망 직군이 실제 본인 스킬과 안 맞을 수 있음 → "당신은 데이터엔지니어에 더 적합" 같은 인사이트는 차별적 기능이 됨.
- **다음 단계 연결**: 이 Gap 리포트(특히 `missing_skills` 우선순위)가 LLM 로드맵 생성기의 입력이 된다(설계문서 §4.5 활용 항목, §11 작업 6).
