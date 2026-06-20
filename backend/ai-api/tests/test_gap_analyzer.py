import pytest
from app.services.gap_analyzer import resolve_role, analyze_gap, rank_roles_by_fit

@pytest.fixture
def sample_demand():
    return {
        "meta": {"job_count": 100, "position_count": 120, "rank1_only": False},
        "roles": {
            "백엔드개발자": {
                "position_count": 24,
                "tech_stack": [
                    {"skill": "java", "count": 18, "pct": 0.75},
                    {"skill": "spring", "count": 14, "pct": 0.583},
                    {"skill": "aws", "count": 12, "pct": 0.5},
                    {"skill": "docker", "count": 5, "pct": 0.2},
                    {"skill": "mysql", "count": 4, "pct": 0.15},
                    {"skill": "redis", "count": 1, "pct": 0.05}
                ],
                "experience_level": {"경력": 16, "신입": 8}
            },
            "데이터분석가": {
                "position_count": 10,
                "tech_stack": [
                    {"skill": "python", "count": 8, "pct": 0.8},
                    {"skill": "sql", "count": 7, "pct": 0.7},
                    {"skill": "tableau", "count": 5, "pct": 0.5}
                ],
                "experience_level": {"신입": 5, "경력": 5}
            },
            "노이즈직군": {
                "position_count": 1,
                "tech_stack": [
                    {"skill": "s1", "count": 1, "pct": 0.05},
                    {"skill": "s2", "count": 1, "pct": 0.04},
                    {"skill": "s3", "count": 1, "pct": 0.03},
                    {"skill": "s4", "count": 1, "pct": 0.02},
                    {"skill": "s5", "count": 1, "pct": 0.01}
                ]
            }
        }
    }

@pytest.mark.smoke
def test_analyze_gap_basic(sample_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["Java", "스프링", "MySQL"]
    }
    
    report = analyze_gap(profile, sample_demand)
    
    assert report["role"] == "백엔드개발자"
    assert report["role_resolved"] is True
    
    matched_skills = [x["skill"] for x in report["matched_skills"]]
    assert "java" in matched_skills
    assert "spring" in matched_skills
    
    missing_skills = [x["skill"] for x in report["missing_core_skills"]]
    # Expected core missing: aws, docker, mysql (because user has java, spring, mysql wait.. mysql is in user profile!)
    # Profile skills: Java, 스프링, MySQL
    # core: java, spring, aws, docker, mysql
    # user has java, spring, mysql
    # missing core: aws, docker
    assert "aws" in missing_skills
    assert "docker" in missing_skills
    assert "redis" not in missing_skills
    
    # 0.75 + 0.583 + 0.15 = 1.483
    # 1.483 / (0.75 + 0.583 + 0.5 + 0.2 + 0.15 = 2.183) = 0.679
    assert 0.67 < report["readiness_score"] < 0.69

@pytest.mark.full
def test_readiness_score(sample_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java", "spring"]
    }
    report = analyze_gap(profile, sample_demand)
    # expected: (0.75 + 0.583) / (0.75 + 0.583 + 0.5 + 0.2 + 0.15) = 1.333 / 2.183 ≈ 0.611
    expected_score = round((0.75 + 0.583) / (0.75 + 0.583 + 0.5 + 0.2 + 0.15), 3)
    assert abs(report["readiness_score"] - expected_score) <= 0.01

@pytest.mark.full
def test_core_threshold_excludes_tail(sample_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java", "spring", "redis"]
    }
    report = analyze_gap(profile, sample_demand)
    # redis는 0.05 < 0.10이므로 핵심 스킬(core)에서 제외되어야 한다.
    expected_score = round((0.75 + 0.583) / (0.75 + 0.583 + 0.5 + 0.2 + 0.15), 3)
    assert abs(report["readiness_score"] - expected_score) <= 0.01
    
    missing = [x["skill"] for x in report["missing_core_skills"]]
    assert "redis" not in missing

@pytest.mark.full
def test_core_fallback_topk(sample_demand):
    # 데이터분석가는 스킬이 3개 뿐이므로 모두 fallback 처리되어 core로 간주되어야 함.
    profile = {
        "desired_role": "데이터분석가",
        "skills": ["python"]
    }
    report = analyze_gap(profile, sample_demand)
    missing = [x["skill"] for x in report["missing_core_skills"]]
    assert "sql" in missing
    assert "tableau" in missing

@pytest.mark.full
def test_missing_tail_count(sample_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": ["java"]
    }
    report = analyze_gap(profile, sample_demand)
    # 전체 6개 (java, spring, aws, docker, mysql, redis)
    # core는 5개 (java, spring, aws, docker, mysql)
    # 유저: java
    # missing_core = 4 (spring, aws, docker, mysql)
    # 전체 미보유 = 5 (spring, aws, docker, mysql, redis)
    # tail = 5 - 4 = 1
    assert report["missing_tail_count"] == 1

@pytest.mark.full
def test_resolve_role_aliases(sample_demand):
    assert resolve_role("백엔드", sample_demand) == "백엔드개발자"
    assert resolve_role("백엔드 개발자", sample_demand) == "백엔드개발자"
    assert resolve_role("서버개발자", sample_demand) == "백엔드개발자"
    assert resolve_role("데이터 분석", sample_demand) == "데이터분석가"

@pytest.mark.full
def test_unknown_role_graceful(sample_demand):
    profile = {
        "desired_role": "우주비행사",
        "skills": ["로켓", "무중력"]
    }
    report = analyze_gap(profile, sample_demand)
    
    assert report["role_resolved"] is False
    assert report["role"] is None
    assert report["readiness_score"] == 0.0
    assert len(report["matched_skills"]) == 0
    assert len(report["notes"]) > 0

@pytest.mark.full
def test_empty_skills(sample_demand):
    profile = {
        "desired_role": "백엔드개발자",
        "skills": []
    }
    report = analyze_gap(profile, sample_demand)
    
    assert report["readiness_score"] == 0.0
    assert len(report["matched_skills"]) == 0
    assert len(report["missing_core_skills"]) == 5 # java, spring, aws, docker, mysql
    assert report["missing_tail_count"] == 1 # redis

@pytest.mark.full
def test_rank_roles_by_fit(sample_demand):
    profile = {
        "desired_role": "백엔드개발자", # 무의미하게 던짐
        "skills": ["python", "sql", "tableau"]
    }
    ranked = rank_roles_by_fit(profile, sample_demand)
    
    # ranked[0] should be 데이터분석가 (100% fit)
    assert ranked[0]["role"] == "데이터분석가"
    assert ranked[0]["readiness_score"] == 1.0
    
    # 노이즈직군은 position_count가 1이므로 배제되어야 함
    roles_in_ranked = [r["role"] for r in ranked]
    assert "노이즈직군" not in roles_in_ranked
