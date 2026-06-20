# Antigravity 작업 지시 프롬프트 — LLM 매칭·추천 레이어 구현

> 대상 툴: Antigravity (Agent Coding) · 모델: Gemini 3.1 Pro
> 사용법: `=== 프롬프트 시작 ===` ~ `=== 프롬프트 끝 ===` 구간을 그대로 복사해 붙여넣으세요.
> 작업 디렉터리: `backend/ai-api/`

---

=== 프롬프트 시작 ===

## 역할 / 목표

너는 CareerStep 프로젝트의 백엔드 엔지니어다. `backend/ai-api` 에 **사용자↔공고 LLM 매칭·추천 레이어**를 구현한다.

사용자 1명의 프로필을 받아, 가공된 공고(MongoDB `job_raw`) 중 적합한 것을 골라 **매칭 점수(0~100)·근거·보유/부족 스킬 + 종합 강점/갭/로드맵**을 반환한다.

### 가장 중요한 설계 원칙 — 비용 구조 (반드시 지킬 것)
공고가 100건이 넘어도 **사용자당 LLM 호출은 1회**여야 한다. 절대 "공고 하나당 LLM 호출 1회" 로 만들지 마라. 구조는 2단계다:

1. **후보 검색(retrieval) — LLM 0회 (결정론):** 이미 만든 라우팅/수요/Gap 로직으로 전체 공고를 점수화해 **상위 K개(기본 15, 최대 20)만** 추린다.
2. **배치 채점(batch scoring) — LLM 1회:** 추린 후보 전부(≤20)를 **하나의 프롬프트에 묶어** 넣고, LLM이 각 후보의 점수·근거를 JSON 배열로 한 번에 반환한다.

→ 사용자당 비용 = (결정론 1패스, 공짜) + (LLM 1콜, 후보 ≤20개 묶음). 공고 수가 늘어도 콜 수는 일정하다.

## 작업 전 반드시 읽을 파일 (컨텍스트)

1. `docs/matching-engine-design.md` — §4(후보검색), §4.5(시장수요), §5(LLM 매칭), §10(에이전트/Phase). 본 작업은 Phase 1 모놀리식이다.
2. `app/services/demand_aggregator.py` — `demand_for_role()`, 수요 분포 구조.
3. `app/services/gap_analyzer.py` — `resolve_role()`, `analyze_gap()`, `core_skills()`. 후보검색·컨텍스트에 재사용.
4. `app/services/router.py` — `process_routing_for_job()`, `routed_roles` 구조.
5. `app/core/mongo.py` — `mongo.job_raw` (요약·라우팅된 공고가 여기 있음).
6. `app/gateway/client.py` — `gpt_gateway.chat_json(...)` 의 **현재 시그니처**(아래 주의).
7. `app/routers/resume.py` 또는 `app/routers/essay.py` — `chat_json` 을 `response_format` 과 함께 올바르게 호출하는 **현행 예시**. 이 패턴을 그대로 따른다.
8. `app/schemas.py` — `ProfileInput`, `RecommendJobsRequest/Response`, `RecommendedJob`.
9. `tests/conftest.py` — Gateway/DB mock 픽스처, `smoke`/`full` 마커.

### ⚠️ 현재 코드의 함정 (먼저 고칠 것)
- `gpt_gateway.chat_json` 시그니처는 이제 **`response_format: type[BaseModel]` 이 필수**다(Structured Outputs로 마이그레이션됨). 그런데 `app/routers/recommendations.py` 는 아직 옛 방식으로 호출해서 **현재 깨진 상태**다. `resume.py`/`essay.py` 처럼 `response_format=RecommendJobsResponse` 를 넘기도록 고쳐라.
- `app/schemas.py` 의 `JobInput`(`id:int`, `description:str`)과 `RecommendedJob.job_id:int` 는 **구 SQL 모델 기준**이라 MongoDB 요약 구조와 안 맞는다. 아래대로 교체한다.

## 입력 데이터 구조 (정확히 이 형태)

### MongoDB `job_raw` 문서 (요약·라우팅 완료분)
```json
{
  "_id": "49306604", "job_id": "49306604",
  "company_name": "...", "title": "...", "status": "routed",
  "summary": {
    "relevant_positions": [
      {
        "position_title": "백엔드 개발자",
        "experience_level": "경력",
        "main_tasks": ["..."], "requirements": ["..."],
        "preferred": ["..."], "tech_stack": ["python"],
        "location": "서초",
        "routed_roles": [{"role": "백엔드개발자", "score": 0.42, "rank": 1}]
      }
    ]
  }
}
```
- **매칭 단위 = position**(공고 한 건에 여러 포지션 가능). 후보는 `job_id + position_title` 로 식별.

### 사용자 프로필 (`ProfileInput`)
```json
{"desired_role": "백엔드 개발자", "skills": ["Java","스프링부트"], "certificates": ["정보처리기사"], "projects": ["쇼핑몰 API 개발"]}
```

## 구현 1 — `app/services/matcher.py` (신규, 핵심)

### 1-A. `retrieve_candidates(profile, positions, demand, top_k=15, max_k=20) -> list[dict]`  (LLM 0회, 결정론)
- `positions`: 모든 공고의 relevant_positions 를 평탄화한 리스트(각 항목에 `job_id`, `company_name` 포함).
- `gap_analyzer.resolve_role(profile["desired_role"], demand)` 로 사용자 표준 직군 결정.
- 후보 풀 = `routed_roles` 에 해당 직군이 포함된 포지션. (해당 직군 후보가 top_k 미만이면 인접/2순위 직군까지 확장하는 fallback.)
- 각 후보 `retrieval_score` = 직군 적합도(`routed_roles`의 해당 role score) + 사용자 스킬과 `tech_stack` 교집합 비율(가중). 정규화된 스킬 비교는 `alias_dict.normalize_text` 사용.
- `retrieval_score` 내림차순 정렬 → 상위 `min(top_k, max_k)` 반환. 각 후보는 **컴팩트 요약**만 담는다(아래).
- 순수 함수(파일/네트워크/LLM 호출 없음) → 오프라인 단위테스트 가능.

### 1-B. 컴팩트 후보 포맷 (토큰 절약)
LLM 에 넘길 때 공고당 **꼭 필요한 필드만**, 긴 리스트는 상한을 둔다(예: main_tasks/requirements/preferred 각 최대 6개):
```json
{"job_id":"49306604","position_title":"백엔드 개발자","company":"...",
 "experience_level":"경력","tech_stack":[...],"requirements":[...max6],
 "preferred":[...max6],"main_tasks":[...max6]}
```
`benefits`, `location` 등 매칭과 무관/저가치 필드는 제외.

### 1-C. `match_jobs(profile, positions, demand, model=None) -> dict`  (LLM 1회)
- `retrieve_candidates` 로 후보 ≤20개 확보.
- (선택) `gap_analyzer.analyze_gap(profile, demand)` 결과를 컨텍스트로 동봉(종합 갭/로드맵 품질 향상).
- **단 한 번** `gpt_gateway.chat_json(system_prompt=MATCH_JOBS_SYSTEM_PROMPT, payload={profile, candidates, market_demand_top, gap}, endpoint="/recommend/jobs", response_format=RecommendJobsResponse, model=model)` 호출.
- 결과를 `RecommendJobsResponse` 로 검증해 반환.
- 후보가 0개면 LLM 호출 없이 빈 추천 + 안내 notes 반환.

## 구현 2 — `app/schemas.py` (교체/보강)
```python
class CandidateJob(BaseModel):           # JobInput 대체 (구 SQL용 JobInput은 제거 또는 유지하되 미사용)
    job_id: str
    position_title: str
    company: str
    experience_level: str | None = None
    tech_stack: list[str] = []
    requirements: list[str] = []
    preferred: list[str] = []
    main_tasks: list[str] = []

class RecommendJobsRequest(BaseModel):
    profile: ProfileInput
    candidates: list[CandidateJob] = Field(max_length=20)   # ★최대 20 유지
    market_demand_top: list[str] = []   # 해당 직군 핵심 수요 스킬(컨텍스트)
    # gap 컨텍스트는 dict로 받아도 됨

class RecommendedJob(BaseModel):
    job_id: str                 # ★ int → str
    position_title: str         # 동일 job_id 내 포지션 구분
    match_score: int = Field(ge=0, le=100)
    reason: str
    matched_skills: list[str]
    missing_skills: list[str]
```
- `RecommendJobsResponse`(recommendations, strengths, gaps, roadmap, policy_violation)는 유지. **Structured Outputs 호환**을 위해 `resume.py`/`essay.py` 가 쓰는 response_format 모델 패턴(필드 정의 방식)을 그대로 따를 것.

## 구현 3 — `app/services/prompts.py` (`MATCH_JOBS_SYSTEM_PROMPT` 신규/개정)
기존 `RECOMMEND_JOBS_SYSTEM_PROMPT` 를 개정하거나 신규 작성. 핵심 지시:
- 입력의 `candidates` **각각**에 대해 점수·근거를 매겨 `recommendations` 배열로 **한 번에** 반환(후보 수만큼).
- 점수는 **tech_stack 만이 아니라** `requirements`(학력·연차), `experience_level`(신입/경력 부합), `preferred`, `main_tasks` 까지 종합. 대체 가능한 스택(java vs python 등)을 모두 필수로 취급하지 말고, 사용자의 실제 스택 생태계를 고려해 판단하라.
- `reason` 은 사용자 프로필의 **명시적 근거**(보유 스킬/자격/프로젝트)와 연결. 사용자가 안 가진 경험·자격·프로젝트를 **지어내지 말 것**(Guardrail). 위반 유도 시 `policy_violation=true`.
- 종합 `gaps`/`roadmap` 은 동봉된 `market_demand_top`/gap 컨텍스트의 수요 빈도를 우선순위로 활용.
- 반드시 유효한 JSON만 출력.

## 구현 4 — `app/routers/recommendations.py` (수정)
- 현행 깨진 호출을 고친다: `chat_json(..., response_format=RecommendJobsResponse)`.
- 엔드포인트 두 개:
  - `POST /recommend/jobs` — 호출자가 `candidates` 를 직접 준 경우 배치 채점(matcher.match_jobs 의 LLM 파트). 내부 전용(`verify_internal_key`).
  - `POST /recommend/match` — `profile` 만 받아 **DB에서 직접** routed 공고를 읽어 retrieve→batch 까지 수행(원스톱). MongoDB 조회는 라우터/서비스에서 `mongo.job_raw.find({"status": "routed"})`(또는 summary 존재) 사용.
- 모델 라우팅: 채점은 가성비 모델(`settings.openai_model` 또는 명시적 mini). 로드맵 고급모델 분리는 이번엔 하지 않음(Phase 1 단일콜). 주석으로 "Phase 2에서 로드맵 모델 분리 가능" 남길 것.

## 구현 5 — `run_match.py` (루트 데모 스크립트)
- `run_demand_agg.py` 스타일. `--source samples|mongo`.
- 샘플 프로필로 **retrieve_candidates 결과(후보 목록 + retrieval_score)를 먼저 출력**(LLM 없이 공짜로 확인).
- `OPENAI_API_KEY` 가 설정돼 있으면 이어서 `match_jobs` 까지 실행해 `match_report.md` 생성. 없으면 후보까지만 출력하고 안내.

## 구현 6 — 테스트 `tests/test_matcher.py`
LLM 없이 도는 결정론 부분을 우선 검증. `conftest.py` 의 Gateway mock 픽스처로 LLM 파트도 검증.
- `@pytest.mark.smoke test_retrieve_basic`: 직군 맞는 포지션이 후보에 오르고, 무관 직군은 빠지는지.
- `@pytest.mark.full test_retrieve_topk_cap`: 후보가 많아도 max_k(20) 초과하지 않는지.
- `@pytest.mark.full test_retrieve_ranking`: 스킬 겹침 많은 후보가 상위인지.
- `@pytest.mark.full test_match_jobs_single_call`: `match_jobs` 가 **chat_json 을 정확히 1회** 호출하고(mock), 후보 ≤20 으로 호출하며, 응답을 `RecommendJobsResponse` 로 파싱하는지.
- `@pytest.mark.full test_no_candidates`: 후보 0개면 LLM 호출 없이 빈 결과 반환.

## 완료 기준 (Definition of Done)
1. `pytest -m smoke` 및 `pytest tests/test_matcher.py -v` 전체 통과, 커버리지 60% 하한 유지.
2. `recommendations.py` 가 새 `chat_json` 시그니처로 정상 동작(기존 깨짐 해소).
3. `python run_match.py --source samples` 실행 시 후보 목록이 출력되고, 키가 있으면 `match_report.md` 생성.
4. **사용자당 LLM 호출이 1회**임을 `test_match_jobs_single_call` 로 증명.
5. 새 pip 의존성 0개. 변경 요약(파일별 변경·삭제한/추가한 스키마 필드)을 한국어로 보고.

## 제약
- 후보 검색·payload 빌드는 순수 함수(파일/네트워크/LLM 금지). I/O는 라우터와 `run_match.py` 에만.
- LLM 호출은 반드시 `gpt_gateway.chat_json` 경유(직접 OpenAI 호출 금지). 비용/재시도/로깅이 거기서 처리됨.
- `chat_json` 은 사용자당 1회만. 후보 루프 안에서 호출 금지.
- 라우팅(router.py) 로직은 변경하지 말 것.

=== 프롬프트 끝 ===

---

## 참고: 설계 의도 (붙여넣지 않아도 됨)
- **2단계(결정론 retrieval + 배치 LLM)** 가 비용의 핵심. 공고 1000건이어도 후보는 ≤20, LLM은 1콜.
- **전체 필드 매칭**으로 "tech_stack만 보는" 한계(대체스택 합산·경력수준 무시)를 LLM이 흡수.
- Phase 1은 단일콜(채점+로드맵 한 번에). 품질/비용 이슈 생기면 Phase 2에서 로드맵만 고급모델로 분리(설계문서 §10).
- `run_match.py` 가 LLM 없이 후보까지 보여주므로, 키 없이도 retrieval 품질을 먼저 검증 가능.
