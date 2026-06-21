# CareerStep — 추천/매칭 API 명세 (프론트엔드용)

> 대상: 공고 목록 **배지 점수** + **맞춤 추천 페이지** UI 작업
> 짝 문서: [API_SPEC.md](./API_SPEC.md) (전체 API), [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)
> 범례: ✅ 구현됨 · 🚧 신규/구현 예정(프론트가 의존할 **계약**)

## Base URL

```text
https://careerstep-main-api.onrender.com/api/v1
```

보호 API는 로그인/회원가입에서 받은 access token 포함:

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

---

## 1. 두 가지 점수 개념 (중요)

UI에 두 종류의 점수가 등장하며 **출처와 의미가 다르다.**

| 구분 | 배지 점수 (badge) | 추천 점수 (match) |
| --- | --- | --- |
| 노출 위치 | 공고 **목록**의 각 카드 | **추천 페이지**의 추천 카드 |
| 계산 방식 | 결정론(스킬·직군 매칭), LLM 미사용 | LLM 채점 + 사유 + 로드맵 |
| 대상 공고 | 목록에 뜨는 모든 공고 | 상위 후보 ~20개만 |
| 갱신 시점 | 요청 시 즉석 계산(항상 최신) | 프로필 저장 시 백그라운드 재계산 |
| 응답 형태 | `match_badge` (아래 2장) | `RecommendJobsResponse` (아래 4장) |

> 한 줄 요약: **목록엔 싼 배지 점수, 추천 페이지엔 LLM 점수+로드맵.** 둘은 별개 API다.

---

## 2. 공고 목록 + 배지 점수 🚧

### `GET /jobs`

| 항목 | 값 |
| --- | --- |
| Auth | **선택**. 토큰 있으면 각 공고에 `match_badge` 포함, 없으면 `null` |
| Query | `sort=match` (선택, 배지 점수 내림차순) · `limit` (선택, 기본 60) |

### Response (200)

```json
[
  {
    "id": 49364191,
    "title": "백엔드 개발",
    "company": "회사명",
    "location": "서울",
    "employment_type": "신입",
    "skills": ["Java", "Spring Boot", "MySQL"],
    "description": "REST API 개발 ...",
    "match_badge": {
      "score": 82,
      "matched_skills": ["Java", "Spring Boot"]
    }
  }
]
```

### 필드

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | int | 공고 ID (저장/상세 조회 키) |
| `skills` | string[] | 공고 요구 기술 (최대 5개) |
| `match_badge` | object \| null | 비로그인 또는 프로필 미작성 시 `null` |
| `match_badge.score` | int (0–100) | 결정론 매칭 점수 = (직군점수 + 스킬교집합점수) / 2 × 100. 스킬·희망직군이 모두 비면 0 |
| `match_badge.matched_skills` | string[] | 사용자 보유 ∩ 공고 요구 (배지 툴팁용) |

### 프론트 처리 가이드

- `match_badge`가 `null`이면 배지를 숨기거나 "로그인 시 매칭 점수 확인" CTA로 대체.
- 점수 구간 색상 예: `≥70` 강조 / `40–69` 보통 / `<40` 흐리게. (구간 기준은 디자인 합의)
- 배지 점수는 **로드맵/사유를 포함하지 않는다.** 상세 분석은 추천 페이지로 유도.

---

## 3. 추천 트리거 — 프로필 저장 ✅(저장) / 🚧(자동 트리거)

프론트는 **별도 추천 호출이 필요 없다.** 프로필을 저장하면 서버가 백그라운드 재계산을 시작한다.

### `PUT /profiles/me`  (Auth 필수)

```json
{
  "desired_role": "백엔드 개발자",
  "skills": ["Java", "Spring Boot"],
  "certificates": ["정보처리기사"],
  "projects": ["쇼핑몰 API 개발"]
}
```

- 저장 즉시 `ProfileRead` 반환(기존과 동일, [API_SPEC.md](./API_SPEC.md) 참고).
- 🚧 저장 직후 서버가 추천 비동기 작업을 enqueue → 추천 상태가 `pending`이 된다.
- 따라서 **저장 성공 후 추천 페이지로 이동하면 `pending`부터 시작**하는 것이 정상.

---

## 4. 맞춤 추천 조회 (폴링) 🚧

### `GET /ai/recommendations/me`  (Auth 필수)

추천 페이지 진입 시, 그리고 `status: "pending"`인 동안 주기적으로(예: 3초 간격) 호출.

### Response (200) — 상태별 4가지

**(a) 아직 프로필 없음**
```json
{ "status": "no_data", "message": "프로필을 저장하면 추천이 생성됩니다." }
```

**(b) 생성 중** → 로딩 스피너
```json
{ "status": "pending", "message": "추천 결과를 생성 중입니다." }
```

**(c) 오류** → 재시도 안내
```json
{ "status": "error", "message": "추천 생성 중 오류가 발생했습니다." }
```

**(d) 완료** → 화면 렌더
```json
{
  "status": "done",
  "updated_at": "2026-06-21T07:30:00Z",
  "data": {
    "recommendations": [
      {
        "job_id": "49364191",
        "position_title": "백엔드 개발",
        "match_score": 82,
        "reason": "Java와 Spring Boot, 쇼핑몰 API 경험이 이커머스 백엔드와 잘 맞습니다.",
        "matched_skills": ["Java", "Spring Boot", "쇼핑몰 API 개발"],
        "missing_skills": ["MySQL 설계 및 최적화", "AWS", "Git"]
      }
    ],
    "strengths": ["Java/Spring Boot 기본 정합성이 높음", "쇼핑몰 API 경험"],
    "gaps": ["RDBMS 설계/최적화 경험 부족", "AWS/Docker 등 배포 역량 보강 필요"],
    "roadmap": [
      {
        "order": 1,
        "title": "Java/Spring Boot 백엔드 핵심 고도화",
        "why": "보유 스킬과 상위 공고 공통 요구가 겹쳐 가장 빠르게 합격 가능성을 높임",
        "how": "OOP 설계, 계층 구조, REST 설계 + 쇼핑몰 API 확장 미니 프로젝트",
        "duration": "2~3주",
        "outcome": "Spring Boot 실무 구조를 포트폴리오로 증명"
      }
    ],
    "policy_violation": false
  }
}
```

### `data` 필드 (status=done일 때만 존재)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `recommendations` | object[] | 추천 공고 목록 |
| `recommendations[].job_id` | string | 공고 ID (목록 `/jobs`의 `id`와 매칭 시 string↔int 변환 주의) |
| `recommendations[].position_title` | string | 포지션명 |
| `recommendations[].match_score` | int (0–100) | LLM 매칭 점수 |
| `recommendations[].reason` | string | 추천 사유 (카드 본문) |
| `recommendations[].matched_skills` | string[] | 보유 매칭 스킬 (칩) |
| `recommendations[].missing_skills` | string[] | 부족 스킬 (칩) |
| `strengths` | string[] | 종합 강점 패널 |
| `gaps` | string[] | 핵심 갭 패널 |
| `roadmap` | object[] | 학습 로드맵 (타임라인) |
| `roadmap[].order` | int | 단계 순서 |
| `roadmap[].title` / `why` / `how` / `duration` / `outcome` | string | 단계 제목/왜/어떻게/기간/완료역량 |
| `policy_violation` | bool | true면 안내 메시지로 대체 |

### 프론트 처리 가이드

- `recommendations`는 **`match_score` 내림차순으로 방어적으로 정렬**할 것 (서버 정렬을 신뢰하지 말 것 — 현재 정렬 보장 안 됨).
- `roadmap`은 `order` 기준 정렬해 타임라인으로 렌더.
- `job_id`는 string, 목록 `/jobs.id`는 int → 카드 연결 시 형 변환 통일.
- 폴링은 `done`/`error` 도달 시 중단. `pending` 최대 대기(예: 60초) 후 타임아웃 안내 권장.

### (선택) 수동 재생성 🚧

| Method | Endpoint | Auth | 설명 |
| --- | --- | --- | --- |
| POST | `/ai/recommendations/refresh` | Required | 프로필 변경 없이 추천 강제 재계산 → `{ "status": "processing" }` |

---

## 5. 상태 머신 (프론트 기준)

```
[프로필 저장] ──▶ pending ──(15~30초)──▶ done  (data 렌더)
                     │
                     └──▶ error  (재시도 버튼)

프로필 없음 ──▶ no_data  (프로필 작성 유도)
```

## 6. 미해결/주의

- `match_badge`, `/ai/recommendations/me` 프록시, 저장 시 자동 트리거는 🚧 **구현 예정**. 위 응답 형태는 확정 계약으로 간주하고 UI 선작업 가능.
- 추천 `recommendations` 정렬은 백엔드 수정 전까지 프론트에서 정렬.
- `gaps`에 사용자 직군과 무관한 대체 스택(예: Node.js/Python)이 섞일 수 있음 — 백엔드 정제 예정.
