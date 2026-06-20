# Antigravity 수정 지시 프롬프트 — 매칭 결과 정렬·한국어·로드맵 개선

> 대상 툴: Antigravity (Agent Coding) · 모델: Gemini 3.1 Pro
> 사용법: `=== 프롬프트 시작 ===` ~ `=== 프롬프트 끝 ===` 구간을 그대로 복사해 붙여넣으세요.
> 작업 디렉터리: `backend/ai-api/`
> 배경: 실데이터 148건 매칭 검증 결과 per-job 채점은 양호. 다음 3가지만 개선한다.

---

=== 프롬프트 시작 ===

## 배경 / 목표

매칭 엔진(`app/services/matcher.py`, `app/services/prompts.py`)을 실데이터로 검증한 결과 채점 품질은 양호했다. 다만 결과 표현·로드맵에서 3가지를 개선한다. 기능 추가가 아니라 **품질 다듬기**다.

### 개선 1 — 추천 결과를 매칭 점수 내림차순으로 정렬
현재 `recommendations` 가 retrieval 순서(점수 뒤섞임: 10→90→70→…)로 반환된다. 가장 잘 맞는 공고가 맨 위에 오도록 **`match_score` 내림차순 정렬**해야 한다.

### 개선 2 — LLM 출력 언어를 한국어로
현재 `reason`, `strengths`, `gaps`, `roadmap` 이 영어로 나온다. 한국어 서비스이므로 **모두 한국어로 출력**해야 한다.

### 개선 3 — 로드맵/갭을 "사용자 스택의 보완"으로 (대체 스택 추천 금지)
현재 종합 `gaps`/`roadmap` 이 `market_demand_top`(직군 전체 수요 빈도) 기준이라, Java/Spring 개발자에게 "Python 배워라, Node.js 배워라"처럼 **대체(substitute) 스택**을 추천한다. 이는 부족이 아니라 다른 길이다. 로드맵은 사용자의 현재 스택 생태계를 **보완(complement)** 하는 방향이어야 한다(예: Java/Spring 보유자 → AWS, Docker, MySQL, 테스트, JPA, CI/CD 등).

## 작업 전 읽을 파일
- `app/services/prompts.py` — `MATCH_JOBS_SYSTEM_PROMPT`.
- `app/services/matcher.py` — `match_jobs` (응답 파싱부).
- `tests/test_matcher.py`, `tests/conftest.py`.

## 수정 1 — 정렬 (`app/services/matcher.py`)
- `match_jobs` 에서 `gpt_gateway.chat_json` 결과를 `RecommendJobsResponse` 로 검증한 뒤, **반환 전에 `recommendations` 를 `match_score` 내림차순으로 정렬**한다.
- 정렬은 코드에서 결정론적으로 수행한다(LLM 출력 순서에 의존하지 않기 위함). 동점이면 순서 유지(안정 정렬).
- 예: `response.recommendations.sort(key=lambda r: r.match_score, reverse=True)` (Pydantic 모델 리스트 정렬).

## 수정 2 + 3 — 프롬프트 (`app/services/prompts.py`, `MATCH_JOBS_SYSTEM_PROMPT`)
기존 지시는 유지하고 아래를 반영한다.

- **언어**: 다음 한 줄을 명확히 추가 — "모든 `reason`, `strengths`, `gaps`, `roadmap` 의 텍스트는 반드시 한국어로 작성한다. 기술명/고유명사(예: Java, AWS)는 원문 표기를 유지한다." (`match_score` 등 숫자/필드명은 그대로.)
- **로드맵/갭 기준 변경**: 기존의 "prioritize the most frequent skills in `market_demand_top`" 지시를 다음으로 **대체**한다:
  - 종합 `gaps`/`roadmap` 은 사용자의 현재 보유 스킬 **생태계를 보완하는** 스킬을 우선한다.
  - 사용자가 이미 보유한 스택과 **대체 관계인 다른 언어/프레임워크**(예: Java 보유자에게 Python·Node.js, React 보유자에게 Vue 등)는 `market_demand_top` 에 자주 등장하더라도 **로드맵 상위로 추천하지 않는다.**
  - 대신 사용자의 스택을 심화/확장하는 인접 역량(예: Java/Spring → 클라우드(AWS), 컨테이너(Docker/K8s), DB(MySQL/JPA), 테스트, CI/CD)을 우선한다.
  - 단, 어떤 스킬이 사용자 직군에서 **사실상 필수**(공고 대다수가 요구)라면 대체 스택이라도 갭에 포함할 수 있다 — 판단 근거를 reason/roadmap 설명에 녹인다.
- 이 변경에도 기존 **Guardrail**(없는 경력·자격·프로젝트 날조 금지, `policy_violation`)과 "유효 JSON만 출력"은 그대로 유지한다.

## 테스트 — `tests/test_matcher.py`
- `@pytest.mark.full test_recommendations_sorted_desc`: mock 응답에 점수가 뒤섞인 추천 여러 개를 주고, `match_jobs` 반환의 `recommendations` 가 `match_score` 내림차순인지 단언.
- (프롬프트 텍스트 변경은 단위테스트로 검증이 어려우므로) 기존 `test_match_jobs_single_call` 등은 그대로 통과 유지.

## 재검증
1. `pytest tests/test_matcher.py -v` 전체 통과(신규 정렬 테스트 포함), 커버리지 60% 유지.
2. `python run_match.py --source mongo` (또는 samples) 재실행 → `match_report.md` 확인:
   - 추천이 **높은 점수부터** 정렬돼 있는가
   - `reason`/`gaps`/`roadmap` 이 **한국어**인가
   - 로드맵이 Java/Spring 보유자에게 Python·Node.js 같은 대체 스택 대신 **보완 스킬(AWS/Docker/MySQL/테스트 등)** 위주인가

## 완료 기준 (DoD)
1. 추천이 `match_score` 내림차순으로 반환됨(테스트로 보장).
2. LLM 출력 텍스트가 한국어.
3. 로드맵이 대체 스택이 아닌 보완 스킬 위주.
4. 새 의존성 0개, LLM 호출 여전히 사용자당 1회, `router.py` 미변경.
5. 변경 요약을 한국어로 보고.

## 제약
- 정렬은 코드(matcher)에서 수행(LLM 순서 의존 금지).
- LLM 호출은 `gpt_gateway.chat_json` 경유, 사용자당 1회 유지.
- `router.py`·집계 로직(`demand_aggregator.py`)은 변경하지 말 것.

=== 프롬프트 끝 ===

---

## 참고: 수정 의도 (붙여넣지 않아도 됨)
- **정렬은 코드에서**: LLM에 "정렬해 달라"고 맡기면 들쭉날쭉하니 결정론적으로 코드 정렬이 안전.
- **보완 vs 대체**: 이게 이번 핵심. "시장 수요 빈도"만 보면 다수 직군에 흔한 Python/Node가 항상 상위로 올라와 Java 개발자에게도 추천되는 왜곡이 생긴다. 로드맵 가치는 "내 스택을 어떻게 키울까"이지 "남들이 많이 쓰는 다른 언어"가 아니다.
- per-job 채점은 이미 잘 되므로 건드리지 않는다. 이번은 표현·로드맵 레이어만.
