# Antigravity 수정 지시 프롬프트 — 매칭 엔진 retrieval 품질 + 테스트 강화

> 대상 툴: Antigravity (Agent Coding) · 모델: Gemini 3.1 Pro
> 사용법: `=== 프롬프트 시작 ===` ~ `=== 프롬프트 끝 ===` 구간을 그대로 복사해 붙여넣으세요.
> 작업 디렉터리: `backend/ai-api/`
> 배경: 매칭 엔진 1차 구현은 잘 됐으나, 검증 중 3가지 문제가 발견됨. 아래를 수정한다.

---

=== 프롬프트 시작 ===

## 배경 / 문제 진단

`app/services/matcher.py` 매칭 엔진을 실제 샘플로 검증한 결과 3가지 문제가 확인됐다.

### 문제 1 (중요) — "정확히 1회 LLM 호출" 테스트가 실제로는 1회를 검증하지 않음
`tests/test_matcher.py` 의 `test_match_jobs_single_call` 이 커스텀 mock 의 `.called is True`(불리언)만 확인한다. 이건 "한 번이라도 호출됐는가"이지 "정확히 1번 호출됐는가"가 아니다. 버그로 5번 호출해도 통과한다. **호출 횟수를 세서 정확히 1이어야 함을 단언**하도록 고쳐라.

### 문제 2 (중요) — retrieval fallback 이 무관(0점) 공고로 후보를 채움
`retrieve_candidates` 의 현재 fallback 은 "후보가 top_k 미만이면 전체를 retrieval_score 순으로 정렬해 max_k 개"를 취한다. 그 결과 직군이 전혀 안 맞는 `retrieval_score==0` 공고(예: 정비사, 디테일링 팀원)까지 끌려와 LLM 채점 대상이 된다(토큰 낭비 + 채점 혼선).

### 문제 3 — overlap 가중이 약해 신호 없는 잡음이 상위로 뜸
현재 `retrieval_score = role_score + overlap_score * 0.5`. `tech_stack`이 비어 있고 라우터 점수만 높은 포지션(예: 단일 키워드로 score=1.0이 된 비개발 공고)이, 실제 스킬이 겹치는 진짜 적합 공고보다 위에 랭크된다.

## 작업 전 읽을 파일
- `app/services/matcher.py` — `retrieve_candidates`, `match_jobs`.
- `app/services/gap_analyzer.py` — `resolve_role`(인접 직군 fallback에 활용 가능).
- `tests/test_matcher.py`, `tests/conftest.py`.

## 수정 1 — `retrieve_candidates` (matcher.py)

### 1-A. 0점 후보 절대 포함 금지
최종 반환 후보에서 **`retrieval_score <= 0` 인 항목은 무조건 제외**한다. 그 결과 후보가 `top_k`(또는 `max_k`)보다 적어도 그대로 둔다 — **무관 공고로 억지로 채우지 않는다.** (LLM에 0점 공고를 보내느니 후보가 적은 게 낫다.)

### 1-B. fallback 을 "인접/2·3순위 직군"으로 (전체 무차별 정렬 금지)
1순위 직군 일치 후보(`role_score > 0`)가 `top_k` 미만이면:
- 각 포지션의 `routed_roles` 중 **rank 2·3 직군까지** 사용자 해석 직군과 일치하는지 확인해 그 score 를 `role_score` 로 인정(인접 직군 확장).
- 그래도 0점인 포지션은 후보에서 제외(1-A 적용).
- 즉 fallback 은 "관련 있는 후보를 더 넓게 인정"하는 것이지, "관련 없는 공고를 채우는" 것이 아니다.

### 1-C. overlap 가중 상향 + 신호 가드
- `retrieval_score = role_score + overlap_score * 1.0` 으로 overlap 비중을 높인다(기존 0.5 → 1.0).
- 정렬 시 동점이면 `overlap_score` 가 높은 쪽을 우선(스킬 신호가 있는 후보 우대).
- (선택) `tech_stack` 이 비어 있고 `requirements`·`main_tasks` 도 비어 있는 "내용 없는" 포지션은 후보에서 제외하는 가드를 둔다.

> 참고: 라우터(router.py)의 점수 정규화 자체(빈약한 텍스트에 score=1.0)는 이번 범위 밖이다. 여기서는 matcher 단에서 overlap 가중·0점 제외로 영향을 완화만 한다. router.py 는 수정하지 말 것.

## 수정 2 — `test_match_jobs_single_call` 강화 (tests/test_matcher.py)
- mock 이 **호출 횟수(call_count)** 를 세도록 바꾼다(예: `unittest.mock.AsyncMock` 사용 또는 커스텀 카운터).
- `assert mock_chat.call_count == 1` 로 **정확히 1회**를 단언한다. (`.called` 불리언 단언은 제거/대체.)

## 수정 3 — retrieval 품질 테스트 추가 (tests/test_matcher.py)
- `@pytest.mark.full test_retrieve_excludes_zero_score`: 직군도 안 맞고 스킬도 안 겹치는 포지션(=retrieval_score 0)이 결과에 **포함되지 않음**을 단언. 관련 후보가 top_k 미만이어도 0점이 채워지지 않는지 확인.
- `@pytest.mark.full test_retrieve_overlap_priority`: role_score 만 높고 tech_stack 빈 포지션보다, role_score 는 약간 낮아도 사용자 스킬이 겹치는 포지션이 **상위**에 오는지 단언.

## 재검증 (코드 변경 후)
1. `pytest tests/test_matcher.py -v` 전체 통과(신규 테스트 포함), 커버리지 60% 유지.
2. `python run_match.py --source samples` 실행 시, 후보 목록에 **정비사·디테일링 같은 0점 무관 공고가 사라졌는지** 콘솔로 확인.

## 완료 기준 (DoD)
1. `test_match_jobs_single_call` 이 `call_count == 1` 로 정확히 1회를 검증.
2. retrieval 결과에 `retrieval_score<=0` 후보가 없음(테스트로 보장).
3. 스킬 겹치는 후보가 빈-tech 잡음보다 상위(테스트로 보장).
4. `run_match.py --source samples` 후보 목록이 1차보다 깨끗해짐.
5. 새 의존성 0개, router.py 미변경, LLM 호출은 여전히 사용자당 1회. 변경 요약을 한국어로 보고.

## 제약
- LLM 호출은 `gpt_gateway.chat_json` 경유, 사용자당 1회 유지(후보 루프 내 호출 금지).
- retrieval 은 순수 함수 유지(파일/네트워크/LLM 금지).
- router.py 는 건드리지 말 것.

=== 프롬프트 끝 ===

---

## 참고: 수정 의도 (붙여넣지 않아도 됨)
- **0점 제외 > 억지 채움**: 후보가 5개뿐이면 5개만 LLM에 보내는 게, 무관 공고 15개를 섞어 보내는 것보다 비용·품질 모두 낫다.
- **인접 직군 fallback**: 원래 설계 의도(§4)는 "2·3순위 직군 확장"이었는데 1차 구현이 "전체 무차별 정렬"로 단순화되며 잡음이 들어왔다. 이를 설계 의도대로 되돌리는 것.
- **overlap 가중 ↑**: 라우터의 sparse-text score=1.0 잡음을 matcher 단에서 상쇄. 근본 수정(router 정규화)은 별도 작업으로 남김.
- 실데이터 148개에선 dense 직군은 fallback 자체가 잘 안 걸리지만, sparse 직군(블록체인 등)에서 이 수정이 품질을 지켜준다.
