# 📋 다음 작업 To-Do List

## ✅ 완료 (06.15 ~ 06.17)

### 0. GPT Gateway 구축 및 테스트 체계화 (`ai-api` 확장)
- [x] GPT Gateway 패키지 신설 (gateway/client.py, rate_limiter.py, usage_tracker.py)
- [x] ai-api 전체 비동기(Async) 전환 (AsyncOpenAI, aiosqlite, async def 라우터)
- [x] ai_usage 테이블 신설 (토큰/비용 추적)
- [x] 에러 분류별 차등 Fallback 로직 (429 재시도, 401 즉시 실패 등)
- [x] 기존 라우터(essay, recommendations) Gateway 연동 마이그레이션
- [x] pytest + pytest-asyncio 테스트 프레임워크 구축
- [x] smoke/full 마커 범주화 (3범주 11건 전체 PASS, 커버리지 62%)
- [x] 프로덕션/개발 의존성 분리 (requirements-dev.txt)

---

## 🔴 우선순위 높음 (다음 세션에서 즉시 진행)

### 1. GPT 요약 엔진 구현 (`ai-api` 확장)
- [ ] MongoDB `job_raw` 컬렉션에서 `status: "detailed"` 도큐먼트를 배치 단위로 조회하는 리더 구현
- [ ] **텍스트 공고** (`is_image_job == False`): `detail_markdown`을 가벼운 모델(`gpt-4o-mini`)에 전달하여 구조화된 JSON 요약 추출
  - 추출 항목 예시: 모집 분야, 자격 요건, 우대 사항, 기술 스택, 복지/혜택, 근무 조건
- [ ] **이미지 공고** (`is_image_job == True`): `image_urls`를 OpenAI Vision API(`gpt-4o`)에 전달하여 이미지 기반 요약 추출
- [ ] 요약 결과를 MongoDB `job_raw` 도큐먼트에 `summary` 필드로 업데이트하고 `status`를 `"summarized"`로 갱신
- [ ] 요약 프롬프트 설계 및 JSON 출력 스키마 정의

### 2. GPT 요약 프롬프트 최적화
- [ ] 다양한 공고 형식(테이블형, 리스트형, 혼합형)에 대응하는 범용 프롬프트 작성
- [ ] 10~20개 샘플로 요약 품질 검증 및 프롬프트 튜닝
- [ ] 비용 최적화: 텍스트 공고 → `gpt-4o-mini`, 이미지 공고 → `gpt-4o` 분기 처리

---

## 🟡 우선순위 중간

### 3. 크롤러 스케줄링 및 자동화
- [ ] 주기적 수집을 위한 스케줄러 구현 (예: APScheduler 또는 cron 기반)
- [ ] 이미 수집된 공고(`status: "detailed"` 이상)는 재수집하지 않는 증분 수집 로직 추가
- [ ] 마감된 공고를 자동으로 `status: "expired"` 처리하는 로직 구현

### 4. Docker Compose 통합 및 배포
- [ ] `docker-compose.yml`에 `crawler-api` 서비스의 환경변수(`.env`) 바인딩 확인
- [ ] 전체 서비스(`main-api`, `ai-api`, `crawler-api`) 통합 Docker Compose 빌드 및 테스트
- [ ] MongoDB Atlas 연결 헬스체크 추가

### 5. 프론트엔드 연동
- [ ] `main-api`에서 MongoDB `job_raw` 컬렉션의 요약된 공고 데이터를 조회하는 REST API 엔드포인트 구현
- [ ] 프론트엔드에서 채용 공고 목록/상세 페이지에 요약 데이터를 표시하는 UI 구현

---

## 🟢 우선순위 낮음 (추후)

### 6. 데이터 품질 고도화
- [ ] 태그(`tags`) 필드의 중복 키워드 정제 (예: "서버관리"가 2번 들어가는 경우)
- [ ] 공고 마감일(`deadline_raw`) 파싱 및 Date 타입 변환
- [ ] 수집 실패(`status: "failed"`) 공고에 대한 재시도(retry) 로직 추가

### 7. 모니터링 및 로깅
- [ ] 수집 배치 실행 결과를 Slack/Discord 웹훅으로 알림 전송
- [ ] 수집/요약 통계 대시보드 구현 (총 수집 건, 요약 완료 건, 실패 건 등)
