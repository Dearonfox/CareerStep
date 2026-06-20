# 사용자 ↔ 공고 매칭 엔진 설계 (LLM 기반)

> 작성일: 2026.06.20 (개정: 시장 수요 기준 피봇) · 대상 모듈: `ai-api`, `main-api`, `frontend`
> 상태: 설계(Design) — 구현 착수 전

> **핵심 설계 전환 (2026.06.20):** 합격 후기/합격자 스펙 데이터는 확보 불가로 판단. 따라서 벤치마크 기준을 **"합격자 스펙" → "시장 수요(채용공고 집계)"** 로 전환한다. Gap 진단·로드맵의 기준선은 합격자 흉내가 아니라 **수집된 공고를 집계한 직군별 수요 분포**다. Neo4j 합격 후기 그래프는 로드맵에서 제외(§9 참조).

---

## 0. 배경

크롤러 → 요약 → 직무 라우팅까지 데이터 파이프라인은 완성됐다 (`status: pending → detailed → summarized → routed`).
지금 비어 있는 것은 **"가공된 공고 데이터를 사용자 개인의 역량과 이어서 매칭 점수·근거를 산출하는 엔진"** 이다. 이 문서는 그 엔진을 LLM 기반으로 구현하기 위한 설계를 정의한다.

기존 자산:
- `ai-api/routers/recommendations.py` — LLM 추천 엔드포인트(스캐폴드, 실데이터 미연결)
- `ai-api/schemas.py` — `ProfileInput`, `RecommendJobsRequest/Response`, `RecommendedJob` 정의 존재
- `main-api/models.py` — `Profile`(desired_role, skills, certificates, projects)
- `frontend` — `MatchScoreBadge.tsx`, `useRecommendStore.ts` (mock 구동 중)

이 설계는 새로 만드는 게 아니라 **위 스캐폴드를 실데이터에 연결하고 후보 검색 단계를 추가**하는 것이 핵심이다.

---

## 1. 초안 아키텍처와의 매핑

원래 5-레이어 초안 대비 현재 구현 위치를 정리한다. 초안의 Graph RAG/Vector DB 비전은 **향후 진화 경로**로 두고, 지금은 실용적 대체재로 간다.

| 초안 레이어 | 초안 구상 | 현재 구현 (MVP) | 비고 |
|---|---|---|---|
| 1. Data Layer | 후기·공고 수집 → 정제 → Neo4j + Vector DB 적재 | 잡코리아 공고 크롤링 → MongoDB `job_raw` → GPT 요약 → routed_roles | 후기/Neo4j/Vector DB 미구현. 공고만 확보 |
| 2. User Layer | 이력서·성적표 파싱 → 역량 추출 → MySQL `profiles` | `profiles` 테이블 + 수동 입력 폼 존재 | 자동 파싱(PDF/성적표)은 미구현 |
| 3. AI Core | Graph RAG 검색 + 마일스톤 생성 + 모델 라우팅 | 직무 라우팅(`router.py`) 완료, **매칭/추천은 이 문서 대상** | Graph RAG → routed_roles 기반 후보검색으로 대체 |
| 4. Core & Monitor | JWT/Redis, 내부 프록시, latency 추적 | JWT·Redis 인증, `X-Internal-Key` 프록시, ai_usage 추적 구현 | 대체로 완료 |
| 5. Frontend | 대시보드·타임라인·입력 위젯 | 컴포넌트 스캐폴드(mock) | 실데이터 연동 필요 |

핵심 결론: **초안의 "Graph RAG 검색기"는 현 단계에서 `routed_roles` 기반 후보 필터링 + LLM 재정렬로 근사**한다. Neo4j/Vector DB는 데이터(특히 합격 후기)가 쌓인 뒤 도입한다.

---

## 2. 목표와 범위

### 목표
사용자 1명의 역량 프로필을 입력받아, 가공된 공고 중 **적합도 높은 순으로 매칭 점수(0~100)·근거·보유/부족 스킬·역량 갭·로드맵**을 반환한다.

### 이번 범위 (In Scope)
- routed_roles 기반 **후보 공고 검색(retrieval)** 단계 신설
- 후보 공고 + 사용자 프로필을 LLM에 전달하는 **매칭 엔드포인트** 실데이터 연결
- main-api ↔ ai-api 매칭 프록시 라우트
- 매칭 결과 응답 스키마 확정 및 프론트 연동 포인트 정의

### 범위 외 (Out of Scope, 향후)
- 합격 후기 그래프(Neo4j) / 공고 임베딩(Vector DB)
- 이력서·성적표 자동 파싱
- 마일스톤/대외활동 생성기 (별도 엔진, 본 매칭 결과를 입력으로 사용)

---

## 3. 엔드투엔드 데이터 흐름

```
[Frontend]
   │  GET /api/recommendations/me  (JWT)
   ▼
[main-api]
   1) profiles 테이블에서 사용자 역량 로드
   2) 후보 검색: MongoDB job_raw(status=routed)에서
      user.desired_role(+alias) ∩ job.routed_roles 인 공고 Top-K(예: 20) 선별
      └ 1차 점수 = routed_roles score × skill 겹침 가중치
   2-B) 시장 수요 집계: 같은 직군 공고 전체에서 skills/requirements 빈도 분포 산출
        └ "백엔드개발자 공고의 80%가 Spring, 60%가 AWS 요구" (§4.5)
   3) 후보 공고 요약 + 프로필 + 시장수요 분포를 ai-api로 전달 (X-Internal-Key)
   │  POST /recommend/jobs
   ▼
[ai-api]  (recommendations.py)
   4) GPT 매칭: 프로필 ↔ 후보공고 → match_score/reason/matched·missing skills
      Gap = 프로필 vs 시장수요 분포 (합격자 흉내가 아니라 시장 기준)
      strengths / gaps / roadmap 생성
   5) gpt_gateway 경유 (비용·rate limit·재시도 자동 처리)
   ▼
[main-api] 결과 후처리(정렬·필터) → [Frontend] 렌더 (MatchScoreBadge 등)
```

핵심 설계 결정: **2단계(후보 검색)를 반드시 둔다.** 공고가 148개+이고 LLM 입력은 한 번에 ≤20개로 제한(`RecommendJobsRequest.jobs max_length=20`)되므로, routed_roles로 먼저 추려야 LLM 비용과 품질이 모두 잡힌다. LLM은 "정밀 재정렬 + 근거 생성" 역할.

---

## 4. 후보 검색(Retrieval) 단계 — main-api 신설

`router.py`의 스코어링 철학을 재사용한 결정론적 1차 필터.

입력: `Profile.desired_role`, `Profile.skills`
처리:
1. `desired_role` 을 `alias_dict` 로 정규화 → 표준 직군 키
2. MongoDB `job_raw`에서 `status="routed"` 이고 `routed_roles[].role` 에 해당 직군이 포함된 공고 조회
3. 1차 점수 = `routed_roles.score`(직군 적합도) + `skills` 교집합 비율 가중
4. 점수 내림차순 Top-K(기본 20) 선별 → LLM 입력 후보

이 단계는 LLM 호출 0회. 후보가 20개 미만이면 직군 인접도(예: 백엔드개발자↔서버엔지니어)로 보충하는 fallback을 둔다.

---

## 4.5 시장 수요 프로필 집계 (Market-Demand Benchmark) — main-api 신설 ★핵심

합격 후기 데이터가 없으므로, **벤치마크 기준선을 "수집된 공고의 집계"로 대체**한다. 이것이 이 제품의 차별점이자 Gap·로드맵의 근거가 된다.

처리 (LLM 호출 0회, MongoDB 집계):
1. 사용자 희망 직군(정규화 키)에 routed 된 공고 전체를 모은다 (후보 Top-K가 아니라 **해당 직군 전수**)
2. 각 공고 `summary.기술스택` / `summary.자격요건` / `summary.우대사항` 항목을 정규화·집계
3. 직군별 **수요 분포** 산출: 항목별 등장 빈도(%)와 순위
   - 예) `백엔드개발자`: `{ "Spring": 0.80, "AWS": 0.62, "Kafka": 0.35, "MSA": 0.28, ... }`
4. 결과를 캐시(직군 단위, 일 1회 갱신 정도면 충분)

활용:
- **Gap 진단의 기준선**: "내 스킬" vs "시장 수요 분포" → "공고의 62%가 AWS를 요구하는데 보유하지 않음" 같이 **정량적·데이터 근거** 갭 도출. 환각 불가능 (실제 집계 수치).
- **로드맵의 우선순위**: 갭 중 수요 빈도가 높은 항목부터 채우도록 LLM에 가중치 제공.
- **희소성 신호**: 사용자가 보유했지만 시장 수요가 높은 스킬 → "강점"으로 부각.

이 집계는 §10.1 Data Retriever 에이전트의 실질 데이터 소스(Neo4j 대체)이기도 하다.

---

## 5. LLM 매칭 단계 — ai-api (`recommendations.py` 확장)

기존 엔드포인트를 실데이터로 연결한다. 인터페이스는 유지하되 입력 공고를 MongoDB 요약 기반으로 채운다.

- 엔드포인트: `POST /recommend/jobs` (내부 전용, `verify_internal_key`)
- 게이트웨이: `gpt_gateway.chat_json()` 경유 (비용/rate limit/재시도 자동)
- 모델 라우팅 (초안 "모델 라우팅 가이드" 반영):
  - **매칭 점수·근거 산출** → 가성비 모델 `gpt-4.1-mini` (구조적 추출 성격)
  - **로드맵/마일스톤 생성** → 고품질 모델(Claude 또는 `gpt-4o`)로 분기 (복잡 추론)
  - 분기 기준은 endpoint 또는 요청 플래그(`need_roadmap`)로 제어

---

## 6. API & 스키마

### 6.1 main-api 신규 라우트
```
GET  /api/recommendations/me        # 내 프로필 기반 추천 (JWT)
  → 200 RecommendJobsResponse
POST /api/recommendations/preview   # (선택) 프로필 직접 전달해 미리보기
```

### 6.2 ai-api 요청 (기존 스키마 보강)
`JobInput` 을 MongoDB 요약 구조에 맞춰 확장 — 현재 SQL 기반 필드(id:int, description:str) 대신 요약·라우팅 필드 추가.

```python
class JobInput(BaseModel):
    job_id: str              # MongoDB _id (잡코리아 job_id)
    title: str
    company: str
    routed_roles: list[str]  # 라우팅된 직군 (1차 후보 근거)
    skills: list[str]        # summary.기술스택
    requirements: list[str]  # summary.자격요건
    preferred: list[str]     # summary.우대사항
    employment_type: str | None = None
    location: str | None = None
```

### 6.3 응답 (기존 유지 + 보강)
`RecommendedJob` 에 1차 점수 추적용 필드 옵션 추가:
```python
class RecommendedJob(BaseModel):
    job_id: str
    match_score: int          # 0~100 (LLM 최종)
    retrieval_score: float | None = None  # 1차 결정론 점수(디버깅/정렬)
    reason: str
    matched_skills: list[str]
    missing_skills: list[str]
```
`RecommendJobsResponse` 의 `strengths/gaps/roadmap/policy_violation` 은 그대로 사용.

---

## 7. 프롬프트 보강

기존 `RECOMMEND_JOBS_SYSTEM_PROMPT` 의 안티-환각 원칙(사용자 경험·자격·프로젝트 날조 금지)은 유지하고, 다음을 추가한다:
- 입력 공고가 `routed_roles`·요약 기반임을 명시하고, **매칭 근거를 routed_roles 및 요약 항목과 명시적으로 연결**하도록 지시
- `match_score` 산정 기준 명문화: 직군 일치(40) + 보유 스킬 커버리지(40) + 우대/프로젝트 적합(20) 가이드라인 제시
- **시장 수요 분포(§4.5)를 컨텍스트로 주입**하고, `gaps` 는 "시장 공고의 N%가 요구하나 미보유" 형태로 **수치 근거와 함께** 서술하도록 지시. 합격자/타인 사례를 지어내지 말 것.
- 로드맵은 갭 중 **수요 빈도 높은 항목 우선**으로 정렬하도록 지시
- 한국어 직군·기술 표면형 다양성(예: "백엔드"="서버개발") 인지 지시

---

## 8. 프론트엔드 연동

- `useRecommendStore.ts`: mock 제거 → `GET /api/recommendations/me` 연동
- `MatchScoreBadge.tsx`: `match_score` 바인딩 (이미 prop 구조 존재)
- `JobCard.tsx`: `matched_skills` / `missing_skills` 칩 표시
- 결과 페이지: `strengths` / `gaps` / `roadmap` 섹션 렌더 (초안의 "마일스톤 타임라인 UI" 축소판)

---

## 9. 향후 진화

1. **Vector DB 도입 (유효)**: 공고 요약을 임베딩해 후보 검색·시장수요 집계를 키워드 매칭 → 의미 유사도로 고도화. 합격 후기와 무관하게 공고 데이터만으로 가능하므로 **현실적 다음 단계**.
2. **마일스톤 생성기 분리**: 본 매칭의 `gaps`(시장수요 기준)를 입력으로 주차별 액션 플랜 생성 (Claude 분기).
3. **시장 수요 시계열화**: 주기 수집을 활용해 직군별 수요 분포의 **추세**(예: "최근 Kafka 요구 증가") 제공 — 합격 후기보다 오히려 차별적인 인사이트.

> **제외: Neo4j 합격 후기 그래프** — 합격자 스펙↔활동 관계 데이터 확보 불가로 로드맵에서 제외. "비슷한 합격자가 한 활동" 기능 대신 §4.5 시장 수요 집계를 벤치마크로 사용한다. 추후 신뢰 가능한 후기 데이터 소스가 생기면 재검토.

본 설계의 후보 검색·수요 집계 단계는 이후 Vector DB 검색기로 **교체 가능하도록 인터페이스 분리**해 둔다 (retrieval/aggregation 함수를 추상화).

---

## 10. AI Core: 멀티 에이전트 아키텍처 매핑 및 단계적 도입

초안의 AI Core는 Orchestrator가 워커 에이전트(Gap Analyzer / Data Retriever / Milestone Planner)를 지휘하고 Guardrail이 최종 검증하는 멀티 에이전트 구조다. **본 매칭 엔진의 단일 LLM 호출은 이 구조의 모놀리식(monolithic) 버전**이며, 같은 산출물(match·gap·roadmap)을 한 번에 만든다. 따라서 둘은 대립이 아니라 **성숙 단계(phase)의 차이**다.

### 10.1 에이전트 ↔ 현재 자산 매핑

| 에이전트 | 역할 | 현재 구현 | 모델(초안) | 비고 |
|---|---|---|---|---|
| Orchestrator | 상태관리·취합·재작업 루프 | ❌ 없음 (main-api 순차 호출이 대체) | Claude | Phase 2에서 LangGraph 등 도입 |
| Gap Analyzer | 유저 스펙↔**시장 수요** 갭 도출 | △ 응답 `strengths`/`gaps` 에 내포 | gpt-4o-mini | 기준선 = §4.5 수요 분포(합격자 스펙 아님) |
| Data Retriever | 툴 호출로 공고·수요 검색 | △ §4 후보검색 + §4.5 수요집계 = 결정론 버전 | 툴 에이전트 | 데이터 소스 = MongoDB 집계(Neo4j 아님) |
| Milestone Planner | 가용시간 결합 주차별 플랜 | △ 응답 `roadmap` 에 내포 | Claude | 로드맵 모델 라우팅과 일치 |
| Guardrail | 허위경력 필터 + Pydantic 검증 | ✅ `policy_violation` 플래그 + 스키마 검증 | — | 이미 부분 구현 |

핵심: 모놀리식 응답의 각 필드(`gaps`, `roadmap`, `policy_violation`)가 이미 각 에이전트의 산출물에 대응한다. 분할은 "필드를 전담 에이전트로 승격"하는 작업이 된다.

### 10.2 단계적 도입 전략

- **Phase 1 (현재 매칭 엔진):** 모놀리식. `gpt_gateway.chat_json()` 단일 호출로 gap·match·roadmap 동시 생성, `policy_violation` 으로 Guardrail 대체. 가치 검증·빠른 출시 우선.
- **Phase 2 (Data Retriever 분리):** 후보검색·수요집계를 툴 에이전트로 승격. `aggregate_market_demand(role)`, `search_vector_db(keywords)` 툴 장착. §9의 Vector DB 도입과 동반 (Neo4j는 제외).
- **Phase 3 (Planner·Guardrail 분리):** Milestone Planner(Claude)와 Guardrail을 독립 에이전트로 분리, Orchestrator가 재작업 루프 관장. 가용시간·제약조건 입력 추가.

원칙: 각 단계에서 **외부 인터페이스(요청/응답 스키마)는 유지**하고 내부 구현만 모놀리식→멀티 에이전트로 교체한다. 프론트는 영향받지 않는다.

### 10.3 Guardrail 우선 강화 (Phase 1 내에서)

허위 경력 생성 금지는 초안 주의사항이자 현재도 중요하므로, Phase 1 단일 호출 안에서도 다음을 강제한다: 프롬프트의 안티-환각 규칙(§7) + 응답 Pydantic 검증 + `policy_violation` 플래그 + (선택) 사후 검증 패스. 전담 에이전트 분리는 Phase 3로 미루되 규칙 자체는 지금부터 적용.

---

## 11. 작업 분해 (다음 세션 To-Do)

우선순위 순:

1. (main-api) **시장 수요 집계 모듈 신설 (§4.5)** — 직군별 skills/requirements 빈도 분포, 캐시. ★제품 차별점, 우선
2. (ai-api) `schemas.py` — `JobInput`/`RecommendedJob` + `market_demand` 입력 필드 보강
3. (ai-api) `prompts.py` — 매칭 점수 기준 + 시장수요 기반 gap 서술 규칙 추가
4. (main-api) 후보 검색 모듈 신설 — `routed_roles` + skills 1차 스코어링, Top-K 선별
5. (main-api) `GET /api/recommendations/me` 라우트 + ai_proxy 연동 (수요분포 동봉)
6. (ai-api) `recommendations.py` 실데이터 연결 + 모델 라우팅(mini/roadmap 분기)
7. (frontend) `useRecommendStore` 실연동, MatchScoreBadge/JobCard 바인딩, 수요분포 시각화
8. (test) 골든셋 프로필 2~3개로 매칭 품질·비용 검증 (pytest)

선행 의존성: MongoDB `job_raw` 에 `status="routed"` 도큐먼트가 존재해야 함 (이미 충족).
