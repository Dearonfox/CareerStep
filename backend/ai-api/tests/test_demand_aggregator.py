import pytest
from app.services.demand_aggregator import aggregate_demand

@pytest.fixture
def mock_jobs():
    return [
        {
            "job_id": "1",
            "summary": {
                "relevant_positions": [
                    {
                        "position_title": "백엔드 개발자",
                        "tech_stack": ["java", "spring", "희귀스킬A"],
                        "experience_level": "신입",
                        "routed_roles": [{"role": "백엔드개발자", "rank": 1, "score": 1.0}]
                    }
                ]
            }
        },
        {
            "job_id": "2",
            "summary": {
                "relevant_positions": [
                    {
                        "position_title": "자바 백엔드",
                        "tech_stack": ["java", "spring", "aws", "희귀스킬B"],
                        "experience_level": "경력",
                        "routed_roles": [{"role": "백엔드개발자", "rank": 1, "score": 1.0}]
                    }
                ]
            }
        }
    ]

@pytest.mark.full
def test_min_count_filter(mock_jobs):
    # min_count = 1 이면 희귀스킬 포함
    demand_min1 = aggregate_demand(mock_jobs, min_count=1)
    backend_tech = demand_min1["roles"]["백엔드개발자"]["tech_stack"]
    skills_min1 = [t["skill"] for t in backend_tech]
    
    assert "java" in skills_min1
    assert "spring" in skills_min1
    assert "희귀스킬a" in skills_min1
    assert "희귀스킬b" in skills_min1
    
    # min_count = 2 (기본값) 이면 희귀스킬 제외
    demand_min2 = aggregate_demand(mock_jobs, min_count=2)
    backend_tech2 = demand_min2["roles"]["백엔드개발자"]["tech_stack"]
    skills_min2 = [t["skill"] for t in backend_tech2]
    
    assert "java" in skills_min2
    assert "spring" in skills_min2
    assert "희귀스킬a" not in skills_min2
    assert "희귀스킬b" not in skills_min2
    
    # aws도 1번 등장하므로 제외됨
    assert "aws" not in skills_min2
