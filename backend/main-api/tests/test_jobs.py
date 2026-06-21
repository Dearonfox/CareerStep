from app.routers.jobs import serialize_mongo_job


def test_serialize_mongo_job_prefers_position_tech_stack_for_badge():
    job = {
        "job_id": "101",
        "title": "Backend Developer",
        "company_name": "CareerStep",
        "tags": ["advertising", "marketing"],
        "summary": {
            "routed_roles": [{"role": "Backend Developer", "score": 1.0}],
            "relevant_positions": [
                {
                    "position_title": "Backend Developer",
                    "tech_stack": ["Java", "Spring Boot"],
                    "requirements": ["Build REST APIs"],
                    "main_tasks": ["Develop backend services"],
                }
            ],
        },
    }

    result = serialize_mongo_job(
        job,
        profile_ctx={
            "skills": ["Java", "Spring Boot"],
            "desired_role": "Backend Developer",
        },
    )

    assert result.skills == ["Java", "Spring Boot"]
    assert result.match_badge is not None
    assert result.match_badge.score == 100
    assert result.match_badge.matched_skills == ["Java", "Spring Boot"]
