# Antigravity 수정 지시 프롬프트 — Gap 분석기 / 집계 엔진 버그 픽스

> 대상 툴: Antigravity (Agent Coding) · 모델: Gemini 3.1 Pro
> 사용법: `=== 프롬프트 시작 ===` ~ `=== 프롬프트 끝 ===` 구간을 그대로 복사해 붙여넣으세요.
> 작업 디렉터리: `backend/ai-api/`
> 배경: 1차 구현은 잘 됐으나 데모(`gap_report.md`)에서 두 가지 문제가 발견됨. 아래를 수정한다.

---

=== 프롬프트 시작 ===

## 배경 / 문제 진단

직전에 구현한 Gap 분석기(`app/services/gap_analyzer.py`)와 시장 수요 집계(`app/services/demand_aggregator.py`)를 148개 전체 데이터로 돌린 결과 두 가지 문제가 확인됐다. 이를 수정하라.

### 문제 1 (중요) — `readiness_score` 가 비정상적으로 낮다
백엔드 핵심 스택(java 50%, springboot 23%, mysql, react)을 보유한 사용자의 적합도가 **13.4%** 로 나온다. 명백히 잘못됐다.

원인: 현재 공식이 `readiness = 보유스킬 pct합 / 전체 수요 tech_stack pct합` 인데, 한 직군의 `tech_stack` 에 "공고 1건에만 등장(pct≈1~2%)" 하는 **롱테일 스킬이 150개 이상** 있다. 이 꼬리들의 pct가 분모에 전부 더해져(분모≈7.3) 누가 와도 한 자릿수%가 된다. 즉 점수가 "핵심 역량 보유 여부"가 아니라 "희귀 스킬까지 다 가졌는지"를 재고 있다.

### 문제 2 — 집계 결과에 노이즈가 많다
- 롱테일: `count==1`(공고 1건만 등장) 스킬이 직군당 90~150개씩 → "외 151개" 같은 의미 없는 꼬리.
- 미정규화 표면형: `next.js`(→`nextjs`), `elk stack`(→`elk`), `auto cad`(→`autocad`) 등이 별도 항목으로 분리됨.

> 참고: 데이터분석가에 `mes`, `fdc`, `erp` 등 제조업 용어가 섞인 것은 **라우팅(router.py) 오분류** 이슈로, 이번 수정 범위에서 **제외**한다(별도 작업).

## 수정 1 — `app/services/demand_aggregator.py` (롱테일 컷 + 정규화 보강)

### 1-A. 롱테일 컷 파라미터 추가
`aggregate_demand(...)` 에 `min_count: int = 2` 파라미터를 추가한다.
- 각 직군의 `tech_stack` 을 최종 출력할 때 `count < min_count` 인 스킬은 **제외**한다(공고 단 1건에만 등장하는 스킬은 "시장 수요"로 보기 어렵다).
- `pct` 는 기존대로 `count / position_count` 로 계산하므로, 다른 스킬 제외와 무관하게 값이 바뀌지 않는다.
- `position_count`, `experience_level` 은 그대로 유지(컷은 tech_stack 표시에만 적용).
- `min_count=1` 이면 기존과 동일하게 전부 포함(하위호환).

### 1-B. alias 정규화 보강
`app/services/alias_dict.py` 의 `ALIAS_DICT` 에 아래 매핑을 추가한다(이미 있으면 생략). 표면형은 소문자/공백제거 기준 둘 다 매칭되도록 `normalize_text` 의 기존 동작에 맞춰 등록:
- `"next.js"` → `"nextjs"`, `"넥스트"` → `"nextjs"`
- `"elk stack"` → `"elk"`, `"elkstack"` → `"elk"`
- `"auto cad"` → `"autocad"`, `"오토캐드"` → `"autocad"`
- 그 외 `demand_profiles.json` 을 훑어보고 명백한 동의어/표기변형(대소문자·점·공백 차이)이 더 보이면 5~10개 범위에서 추가하고, 추가 목록을 보고에 적어라. (애매하면 추가하지 말 것 — 과교정 금지.)

## 수정 2 — `app/services/gap_analyzer.py` (핵심 수요 기준 점수)

### 2-A. "핵심 수요 스킬(core)" 개념 도입
한 직군의 `tech_stack`(pct 내림차순 정렬됨)에서 core 를 다음 규칙으로 산출하는 헬퍼를 추가하라:
```
CORE_PCT_THRESHOLD = 0.10   # 공고의 10% 이상이 요구하는 스킬을 '핵심 수요'로 본다
CORE_MIN_SKILLS = 5         # 임계값 통과 스킬이 이보다 적으면(희소 직군)
CORE_FALLBACK_TOP_K = 8     # 상위 K개를 core 로 사용

def core_skills(tech_stack: list[dict]) -> list[dict]:
    core = [t for t in tech_stack if t["pct"] >= CORE_PCT_THRESHOLD]
    if len(core) < CORE_MIN_SKILLS:
        core = tech_stack[:CORE_FALLBACK_TOP_K]   # 이미 pct 내림차순
    return core
```

### 2-B. `readiness_score` 를 core 기준으로 재정의
```
readiness_score = (사용자 보유 ∩ core 의 pct 합) / (core 의 pct 합)
```
- core 의 pct 합이 0이면 0.0. 소수 3자리 반올림, 범위 0~1.
- **롱테일이 분모에서 빠지므로** 핵심 스택 보유자는 정상적으로 높은 점수가 나온다.

### 2-C. `analyze_gap` 출력 스키마 조정
다음 필드로 정리한다(기존 필드명 최대한 유지, 의미만 core 기준으로):
```json
{
  "role": "백엔드개발자",
  "role_resolved": true,
  "position_count": 44,
  "readiness_score": 0.73,
  "matched_skills": [{"skill": "java", "pct": 0.5}, ...],     // 보유 ∩ 전체수요 (정보용, pct desc)
  "top_strengths": [{"skill": "java", "pct": 0.5}, ...],      // 보유 ∩ core (강점)
  "missing_core_skills": [{"skill": "aws", "pct": 0.18}, ...],// core 중 미보유 (= 학습 우선순위, pct desc)
  "missing_tail_count": 151,                                  // 전체수요 미보유 중 core 가 아닌 꼬리 개수
  "extra_skills": ["..."],                                    // 보유 − 전체수요
  "notes": []
}
```
- 기존 `missing_skills`(전체 미보유 나열)는 제거하고 `missing_core_skills` + `missing_tail_count` 로 대체한다.

### 2-D. `render_markdown` 갱신
- "학습 우선순위"는 `missing_core_skills` 만 표시하고, 꼬리는 "그 외 {missing_tail_count}개의 비핵심 스킬" 한 줄로 요약.
- "주요 강점"은 `top_strengths` 사용.
- readiness 가 core 기준임을 한 줄로 명시(예: "핵심 수요 스킬 기준 적합도").

## 검증용 계산 예시 (테스트가 이 값을 재현해야 함)
수요(가상): `java 0.75, spring 0.583, aws 0.5, redis 0.05`, 임계값 0.10 →
- core = `[java, spring, aws]` (redis 는 0.05 < 0.10 이라 제외)
- 사용자 보유 = `{java, spring}`
- readiness = (0.75 + 0.583) / (0.75 + 0.583 + 0.5) = 1.333 / 1.833 = **0.727**
- top_strengths = `[java, spring]`, missing_core_skills = `[aws]`

## 테스트 갱신 — `tests/test_gap_analyzer.py`
- 기존 `test_readiness_score` 를 위 계산 예시(0.727, 허용오차 0.01)로 **갱신**.
- 추가 `@pytest.mark.full`:
  - `test_core_threshold_excludes_tail`: 롱테일 스킬(pct<0.10)이 readiness 분모·missing_core_skills 에서 제외되는지.
  - `test_core_fallback_topk`: 임계값 통과 스킬이 5개 미만인 희소 직군에서 상위 8개로 fallback 되는지.
  - `test_missing_tail_count`: 전체 미보유 − core 미보유 개수가 `missing_tail_count` 와 일치하는지.
- `tests/test_demand_aggregator.py`(없으면 생성)에 `@pytest.mark.full` `test_min_count_filter`: `count==1` 스킬이 `min_count=2` 에서 제외되고 `min_count=1` 에서 포함되는지.

## 재실행 & 산출물 갱신
1. `python run_demand_agg.py --source samples` 로 `demand_profiles.json` 재생성(기존 파일이 쓰기 중단으로 잘려 있으니 덮어쓰기).
   - 가능하면 실 DB 버전도: `python run_demand_agg.py` (Atlas 접속 가능 시).
2. `python run_gap_analysis.py --source samples` 로 `gap_report.md` 재생성.
3. 백엔드 핵심 스택 보유 프로필의 readiness 가 **두 자릿수 후반~50%대** 로 정상화됐는지 콘솔로 확인.

## 완료 기준 (Definition of Done)
1. `pytest -m smoke` 및 `pytest tests/test_gap_analyzer.py tests/test_demand_aggregator.py -v` 전체 통과, 커버리지 60% 하한 유지.
2. 위 계산 예시(0.727) 테스트 통과.
3. 재생성된 `gap_report.md` 에서 핵심 스택 보유자 readiness 가 13%대가 아니라 정상 범위로 오름, 학습 우선순위가 core 스킬만 깔끔히 표시됨.
4. 새 pip 의존성 0개, LLM/네트워크 호출 0개, 순수 함수 유지.
5. 변경 요약(수정 파일·핵심 변경·추가한 alias 목록)을 한국어로 보고.

## 제약
- LLM/네트워크/DB 호출 금지(순수 로직). I/O는 `run_*.py` 에만.
- 새 의존성 추가 금지. `normalize_text` 재사용(직접 lower/replace 재구현 금지).
- 라우팅(router.py) 오분류는 이번 범위 아님 — 건드리지 말 것.

=== 프롬프트 끝 ===

---

## 참고: 수정 설계 의도 (붙여넣지 않아도 됨)
- **core 임계값 10% + 상위 8개 fallback**: 밀집 직군(백엔드)은 임계값으로 핵심만 추리고, 공고가 적은 희소 직군(블록체인 등)은 임계값 통과 스킬이 부족하니 상위 K개로 보정 → 두 경우 모두 분모가 합리적.
- **롱테일을 집계(min_count)와 점수(core) 양쪽에서 처리**: 집계 단계 `min_count=2` 가 공고 1건짜리 잡음을 원천 제거하고, gap 단계 core 임계값이 그 위에서 "핵심 수요"만 남긴다 — 두 장치는 상호 보완.
- **`missing_tail_count` 만 남긴 이유**: "외 151개"를 나열하면 사용자에게 무의미. 개수만 요약하고 학습 우선순위는 core 에 집중시켜 행동 가능한 조언으로 만든다.
