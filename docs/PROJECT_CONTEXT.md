# CareerStep 프로젝트 컨텍스트

> 마지막 갱신: 2026-06-20 (세션 종료 시점)
> 목적: 다음 세션에서 이 문서만 읽으면 바로 대화를 이어갈 수 있도록 프로젝트의 전체 구조·현재 상태·미해결 과제를 정리

---

## 1. 프로젝트 개요

**CareerStep**은 IT 구직자를 위한 AI 취업 지원 플랫폼이다.
- 채용공고를 자동 수집·요약·분류하고
- 사용자의 역량 프로필과 공고를 매칭하여 적합도 점수·근거·로드맵을 생성한다

### 기술 스택
| 레이어 | 기술 |
|---|---|
| Frontend | React, TypeScript, Zustand, React Router v6 |
| Main Backend | FastAPI (Python), MySQL 8, Redis |
| AI Backend | FastAPI (Python), OpenAI SDK, MongoDB Atlas |
| Crawler | FastAPI (Python), Selenium, MongoDB Atlas |
| 인프라 | Docker Compose, MongoDB Atlas |

### 저장소 구조
```
CareerStep/
├── frontend/                 # React SPA (구직자/관리자)
├── backend/
│   ├── main-api/             # 인증·프로필·CRUD·AI 프록시
│   ├── ai-api/               # GPT 호출·매칭·분석 (이 세션의 주요 작업 대상)
│   └── crawler-api/          # 잡코리아 크롤러
├── docs/
│   ├── ARCHITECTURE.md       # MSA 아키텍처 개요
│   ├── matching-engine-design.md  # 매칭 엔진 상세 설계 (핵심 참고문서)
│   └── task.md               # 전체 To-Do 리스트
├── docker-compose.yml
└── .env
```

---

## 2. 데이터 파이프라인 (완성됨)

```
[잡코리아] ──crawler-api──▶ MongoDB job_raw (status: pending)
   │                            │
   ▼                            ▼ detail_markdown / image_urls 채움
status: detailed ──ai-api 요약──▶ status: summarized (summary 필드 추가)
                                    │
                                    ▼ routed_roles 스코어링
                              status: routed (직군별 점수 배열)
```

### MongoDB `job_raw` 도큐먼트 구조 (핵심)
```json
{
  "_id": "49348400",
  "company_name": "SK에코플랜트㈜",
  "title": "채용 공고 제목",
  "status": "routed",
  "is_image_job": false,
  "summary": {
    "is_relevant": true,
    "relevant_positions": [
      {
        "position_title": "백엔드 개발자",
        "experience_level": "신입",
        "main_tasks": ["API 개발"],
        "requirements": ["Java 3년"],
        "preferred": ["AWS 경험"],
        "tech_stack": ["Java", "Spring Boot", "MySQL"],
        "location": "서울",
        "benefits": ["4대보험"]
      }
    ],
    "filtered_out_positions": ["인사담당"],
    "routed_roles": [
      {"role": "백엔드개발자", "score": 0.92},
      {"role": "풀스택개발자", "score": 0.45}
    ]
  }
}
```

---

## 3. AI Backend (`backend/ai-api`) 파일 맵

### 핵심 서비스 (`app/services/`)

| 파일 | 역할 | LLM 호출 |
|---|---|---|
| [router.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/services/router.py) | 요약된 공고를 26개 직군으로 라우팅·스코어링 | 0회 |
| [alias_dict.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/services/alias_dict.py) | 기술명 정규화 사전 (springboot→spring boot 등) | 0회 |
| [demand_aggregator.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/services/demand_aggregator.py) | 직군별 tech_stack/requirements 빈도 분포 집계 | 0회 |
| [gap_analyzer.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/services/gap_analyzer.py) | 사용자 스킬 vs 시장 수요 → readiness, 강점, 갭 산출 | 0회 |
| [matcher.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/services/matcher.py) | `retrieve_candidates()` (0회) + `match_jobs()` (채점 1회) + `generate_roadmap()` (1회) | 최대 2회 |
| [summarizer.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/services/summarizer.py) | 공고 텍스트/이미지 → GPT 요약 | 공고당 1회 |
| [prompts.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/services/prompts.py) | 모든 시스템 프롬프트 관리 |

### Gateway (`app/gateway/`)

| 파일 | 역할 |
|---|---|
| [client.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/gateway/client.py) | `GPTGateway.chat_json()` — Structured Outputs(`beta.chat.completions.parse`), Rate Limiting, Retry, Usage Tracking |
| [rate_limiter.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/gateway/rate_limiter.py) | RPM/TPM/동시성 제어 |
| [usage_tracker.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/gateway/usage_tracker.py) | SQLite 기반 토큰·비용 추적 |

### 라우터 (`app/routers/`)

| 파일 | 엔드포인트 |
|---|---|
| [recommendations.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/routers/recommendations.py) | `POST /recommend/jobs` (직접 후보 전달), `POST /recommend/match` (DB→retrieve→score 원스톱) |
| [resume.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/routers/resume.py) | `POST /parse/resume` |
| [summarize.py](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/backend/ai-api/app/routers/summarize.py) | `POST /summarize/batch` |

### 스키마 (`app/schemas.py`)

핵심 모델:
- `ProfileInput` — desired_role, skills, certificates, projects
- `CandidateJob` — job_id, position_title, company, tech_stack, requirements, preferred, main_tasks
- `RecommendJobsRequest` — profile + candidates(max 20) + market_demand_top
- `RecommendJobsResponse` — recommendations, strengths, gaps, roadmap, policy_violation
- `RoadmapStep` — order, title, **why, how, duration, outcome**
- `RoadmapResponse` — roadmap + summary (로드맵 전용 호출 응답)

### 설정 (`app/core/config.py`)

```python
openai_model: str = "gpt-4o-mini"           # 채점용 기본 모델
openai_roadmap_model: str = ""               # 로드맵용 (비면 openai_model 폴백)
max_tokens: int = 4000
mongodb_uri: str = ""                        # MongoDB Atlas
```

---

## 4. 매칭 엔진 아키텍처 (현재 구현 상태)

```
사용자 프로필
    │
    ▼
┌─────────────────────────────────────────────────┐
│ Phase 0: 전처리 (LLM 0회)                        │
│  ├─ demand_aggregator.aggregate_demand(jobs)     │
│  ├─ gap_analyzer.analyze_gap(profile, demand)    │
│  └─ matcher.retrieve_candidates(profile, pos)    │
│      ├─ role_score (routed_roles 매칭)            │
│      ├─ overlap_score (tech_stack 교집합)         │
│      ├─ 0점 후보 제외                             │
│      └─ 상위 ≤20개 선별                           │
└─────────────────────────────────────────────────┘
    │ 후보 ≤20개
    ▼
┌─────────────────────────────────────────────────┐
│ Phase 1: 배치 채점 (LLM 1콜)                     │
│  matcher.match_jobs() → gpt_gateway.chat_json()  │
│  입력: profile + candidates + market_demand_top   │
│  출력: recommendations, strengths, gaps           │
│  프롬프트: MATCH_JOBS_SYSTEM_PROMPT               │
└─────────────────────────────────────────────────┘
    │ include_roadmap=True 일 때
    ▼
┌─────────────────────────────────────────────────┐
│ Phase 2: 로드맵 생성 (LLM 1콜)                   │
│  matcher.generate_roadmap()                      │
│  입력: profile, gap_report, top_jobs(상위 5개)    │
│  출력: 5~6단계 roadmap (why/how/duration/outcome) │
│  프롬프트: ROADMAP_SYSTEM_PROMPT (한국어)          │
│  토큰: estimated=2500, max_output=3000            │
└─────────────────────────────────────────────────┘
```

**비용 원칙**: 사용자당 최대 2콜 (채점 1 + 로드맵 1). `include_roadmap=False`면 1콜.

---

## 5. 핵심 설계 결정 기록

| # | 결정 | 이유 |
|---|---|---|
| 1 | 벤치마크 기준을 "합격자 스펙" → "시장 수요(공고 집계)"로 전환 | 합격 후기 데이터 확보 불가 |
| 2 | Neo4j/Vector DB 대신 routed_roles 기반 결정론적 검색 | MVP 단계, 공고 수 수백 건 수준 |
| 3 | retrieval_score ≤ 0인 공고는 무조건 제외 | 무관 공고로 LLM 토큰 낭비 방지 |
| 4 | overlap 가중치 0.5 → 1.0 | 스킬 교집합이 role_score만큼 중요 |
| 5 | `core_skills` = pct ≥ 10% 필터 | 롱테일 스킬이 readiness 분모를 폭등시킴 |
| 6 | 로드맵을 채점과 별도 LLM 콜로 분리 | 한 콜에 다 담으면 토큰 분산돼 로드맵 빈약 |
| 7 | `client.beta.chat.completions.parse` 사용 | SDK 버전상 정식 경로 미동작, beta 경로 확인 |
| 8 | `chat_json`에 `max_output_tokens` 파라미터 추가 | 로드맵 호출에만 3000토큰 할당 |

---

## 6. 테스트 현황

```
tests/test_matcher.py    9 passed   coverage 99%
tests/test_gap_analyzer.py   통과
tests/test_demand_aggregator.py   통과
tests/test_gateway.py   통과
tests/test_router.py    통과
```

실행 방법:
```bash
cd backend/ai-api
pytest tests/ -v
pytest tests/test_matcher.py --cov=app.services.matcher
```

---

## 7. 환경 설정 (.env)

`.env` 파일은 3곳에 존재:
- `CareerStep/.env` (Docker Compose 전체)
- `backend/ai-api/.env` (AI 백엔드 로컬)
- `backend/crawler-api/.env` (크롤러 로컬)

> ⚠️ **현재 MongoDB Atlas 패스워드가 변경되어 인증 실패 상태** (`bad auth : authentication failed`). Atlas 콘솔에서 비밀번호 재설정 후 3개 `.env` 파일 모두 업데이트 필요.

---

## 8. 참고 문서

| 문서 | 위치 | 내용 |
|---|---|---|
| 아키텍처 | [ARCHITECTURE.md](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/docs/ARCHITECTURE.md) | MSA 구조, API 설계, DB 스키마 |
| 매칭 엔진 설계 | [matching-engine-design.md](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/docs/matching-engine-design.md) | 후보 검색, 수요 집계, LLM 매칭, 멀티에이전트 로드맵 |
| 전체 To-Do | [task.md](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/docs/task.md) | 우선순위별 작업 목록 |
| API 스펙 | [API_SPEC.md](file:///c:/Users/wlstj/Documents/CareerStep/CareerStep/docs/API_SPEC.md) | 엔드포인트 상세 |

---

## 9. 다음 세션 우선순위 과제

### 🔴 즉시

1. **MongoDB Atlas 패스워드 갱신** → `.env` 3개 업데이트 → `run_match.py --source mongo` 148개 전체 검증
2. **채점 프롬프트 한국어화** — `MATCH_JOBS_SYSTEM_PROMPT`에 `reason/strengths/gaps` 한국어 출력 규칙 추가 (현재 영어로 반환됨)
3. **로드맵 고품질 모델 분기 테스트** — `OPENAI_ROADMAP_MODEL=gpt-4o` 설정 후 로드맵 품질 비교

### 🟡 중간

4. **main-api 프록시 라우트** — `GET /api/recommendations/me` (JWT → Profile → ai-api 호출 체인)
5. **프론트엔드 연동** — `useRecommendStore.ts` 실데이터 연결, 로드맵 렌더링 UI
6. **크롤러 스케줄링** — APScheduler 기반 주기 수집, 증분 로직, 마감 공고 자동 처리

### 🟢 향후

7. **Vector DB 도입** — 공고 임베딩으로 의미 유사도 검색 고도화
8. **마일스톤 생성기 분리** — 가용시간·제약조건 입력 추가
9. **Docker Compose 통합 배포** — 전 서비스 통합 빌드·테스트
