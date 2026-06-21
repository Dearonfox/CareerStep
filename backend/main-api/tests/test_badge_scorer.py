from app.services.badge_scorer import best_badge_for_positions, score_job


def test_perfect_match_is_100():
    result = score_job(
        skills=["Java", "Spring Boot"],
        desired_role="백엔드 개발자",
        routed_roles=[{"role": "백엔드개발자", "score": 1.0}],
        tech_stack=["Java", "Spring Boot"],
    )
    assert result["score"] == 100
    assert set(result["matched_skills"]) == {"Java", "Spring Boot"}


def test_no_skills_no_role_scores_zero():
    # 스킬도 없고 희망 직군 매칭도 없으면 0
    result = score_job([], "", [], ["Java"])
    assert result["score"] == 0
    assert result["matched_skills"] == []


def test_role_score_is_independent_of_skills():
    # 스킬이 없어도 희망 직군이 routed_role 과 맞으면 role 점수만으로 점수가 잡힌다
    # role 0.9 + overlap 0 -> (0.9)/2 = 0.45 -> 45
    result = score_job([], "백엔드 개발자", [{"role": "백엔드개발자", "score": 0.9}], ["Java"])
    assert result["score"] == 45
    assert result["matched_skills"] == []


def test_overlap_only_when_no_routed_roles():
    # role 매칭 0, 스킬 1/2 겹침 -> (0 + 0.5)/2 = 0.25 -> 25점
    result = score_job(["Java"], "백엔드 개발자", [], ["Java", "Python"])
    assert result["score"] == 25
    assert result["matched_skills"] == ["Java"]


def test_case_and_space_normalization():
    result = score_job(["spring boot"], "백엔드 개발자", [], ["Spring Boot"])
    assert result["matched_skills"] == ["Spring Boot"]
    assert result["score"] == 50  # role 0 + overlap 1 -> 50


def test_role_partial_match():
    # 희망 '백엔드 개발자' vs routed '백엔드개발자' (공백 제거 후 일치)
    result = score_job([], "백엔드 개발자", [{"role": "백엔드개발자", "score": 0.8}], [])
    # tech_stack 비어있어 overlap 0, role 0.8 -> (0.8+0)/2 = 0.4 -> 40
    assert result["score"] == 40


def test_no_role_match_keeps_role_zero():
    result = score_job([], "프론트엔드 개발자", [{"role": "백엔드개발자", "score": 0.9}], [])
    assert result["score"] == 0


def test_best_badge_picks_highest_position():
    routed = [{"role": "백엔드개발자", "score": 0.6}]
    best = best_badge_for_positions(
        skills=["Java", "MySQL"],
        desired_role="백엔드 개발자",
        routed_roles=routed,
        positions_tech_stacks=[["Python"], ["Java", "MySQL"]],
    )
    # 두 번째 포지션: role 0.6 + overlap 1.0 -> (1.6)/2 = 0.8 -> 80
    assert best["score"] == 80
    assert set(best["matched_skills"]) == {"Java", "MySQL"}


def test_score_bounds():
    result = score_job(["Java"], "백엔드 개발자", [{"role": "백엔드개발자", "score": 1.0}], ["Java"])
    assert 0 <= result["score"] <= 100
