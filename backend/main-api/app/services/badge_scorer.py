"""결정론적 배지 점수 계산 (LLM 미사용).

공고 목록의 각 카드에 표시할 0~100 매칭 점수를 read 시점에 즉석 계산한다.
ai-api matcher.retrieve_candidates 의 role_score + overlap_score 로직과 동일한
관점을 main-api 안에서 의존성 없이 가볍게 재현한 것이다.
"""

from __future__ import annotations

import re
from typing import Any


def _norm(value: Any) -> str:
    """스킬·기술명 정규화: 소문자 + 공백 1칸 + 양끝 공백 제거."""
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _norm_role(value: Any) -> str:
    """직군명 정규화: 소문자 + 모든 공백 제거 (예: '백엔드 개발자' -> '백엔드개발자')."""
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def score_job(
    skills: list[str] | None,
    desired_role: str,
    routed_roles: list[dict] | None,
    tech_stack: list[str] | None,
) -> dict:
    """단일 (프로필, 공고) 에 대한 배지 점수를 계산한다.

    Args:
        skills: 사용자 보유 스킬 목록.
        desired_role: 사용자 희망 직군 (자유 텍스트).
        routed_roles: 공고 summary.routed_roles ([{role, score(0~1)}]).
        tech_stack: 공고 요구 기술 목록.

    Returns:
        {"score": int(0~100), "matched_skills": list[str]}
        - score = (role_score + overlap_score) / 2 * 100
        - matched_skills 는 공고 tech_stack 원본 표기를 유지.
    """
    user_skills = {_norm(s): str(s) for s in (skills or []) if str(s).strip()}

    # role_score: 희망 직군과 일치하는 routed_role 의 점수 (0~1)
    role_score = 0.0
    if desired_role:
        target = _norm_role(desired_role)
        for r in routed_roles or []:
            role_name = _norm_role(r.get("role", ""))
            if role_name and (role_name == target or role_name in target or target in role_name):
                try:
                    role_score = max(role_score, float(r.get("score", 0.0) or 0.0))
                except (TypeError, ValueError):
                    continue

    # overlap_score: 보유 스킬 ∩ 공고 요구 기술 / 공고 요구 기술 (0~1)
    tech_norm = {_norm(t): str(t) for t in (tech_stack or []) if str(t).strip()}
    matched_skills = [original for key, original in tech_norm.items() if key in user_skills]
    overlap_score = (len(matched_skills) / len(tech_norm)) if tech_norm else 0.0

    score = round((role_score + overlap_score) / 2 * 100)
    score = max(0, min(100, score))

    return {"score": score, "matched_skills": matched_skills}


def best_badge_for_positions(
    skills: list[str] | None,
    desired_role: str,
    routed_roles: list[dict] | None,
    positions_tech_stacks: list[list[str]],
) -> dict:
    """공고에 포지션이 여러 개일 때, 포지션별 점수 중 최고를 대표 배지로 반환한다."""
    best = {"score": 0, "matched_skills": []}
    found = False
    for tech_stack in positions_tech_stacks or []:
        result = score_job(skills, desired_role, routed_roles, tech_stack)
        if not found or result["score"] > best["score"]:
            best = result
            found = True
    return best
