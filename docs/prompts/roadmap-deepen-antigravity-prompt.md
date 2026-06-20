# Antigravity 작업 지시 프롬프트 — 로드맵 심화 (별도 LLM 호출 분리)

> 대상 툴: Antigravity (Agent Coding) · 모델: Gemini 3.1 Pro
> 사용법: `=== 프롬프트 시작 ===` ~ `=== 프롬프트 끝 ===` 구간을 그대로 복사해 붙여넣으세요.
> 작업 디렉터리: `backend/ai-api/`
> 배경: 매칭(채점/정렬/한국어/보완 로드맵)은 완료됨. 다만 로드맵이 3단계·한 줄짜리로 빈약하다. 로드맵을 **전용 LLM 호출로 분리**해 깊게 만든다(설계문서 §10 Phase 2).

---

=== 프롬프트 시작 ===

## 역할 / 목표

너는 CareerStep 백엔드 엔지니어다. 현재 매칭 엔진은 **단일 LLM 호출**로 공고 채점 + 종합 강점/갭/로드맵을 한꺼번에 만든다. 이 때문에 로드맵이 3단계·한 줄 설명으로 빈약하다.

목표: **로드맵 생성을 전용 LLM 호출로 분리**하여 깊고 실행 가능한 로드맵을 만든다. 채점 호출은 그대로 두고(가성비 모델, 후보 ≤20 배치 1콜), 로드맵만 별도 1콜(고품질 모델)로 생성한다.

### 비용 원칙 (중요)
- 채점(`/recommend/jobs`)은 **사용자당 LLM 1회** 유지(기존 그대로). 후보 루프 안에서 호출 금지.
- 로드맵은 **사용자당 추가 1회**(공고 수와 무관, 1콜). 즉 "matching + roadmap" 전체 = 사용자당 **정확히 2콜**.
- 로드맵 호출은 `include_roadmap` 플래그로 켜고 끌 수 있게 한다(기본 True). 끄면 채점만 = 1콜.

## 작업 전 읽을 파일
- `app/services/matcher.py` — `match_jobs`, `retrieve_candidates`.
- `app/services/gap_analyzer.py` — `analyze_gap`(missing_core_skills/top_strengths/readiness 반환).
- `app/services/prompts.py` — `MATCH_JOBS_SYSTEM_PROMPT`.
- `app/schemas.py` — `RoadmapStep`, `RecommendJobsResponse`.
- `app/gateway/client.py` — `chat_json(system_prompt, payload, endpoint, response_format, model=None, estimated_tokens=...)`.
- `app/core/config.py` — `openai_model`, `max_tokens`.
- `app/routers/resume.py` 또는 `essay.py` — `chat_json` 을 `response_format` 과 함께 쓰는 현행 예시.

## 구현 1 — 스키마 (`app/schemas.py`)
`RoadmapStep` 을 풍부하게 교체한다(기존 `order`, `title` 유지, `description` 제거하고 아래로 확장):
```python
class RoadmapStep(BaseModel):
    order: int
    title: str          # 예: "AWS 클라우드 기초 다지기"
    why: str            # 왜 필요한가 — 사용자 갭/목표 직무·시장 수요 근거
    how: str            # 어떻게 — 구체적 학습 주제 + 실습/미니 프로젝트 제안
    duration: str       # 예상 소요 기간 (예: "2~3주")
    outcome: str        # 완료 시 갖추게 될 역량/산출물 (예: "EC2에 Spring Boot 앱 배포 경험")
```
- 로드맵 전용 응답 모델 추가:
```python
class RoadmapResponse(BaseModel):
    roadmap: list[RoadmapStep]
    summary: str        # 로드맵 전체를 1~2문장으로 요약한 방향성
```
- `RecommendJobsResponse.roadmap` 의 타입은 위 확장된 `RoadmapStep` 을 그대로 사용. (채점 호출은 더 이상 roadmap 을 채우지 않아도 되며, 빈 리스트를 반환하면 됨 — 아래 프롬프트 참고.)
- 모든 변경 모델은 `resume.py`/`essay.py` 가 쓰는 Structured Outputs 패턴과 호환되게(불필요한 숫자 제약 `ge/le` 등은 피함).

## 구현 2 — 프롬프트 (`app/services/prompts.py`)
### 2-A. 채점 프롬프트 슬림화
`MATCH_JOBS_SYSTEM_PROMPT` 에서 종합 `roadmap` 생성 책임을 **제거**한다. 채점 호출은 `recommendations`, `strengths`, `gaps`, `policy_violation` 만 충실히 만들고 `roadmap` 은 빈 배열(`[]`)로 두라고 명시. (강점/갭은 유지 — 로드맵 호출의 입력이 됨.)

### 2-B. 로드맵 전용 프롬프트 신규 `ROADMAP_SYSTEM_PROMPT`
요구사항:
- 입력으로 `profile`(보유 스킬/자격/프로젝트), `gap`(부족 핵심 스킬), `market_demand_top`(직군 수요), `top_jobs`(상위 매칭 공고들의 requirements/preferred 요약)를 받는다.
- **5~6단계**의 단계별 로드맵을 만든다. 각 단계는 `title/why/how/duration/outcome` 를 모두 채운다.
- **즉시 → 단기 → 중기** 순으로 난이도·우선순위가 올라가도록 정렬.
- 각 단계의 `how` 는 추상적 조언("AWS를 배우세요") 금지. **구체적**으로: 학습 주제, 추천 실습/미니 프로젝트, 가능하면 사용자의 기존 프로젝트를 어떻게 확장할지 제시.
- **보완 원칙**: 사용자의 현재 스택(예: Java/Spring)을 심화·확장하는 방향(AWS, Docker/K8s, MySQL/JPA, 테스트, CI/CD 등). 대체 스택(Python/Node 등)은 추천하지 않음 — 단, 목표 직무 대다수가 요구하는 사실상 필수면 예외(근거를 why에 명시).
- **근거 연결**: `why` 는 사용자의 실제 갭과 `top_jobs` 의 공통 요구사항/시장 수요에 연결.
- Guardrail: 사용자가 갖지 않은 경력·자격·프로젝트를 지어내지 말 것.
- **언어**: 모든 텍스트 한국어, 기술명은 원문(Java, AWS 등) 유지.
- 유효한 JSON만 출력.

## 구현 3 — 모델 라우팅 (`app/core/config.py`)
- `openai_roadmap_model: str = ""` 설정 추가. 비어 있으면 `openai_model` 로 폴백.
- (의도: 채점은 가성비 모델, 로드맵은 더 강한 모델. 환경변수로 교체 가능.)

## 구현 4 — matcher (`app/services/matcher.py`)
### 4-A. `generate_roadmap(profile, gap_report, demand, top_jobs, model=None) -> RoadmapResponse`
- `top_jobs`: 채점 결과 상위 N개(예: 5)의 컴팩트 요약(position_title, requirements, preferred). 로드맵을 실제 목표 공고에 맞추기 위함.
- `gpt_gateway.chat_json(system_prompt=ROADMAP_SYSTEM_PROMPT, payload={...}, endpoint="/recommend/roadmap", response_format=RoadmapResponse, model=model or settings.openai_roadmap_model or settings.openai_model)` 를 **단 1회** 호출.
- 출력이 잘리지 않도록 충분한 출력 토큰 확보: 로드맵 호출은 `estimated_tokens` 를 넉넉히(예: 2500) 전달. 만약 `chat_json` 이 `settings.max_tokens` 를 하드코딩해 출력이 truncate 되면, `chat_json` 에 `max_tokens` 오버라이드 파라미터를 추가해 로드맵 호출에만 큰 값(예: 2500~3000)을 주도록 보강.

### 4-B. `match_jobs(..., include_roadmap: bool = True)`
- 기존 채점 호출(1콜) 수행 → `recommendations` 정렬(기존 유지).
- `include_roadmap` 가 True면:
  - 상위 5개 추천을 `top_jobs` 컨텍스트로 만들고,
  - `generate_roadmap(...)` 1콜 실행,
  - 결과의 `roadmap` 을 `RecommendJobsResponse.roadmap` 에 채워 반환.
- False면 채점만(1콜) 반환, roadmap 은 빈 배열.

## 구현 5 — 데모 렌더 (`run_match.py`)
- 로드맵 출력부를 확장 필드(why/how/duration/outcome)에 맞춰 갱신. 각 단계를 제목 + 왜/어떻게/기간/완료시 역량으로 보기 좋게 출력.

## 구현 6 — 테스트 (`tests/test_matcher.py`)
- 기존 "정확히 1회" 테스트는 **채점 단독**(`include_roadmap=False`)에서 chat_json `call_count == 1` 로 유지.
- 신규 `@pytest.mark.full test_match_with_roadmap_two_calls`: `include_roadmap=True` 일 때 chat_json 이 **정확히 2회**(채점 1 + 로드맵 1) 호출되는지 단언.
- 신규 `@pytest.mark.full test_generate_roadmap`: mock 응답으로 `generate_roadmap` 이 `RoadmapResponse`(5~6 step 가정 불필요, 구조만) 를 반환하고 각 step 에 why/how/duration/outcome 키가 있는지 검증.

## 재검증
1. `pytest tests/test_matcher.py -v` 전체 통과, 커버리지 60% 유지.
2. `python run_match.py --source mongo` → `match_report.md` 확인:
   - 로드맵이 **5~6단계**, 각 단계에 왜/어떻게/기간/완료역량이 **구체적으로** 채워졌는가
   - 한국어, 보완 스킬 위주(대체 스택 아님)
   - 콘솔/로그에 채점 1회 + 로드맵 1회 = 총 2회 호출이 보이는가

## 완료 기준 (DoD)
1. 로드맵이 전용 호출로 분리되어 5~6단계·구체 설명(why/how/duration/outcome)으로 생성됨.
2. 채점 호출은 여전히 1콜, 전체(matching+roadmap)는 사용자당 정확히 2콜(테스트로 보장).
3. 출력 한국어, 보완 원칙 유지, Guardrail 유지.
4. 새 pip 의존성 0개, `router.py`·`demand_aggregator.py` 미변경.
5. 변경 요약(파일별 변경, 추가 설정, 호출 수 변화)을 한국어로 보고.

## 제약
- LLM 호출은 `gpt_gateway.chat_json` 경유. 채점 1콜 + 로드맵 1콜 외 추가 호출 금지(공고 루프 내 호출 절대 금지).
- 정렬·retrieval·집계 로직은 변경하지 말 것(이미 검증됨).

=== 프롬프트 끝 ===

---

## 참고: 설계 의도 (붙여넣지 않아도 됨)
- **왜 분리하나**: 한 번의 호출에 20개 채점 + 로드맵을 다 담으면 토큰이 분산돼 로드맵이 빈약해진다. 채점(구조적·기계적)과 로드맵(창의적·심층)은 성격이 달라 분리가 품질·비용 모두 유리. 이게 설계문서 §10 Phase 2.
- **비용**: 사용자당 2콜로 늘지만 공고 수와 무관하게 일정. 로드맵만 고급 모델로 돌려 핵심 가치(조언 품질)에 투자.
- **top_jobs 컨텍스트**: 로드맵을 "일반론"이 아니라 "당신의 상위 매칭 공고들이 공통으로 원하는 것"에 맞춰 구체화하는 장치.
- 채점은 이미 잘 되므로 건드리지 않는다. 이번은 로드맵 레이어만.
