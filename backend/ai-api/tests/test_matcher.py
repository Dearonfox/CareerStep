import pytest
from app.services.matcher import retrieve_candidates, match_jobs, generate_roadmap
from app.schemas import RecommendJobsResponse, RoadmapResponse

@pytest.fixture
def mock_positions():
    return [
        {
            "job_id": "1",
            "position_title": "자바 백엔드",
            "company_name": "A사",
            "tech_stack": ["java", "spring"],
            "routed_roles": [{"role": "백엔드개발자", "score": 1.0}]
        },
        {
            "job_id": "2",
            "position_title": "파이썬 백엔드",
            "company_name": "B사",
            "tech_stack": ["python", "django"],
            "routed_roles": [{"role": "백엔드개발자", "score": 1.0}]
        },
        {
            "job_id": "3",
            "position_title": "프론트엔드",
            "company_name": "C사",
            "tech_stack": ["javascript", "react"],
            "routed_roles": [{"role": "프론트엔드개발자", "score": 1.0}]
        }
    ]

@pytest.fixture
def mock_demand():
    return {
        "roles": {
            "백엔드개발자": {
                "tech_stack": [
                    {"skill": "java", "pct": 0.5},
                    {"skill": "spring", "pct": 0.4},
                    {"skill": "aws", "pct": 0.3},
                    {"skill": "mysql", "pct": 0.2},
                    {"skill": "docker", "pct": 0.15}
                ]
            }
        }
    }

@pytest.mark.smoke
def test_retrieve_basic(mock_positions, mock_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java"]
    }
    # top_k를 2로 설정하면, 1,2번만으로 조건을 만족하므로 fallback이 발동하지 않아 프론트엔드가 제외됨.
    candidates = retrieve_candidates(profile, mock_positions, mock_demand, top_k=2, max_k=2)
    assert len(candidates) == 2
    job_ids = [c["job_id"] for c in candidates]
    assert "1" in job_ids
    assert "2" in job_ids
    assert "3" not in job_ids

@pytest.mark.full
def test_retrieve_topk_cap(mock_positions, mock_demand):
    # 25개의 mock_positions 생성
    many_positions = [{"job_id": str(i), "position_title": "백", "tech_stack": ["java"], "routed_roles": [{"role": "백엔드개발자", "score": 1.0}]} for i in range(25)]
    
    profile = {
        "desired_role": "백엔드개발자",
        "skills": []
    }
    
    candidates = retrieve_candidates(profile, many_positions, mock_demand, top_k=15, max_k=20)
    assert len(candidates) == 20 # max_k 초과하지 않음

@pytest.mark.full
def test_retrieve_ranking(mock_positions, mock_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java", "spring"]
    }
    candidates = retrieve_candidates(profile, mock_positions, mock_demand)
    # job_id "1" (java, spring) 이 overlap_score 가 더 높아야 함.
    # 1: 2/2 = 1.0
    # 2: 0/2 = 0.0
    
    # 1번이 먼저 나와야 함
    assert candidates[0]["job_id"] == "1"
    assert candidates[1]["job_id"] == "2"

@pytest.mark.asyncio
@pytest.mark.full
async def test_match_jobs_single_call(monkeypatch, mock_positions, mock_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java"]
    }
    
    mock_response = {
        "recommendations": [
            {
                "job_id": "1",
                "position_title": "자바 백엔드",
                "match_score": 90,
                "reason": "Good",
                "matched_skills": ["java"],
                "missing_skills": ["spring"]
            }
        ],
        "strengths": ["java"],
        "gaps": ["spring"],
        "roadmap": [],
        "policy_violation": False
    }
    
    class AsyncMock:
        def __init__(self, return_value):
            self.return_value = return_value
            self.call_count = 0
        async def __call__(self, *args, **kwargs):
            self.call_count += 1
            return self.return_value
            
    mock_chat = AsyncMock(mock_response)
    monkeypatch.setattr("app.gateway.gpt_gateway.chat_json", mock_chat)
    
    # include_roadmap=False → 정확히 1콜만
    response = await match_jobs(profile, mock_positions[:1], mock_demand, include_roadmap=False)
    
    assert mock_chat.call_count == 1
    assert isinstance(response, RecommendJobsResponse)
    assert len(response.recommendations) == 1
    assert response.recommendations[0].job_id == "1"
    assert "90점" in response.recommendations[0].reason
    assert "일치 스킬" in response.recommendations[0].reason

@pytest.mark.asyncio
@pytest.mark.full
async def test_no_candidates(monkeypatch, mock_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java"]
    }
    
    class AsyncMock:
        def __init__(self):
            self.call_count = 0
        async def __call__(self, *args, **kwargs):
            self.call_count += 1
            return {}
            
    mock_chat = AsyncMock()
    monkeypatch.setattr("app.gateway.gpt_gateway.chat_json", mock_chat)
    
    response = await match_jobs(profile, [], mock_demand)
    
    assert mock_chat.call_count == 0
    assert len(response.recommendations) == 0
    assert len(response.gaps) > 0

@pytest.mark.full
def test_retrieve_excludes_zero_score(mock_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java"]
    }
    positions = [
        {
            "job_id": "1",
            "position_title": "정비사",
            "tech_stack": [],
            "requirements": ["운전면허"],
            "main_tasks": ["차량 정비"],
            "routed_roles": [{"role": "기타", "score": 1.0}]
        }
    ]
    # top_k가 15라도, 0점(무관) 공고는 포함되지 않아야 함
    candidates = retrieve_candidates(profile, positions, mock_demand, top_k=15, max_k=20)
    assert len(candidates) == 0

@pytest.mark.full
def test_retrieve_overlap_priority(mock_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["python", "django"]
    }
    positions = [
        {
            "job_id": "1",
            "position_title": "빈 텍스트 백엔드",
            "tech_stack": [],
            "requirements": ["백엔드 3년"],
            "main_tasks": ["개발"],
            "routed_roles": [{"role": "백엔드개발자", "score": 1.0}]
        },
        {
            "job_id": "2",
            "position_title": "파이썬 백엔드",
            "tech_stack": ["python", "django", "aws"],
            "requirements": ["파이썬 3년"],
            "main_tasks": ["백엔드 개발"],
            # role_score는 약간 낮음
            "routed_roles": [{"role": "백엔드개발자", "score": 0.8}]
        }
    ]
    
    candidates = retrieve_candidates(profile, positions, mock_demand)
    assert len(candidates) == 2
    
    # 2번: score 0.8 + overlap (2/3)*1.0 = 0.8 + 0.66 = 1.46
    # 1번: score 1.0 + overlap 0 = 1.0
    # 따라서 2번이 우선되어야 함
    assert candidates[0]["job_id"] == "2"
    assert candidates[1]["job_id"] == "1"


@pytest.mark.asyncio
@pytest.mark.full
async def test_match_with_roadmap_two_calls(monkeypatch, mock_positions, mock_demand):
    """ᄌ첹 1회 + 로드맵 1회 = 정확히 2콜 단언."""
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java"]
    }

    scoring_response = {
        "recommendations": [
            {
                "job_id": "1",
                "position_title": "자바 백엔드",
                "match_score": 85,
                "reason": "Good",
                "matched_skills": ["java"],
                "missing_skills": ["aws"]
            }
        ],
        "strengths": ["java"],
        "gaps": ["aws"],
        "roadmap": [],
        "policy_violation": False
    }

    roadmap_response = {
        "roadmap": [
            {
                "order": 1,
                "title": "AWS EC2 기초",
                "why": "상위 공고 3개 모두 AWS 필수",
                "how": "EC2 인스턴스 생성 후 Spring Boot 앱 배포",
                "duration": "1~2주",
                "outcome": "EC2에 앱 배포 완료"
            }
        ],
        "summary": "AWS 덕후부터 시작하세요."
    }

    call_responses = [scoring_response, roadmap_response]

    class AsyncMock:
        def __init__(self, responses):
            self.responses = iter(responses)
            self.call_count = 0
        async def __call__(self, *args, **kwargs):
            self.call_count += 1
            return next(self.responses)

    mock_chat = AsyncMock(call_responses)
    monkeypatch.setattr("app.gateway.gpt_gateway.chat_json", mock_chat)

    response = await match_jobs(profile, mock_positions[:1], mock_demand, include_roadmap=True)

    assert mock_chat.call_count == 2
    assert isinstance(response, RecommendJobsResponse)
    assert len(response.roadmap) == 1
    assert response.roadmap[0].title == "AWS EC2 기초"


@pytest.mark.asyncio
@pytest.mark.full
async def test_generate_roadmap(monkeypatch, mock_demand):
    """로드맵 전용 호출이 RoadmapResponse를 를 반환하고 필드 어주었는지 검증."""
    mock_roadmap = {
        "roadmap": [
            {
                "order": i + 1,
                "title": f"단계{i + 1}",
                "why": "시장 수요 기반",
                "how": "미니 프로젝트 수행",
                "duration": "1주",
                "outcome": "역량 확보"
            }
            for i in range(5)
        ],
        "summary": "단계별 학습 계획입니다."
    }

    class AsyncMock:
        def __init__(self, rv):
            self.rv = rv
            self.call_count = 0
        async def __call__(self, *args, **kwargs):
            self.call_count += 1
            return self.rv

    mock_chat = AsyncMock(mock_roadmap)
    monkeypatch.setattr("app.gateway.gpt_gateway.chat_json", mock_chat)

    gap_report = {
        "top_strengths": [{"skill": "java", "pct": 0.5}],
        "missing_core_skills": [{"skill": "aws", "pct": 0.3}],
        "readiness_score": 0.5
    }
    profile = {"desired_role": "백엔드개발자", "skills": ["java"]}
    top_jobs = [
        {"position_title": "백엔드", "requirements": ["Java"], "preferred": ["AWS"]}
    ]

    result = await generate_roadmap(profile, gap_report, mock_demand, top_jobs)

    assert mock_chat.call_count == 1
    assert isinstance(result, RoadmapResponse)
    assert len(result.roadmap) == 5
    for step in result.roadmap:
        assert hasattr(step, "why")
        assert hasattr(step, "how")
        assert hasattr(step, "duration")
        assert hasattr(step, "outcome")
