"""
시장 수요 집계 엔진 (Market-Demand Aggregator)

합격 후기 데이터 없이, 수집·요약·라우팅된 채용공고(job_raw)를 집계하여
직군별 "시장 수요 분포"를 산출한다. 이 분포가 Gap 진단·로드맵의 기준선이 된다.

설계 문서: docs/matching-engine-design.md §4.5

특징:
- LLM 호출 0회 (순수 집계). DB 의존 없이 dict 리스트만 받으면 동작 → 테스트 용이.
- tech_stack 항목은 alias_dict 로 정규화하여 표면형 불일치(파이썬/python 등)를 합산.
"""

from collections import Counter
from typing import Any, Dict, List

from app.services.alias_dict import normalize_text
from app.services.router import process_routing_for_job


def _normalize_skill(raw: str) -> str:
    """기술 스택 단일 항목을 표준형으로 정규화. 빈 값이면 빈 문자열."""
    if not raw or not str(raw).strip():
        return ""
    return normalize_text(str(raw))


def _roles_of_position(position: Dict[str, Any], rank1_only: bool) -> List[str]:
    """포지션이 속한 직군 목록을 반환. routed_roles 기반."""
    routed = position.get("routed_roles", []) or []
    if rank1_only:
        routed = [r for r in routed if r.get("rank") == 1]
    return [r.get("role") for r in routed if r.get("role")]


def aggregate_demand(
    jobs: List[Dict[str, Any]],
    rank1_only: bool = False,
    ensure_routed: bool = True,
    min_count: int = 2,
) -> Dict[str, Any]:
    """
    job_raw 문서 리스트를 받아 직군별 시장 수요 분포를 집계한다.

    Args:
        jobs: MongoDB job_raw 문서(dict) 리스트. 각 문서는 summary.relevant_positions 보유.
        rank1_only: True면 각 포지션의 1순위 직군에만 집계 반영. False면 routed_roles 전체.
        ensure_routed: True면 routed_roles 없는 문서에 라우팅을 즉석 적용.

    Returns:
        {
          "meta": {"job_count", "position_count", "rank1_only"},
          "roles": {
            "백엔드개발자": {
              "position_count": 12,
              "tech_stack": [{"skill": "python", "count": 9, "pct": 0.75}, ...],
              "experience_level": {"경력": 8, "신입": 4}
            }, ...
          }
        }
        roles 는 position_count 내림차순으로 정렬되어 반환.
    """
    # 직군별 누적기
    role_position_count: Counter = Counter()
    role_skill_counter: Dict[str, Counter] = {}
    role_exp_counter: Dict[str, Counter] = {}

    total_positions = 0

    for job in jobs:
        if ensure_routed:
            job = process_routing_for_job(job)

        summary = job.get("summary") or {}
        positions = summary.get("relevant_positions", []) or []

        for pos in positions:
            roles = _roles_of_position(pos, rank1_only)
            if not roles:
                continue
            total_positions += 1

            # 기술 스택 정규화 (포지션 내 중복 제거 → 공고당 1표)
            skills = {
                s for s in (_normalize_skill(t) for t in pos.get("tech_stack", []) or [])
                if s
            }
            exp = (pos.get("experience_level") or "").strip() or "미상"

            for role in roles:
                role_position_count[role] += 1
                role_skill_counter.setdefault(role, Counter()).update(skills)
                role_exp_counter.setdefault(role, Counter())[exp] += 1

    # 결과 빌드: 직군별 수요 분포
    roles_out: Dict[str, Any] = {}
    for role, pcount in role_position_count.items():
        skill_counter = role_skill_counter.get(role, Counter())
        tech_stack = [
            {"skill": skill, "count": cnt, "pct": round(cnt / pcount, 3)}
            for skill, cnt in skill_counter.most_common()
            if cnt >= min_count
        ]
        roles_out[role] = {
            "position_count": pcount,
            "tech_stack": tech_stack,
            "experience_level": dict(role_exp_counter.get(role, Counter())),
        }

    # position_count 내림차순 정렬
    roles_sorted = dict(
        sorted(roles_out.items(), key=lambda kv: kv[1]["position_count"], reverse=True)
    )

    return {
        "meta": {
            "job_count": len(jobs),
            "position_count": total_positions,
            "rank1_only": rank1_only,
        },
        "roles": roles_sorted,
    }


def demand_for_role(demand: Dict[str, Any], role: str) -> Dict[str, Any] | None:
    """집계 결과에서 특정 직군의 수요 프로필만 추출 (매칭 엔진이 사용)."""
    return demand.get("roles", {}).get(role)


def render_markdown(demand: Dict[str, Any], top_n: int = 15) -> str:
    """집계 결과를 사람이 읽기 좋은 마크다운으로 변환."""
    meta = demand.get("meta", {})
    lines = ["# 직군별 시장 수요 분포 (Market-Demand Profiles)\n"]
    lines.append(
        f"- 공고 {meta.get('job_count')}건 · 포지션 {meta.get('position_count')}건 집계 "
        f"(rank1_only={meta.get('rank1_only')})\n"
    )
    for role, prof in demand.get("roles", {}).items():
        lines.append(f"\n## {role}  (포지션 {prof['position_count']}건)")
        exp = prof.get("experience_level", {})
        if exp:
            exp_str = ", ".join(f"{k} {v}" for k, v in exp.items())
            lines.append(f"- 경력 분포: {exp_str}")
        tech = prof.get("tech_stack", [])[:top_n]
        if tech:
            lines.append("- 기술 수요:")
            for t in tech:
                bar = "█" * max(1, round(t["pct"] * 20))
                lines.append(f"  - {t['skill']:<16} {t['pct']*100:5.1f}%  {bar}  ({t['count']})")
        else:
            lines.append("- 기술 수요: (집계된 tech_stack 없음)")
    return "\n".join(lines)
