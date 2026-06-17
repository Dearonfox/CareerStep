# 작업 일지 — 2026.06.13 (토)

## 📌 프로젝트 개요

**CareerStep** 프로젝트의 `backend/crawler-api` 모듈을 신규 구축하여, 잡코리아 IT 채용 공고를 자동 수집하고 MongoDB Atlas 클라우드 데이터베이스에 적재하는 **경량 ELT 파이프라인**을 완성했습니다.

---

## 완료된 작업 목록

### 1. 크롤러 파이프라인 설계 및 구현

| 파일 | 역할 |
|------|------|
| config.py | 26개 IT 직무 카테고리 코드 매핑, 수집 설정값, MongoDB URI 환경변수 로딩 |
| crawler.py | 잡코리아 목록 API + 상세 iframe API 크롤링, html2text 마크다운 변환, 이미지 공고 자동 감지 |
| db.py | PyMongo Atlas 연동, job_id 기반 Upsert, 상세 정보 개별 업데이트 |
| run.py | 1단계 목록 수집 → 2단계 상세 마크다운/이미지 수집 → MongoDB 적재 배치 오케스트레이터 |
| requirements.txt | requests, beautifulsoup4, pymongo, dnspython, html2text, python-dotenv |
| Dockerfile | 경량 Python 컨테이너 이미지 정의 |

### 2. 핵심 기술적 결정 사항

- **상세 JD 우회 수집**: GI_Read_Comt_Ifrm iframe API를 직접 호출하여 불필요한 UI 리소스 없이 순수 본문만 추출
- **마크다운 변환 엔진**: html2text 라이브러리로 HTML 구조(테이블, 리스트)를 보존한 채 콤팩트한 마크다운으로 변환 (용량 약 1/10 절약)
- **이미지 공고 판별**: 본문 텍스트 150자 미만 + 이미지 존재 시 is_image_job = True로 자동 분류
- **MongoDB 스키마**: _id = job_id로 Upsert하여 중복 적재 방지, status 필드로 파이프라인 진행 상태 추적 (pending → detailed → failed)

### 3. 버그 수정 및 개선

| 이슈 | 원인 | 해결 |
|------|------|------|
| 이미지 URL 중복 수집 | 동일 이미지가 HTML에 여러 번 삽입된 공고 | 순서 보존 중복 필터 추가 |
| UnicodeEncodeError (cp949) | 윈도우 터미널에서 유니코드 이모지 출력 불가 | 이모지를 텍스트 태그로 치환 |
| raw_list.json Git 커밋 노출 | 데이터 파일이 실수로 커밋됨 | git filter-branch로 과거 히스토리에서 완전 삭제 + .gitignore 등록 + git push --force |

### 4. 최종 수집 결과

- **수집 대상**: 잡코리아 IT 26개 카테고리 × 상위 10개 = 최대 260개
- **중복 제거 후**: 고유 **148개** 채용 공고
- **적재 대상**: MongoDB Atlas careerstep DB → job_raw 컬렉션
- **적재 상태**: 전체 148개 도큐먼트 status: detailed 완료

### 5. Git 작업

- 브랜치: feature/crawling → main 병합 (Fast-forward)
- 원격 저장소: GitHub (Dearonfox/CareerStep) 강제 푸시 완료
- .gitignore에 backend/crawler-api/data/ 및 backend/crawler-api/samplefile/ 추가

---
---

# 작업 일지 — 2026.06.15 (일) ~ 06.17 (화)

## 📌 작업 개요

`backend/ai-api` 모듈에 **GPT Gateway 레이어**를 신규 구축하여 OpenAI API 호출의 안정성·비용 추적·동시성 제어를 일원화하고, **pytest 기반 테스트 프레임워크**를 체계적으로 구성했습니다.

---

## 완료된 작업 목록

### 1. GPT Gateway 설계 및 구현 (06.15)

기존 `openai_client.py`의 직접 호출 방식을 대체하는 Gateway 패키지를 신설했습니다.

| 파일 | 역할 |
|------|------|
| gateway/client.py | AsyncOpenAI를 래핑한 GPTGateway 클래스. chat_json() 단일 진입점으로 에러 재시도, rate limit, 로깅을 자동 처리 |
| gateway/rate_limiter.py | asyncio.Semaphore + Sliding Window 기반 RPM/TPM 선제 쓰로틀링 |
| gateway/usage_tracker.py | 모델별 단가(gpt-4o-mini, gpt-4o)에 근거한 실시간 비용 산정 및 DB 적재 |
| gateway/__init__.py | gpt_gateway 싱글톤 인스턴스 노출 |

### 2. 비동기(Async) 전환 (06.15)

| 변경 대상 | 변경 내용 |
|-----------|----------|
| core/logging.py | aiosqlite 기반 비동기 SQLite 로깅 + ai_usage 테이블 신설 |
| core/config.py | Gateway 제어 설정 추가 (rpm_limit, tpm_limit, max_retries, concurrency_limit) |
| routers/essay.py | async def + gpt_gateway.chat_json() 연동 |
| routers/recommendations.py | async def + gpt_gateway.chat_json() 연동 |
| main.py | FastAPI lifespan 이벤트로 비동기 DB 초기화 |
| services/openai_client.py | Deprecated (gateway로 대체) |

### 3. 핵심 기술적 결정 사항

- **Facade 패턴 적용**: 호출자는 프롬프트+데이터만 전달하고, Gateway가 rate limit / retry / 로깅 / 비용 추적을 전담
- **에러 분류별 차등 Fallback**: 429/5xx → Exponential Backoff 재시도, 401/400 → 즉시 실패, JSON 파싱 에러 → 재시도
- **토큰 사용량 선예약**: 호출 전 예상 토큰을 임시 할당 → 완료 후 실제 소모량으로 보정
- **비용 자동 산정**: OpenAI 모델별 공식 단가표 기반 USD 비용 실시간 계산 및 SQLite 적재

### 4. 테스트 프레임워크 구축 (06.17)

루트에 방치된 임시 테스트 스크립트를 삭제하고, pytest 기반 체계적 테스트 구조를 구성했습니다.

| 파일 | 범주 | smoke | full | 합계 |
|------|------|-------|------|------|
| tests/conftest.py | 공용 피처 (DB격리, Gateway격리, Mock팩토리) | - | - | - |
| tests/test_retry.py | 에러 폴백/재시도 | 1 | 4 | 5 |
| tests/test_concurrency.py | 동시성 제어 | 1 | 1 | 2 |
| tests/test_tracking.py | 사용량/비용 기록 | 1 | 3 | 4 |
| **합계** | | **3** | **8** | **11** |

**테스트 인프라 특징:**
- **의존성 분리**: requirements-dev.txt로 프로덕션과 테스트 패키지 격리
- **pytest 마커 범주화**: `smoke`(대표 3건 빠른 검증) / `full`(상세 8건 꼼꼼한 검증) / 범주별 마커(`retry`, `concurrency`, `tracking`)
- **테스트 격리**: tmp_path 기반 임시 DB 자동 생성/삭제, 테스트마다 새 GPTGateway 인스턴스 생성

### 5. 테스트 검증 결과

| 실행 | 결과 |
|------|------|
| `pytest -m smoke -v` | 3 passed in 5.73s ✅ |
| `pytest tests/ -v --cov` | 11 passed in 20.94s ✅ |
| 커버리지 | 62.18% (하한 60% 충족) ✅ |
| Gateway 핵심 모듈 커버리지 | client.py 90%, rate_limiter.py 89%, usage_tracker.py 88% |
