from typing import Any, Dict, List, Optional
from app.services.gap_analyzer import resolve_role, analyze_gap
from app.services.alias_dict import normalize_text
from app.schemas import CandidateJob, RecommendJobsRequest, RecommendJobsResponse, ProfileInput, RoadmapResponse
from app.gateway import gpt_gateway
from app.services.prompts import MATCH_JOBS_SYSTEM_PROMPT, ROADMAP_SYSTEM_PROMPT
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def enrich_score_reasons(result: RecommendJobsResponse) -> None:
    """
    Make recommendation reasons explain the visible score, even when the LLM
    returns a generic reason. This keeps the frontend contract unchanged.
    """
    for recommendation in result.recommendations:
        score_text = f"{recommendation.match_score}점"
        if score_text in recommendation.reason:
            continue

        basis_parts = []
        if recommendation.matched_skills:
            basis_parts.append(f"일치 스킬({', '.join(recommendation.matched_skills[:3])})")
        if recommendation.missing_skills:
            basis_parts.append(f"보완 필요 역량({', '.join(recommendation.missing_skills[:3])})")

        if basis_parts:
            score_basis = f"{score_text}으로 평가한 핵심 근거는 {'와 '.join(basis_parts)}입니다."
        else:
            score_basis = f"{score_text}은 사용자 프로필과 공고 요구사항의 종합 적합도를 기준으로 산정했습니다."

        recommendation.reason = f"{score_basis} {recommendation.reason}".strip()


def retrieve_candidates(profile: Dict[str, Any], positions: List[Dict[str, Any]], demand: Dict[str, Any], top_k: int = 15, max_k: int = 20) -> List[Dict[str, Any]]:
    """
    LLM 없이 결정론적으로 후보 공고를 검색하고 점수화하여 상위 K개를 반환한다.
    """
    desired_role = profile.get("desired_role", "")
    resolved_role = resolve_role(desired_role, demand)

    user_skills = set(normalize_text(s) for s in profile.get("skills", []))

    candidates = []

    for pos in positions:
        routed_roles = pos.get("routed_roles", [])

        role_score = 0.0
        for r in routed_roles:
            if r.get("role") == resolved_role:
                role_score = r.get("score", 0.0)
                break

        # 1-C. 빈 텍스트 포지션 제외 가드
        tech_stack = pos.get("tech_stack", [])
        requirements = pos.get("requirements", [])
        main_tasks = pos.get("main_tasks", [])
        if not tech_stack and not requirements and not main_tasks:
            continue

        tech_stack_set = set(normalize_text(s) for s in tech_stack)

        overlap_score = 0.0
        if tech_stack_set:
            intersection = user_skills.intersection(tech_stack_set)
            overlap_score = len(intersection) / len(tech_stack_set)

        # overlap 가중 1.0으로 상향
        retrieval_score = role_score + overlap_score * 1.0

        # 1-A. 0점 후보 절대 포함 금지
        if retrieval_score <= 0:
            continue

        # 원본을 수정하지 않기 위해 복사
        candidate = dict(pos)
        candidate["_retrieval_score"] = retrieval_score
        candidate["_role_score"] = role_score
        candidate["_overlap_score"] = overlap_score
        candidates.append(candidate)

    # 정렬: retrieval_score 기준 내림차순, 동점시 overlap_score 기준
    candidates.sort(key=lambda x: (x["_retrieval_score"], x["_overlap_score"]), reverse=True)

    # 1순위: 직군이 일치하는 공고
    primary_candidates = [c for c in candidates if c["_role_score"] > 0]

    if len(primary_candidates) < top_k:
        # Fallback: 전체에서 높은 점수순 (0점은 이미 제외됨)
        final_candidates = candidates[:max_k]
    else:
        final_candidates = primary_candidates[:max_k]

    # Compact 포맷으로 변환 (토큰 절약)
    compact_candidates = []
    for c in final_candidates:
        compact_candidates.append({
            "job_id": str(c.get("job_id", "")),
            "position_title": c.get("position_title", ""),
            "company": c.get("company_name", c.get("company", "")),
            "_retrieval_score": c.get("_retrieval_score", 0),
            "experience_level": c.get("experience_level", ""),
            "tech_stack": c.get("tech_stack", []),
            "requirements": c.get("requirements", [])[:6],
            "preferred": c.get("preferred", [])[:6],
            "main_tasks": c.get("main_tasks", [])[:6]
        })

    return compact_candidates


async def generate_roadmap(
    profile: Dict[str, Any],
    gap_report: Dict[str, Any],
    demand: Dict[str, Any],
    top_jobs: List[Dict[str, Any]],
    model: Optional[str] = None,
) -> RoadmapResponse:
    """
    사용자의 갭·시장 수요·상위 매칭 공고를 바탕으로 로드맵을 전용 LLM 1콜로 생성한다.
    """
    # top_jobs 컨텍스트 컴팩트 요약 (토큰 절약)
    top_jobs_summary = [
        {
            "position_title": j.get("position_title", ""),
            "requirements": j.get("requirements", [])[:5],
            "preferred": j.get("preferred", [])[:5],
        }
        for j in top_jobs
    ]

    missing_core = [item["skill"] for item in gap_report.get("missing_core_skills", [])]
    market_demand_top = [
        item["skill"]
        for item in (gap_report.get("top_strengths", []) + gap_report.get("missing_core_skills", []))
    ]
    market_demand_top = sorted(
        dict.fromkeys(market_demand_top),  # 중복 제거, 순서 유지
        key=lambda s: next((i["pct"] for i in gap_report.get("top_strengths", []) + gap_report.get("missing_core_skills", []) if i["skill"] == s), 0),
        reverse=True,
    )

    roadmap_payload = {
        "profile": profile,
        "gap": missing_core,
        "market_demand_top": market_demand_top[:15],
        "top_jobs": top_jobs_summary,
    }

    roadmap_model = model or settings.openai_roadmap_model or settings.openai_model

    logger.info(f"Generating roadmap (model={roadmap_model}) with {len(top_jobs)} top jobs.")

    result = await gpt_gateway.chat_json(
        system_prompt=ROADMAP_SYSTEM_PROMPT,
        payload=roadmap_payload,
        endpoint="/recommend/roadmap",
        response_format=RoadmapResponse,
        model=roadmap_model,
        estimated_tokens=2500,
        max_output_tokens=3000,
    )

    return RoadmapResponse.model_validate(result)


async def match_jobs(
    profile: Dict[str, Any],
    positions: List[Dict[str, Any]],
    demand: Dict[str, Any],
    model: Optional[str] = None,
    include_roadmap: bool = True,
) -> RecommendJobsResponse:
    """
    단 한 번의 LLM 호출로 후보 공고들을 일괄 채점하고,
    include_roadmap=True면 추가 1콜로 로드맵을 생성한다.
    전체 = 사용자당 정확히 2콜 (채점 1 + 로드맵 1).
    """
    candidates = retrieve_candidates(profile, positions, demand)

    if not candidates:
        return RecommendJobsResponse(
            recommendations=[],
            strengths=[],
            gaps=["조건에 맞는 공고를 찾지 못했습니다."],
            roadmap=[],
            policy_violation=False
        )

    gap_report = analyze_gap(profile, demand)
    # market_demand_top 컨텍스트 동봉
    core_skills_map = gap_report.get("top_strengths", []) + gap_report.get("missing_core_skills", [])
    core_skills_map.sort(key=lambda x: x["pct"], reverse=True)
    market_demand_top = [item["skill"] for item in core_skills_map]

    candidate_models = [CandidateJob(**{k: v for k, v in c.items() if not k.startswith("_")}) for c in candidates]

    payload = RecommendJobsRequest(
        profile=ProfileInput(**profile),
        candidates=candidate_models,
        market_demand_top=market_demand_top
    )

    # gap 컨텍스트 추가 정보
    payload_dict = payload.model_dump()
    payload_dict["gap_context"] = gap_report

    logger.info(f"[콜 1/채점] {len(candidates)}개 후보 배치 채점 요청.")

    response_dict = await gpt_gateway.chat_json(
        system_prompt=MATCH_JOBS_SYSTEM_PROMPT,
        payload=payload_dict,
        endpoint="/recommend/jobs",
        response_format=RecommendJobsResponse,
        model=model
    )

    scoring_result = RecommendJobsResponse.model_validate(response_dict)
    scoring_result.recommendations.sort(key=lambda item: item.match_score, reverse=True)
    enrich_score_reasons(scoring_result)

    # roadmap 생성 (선택)
    if include_roadmap and scoring_result.recommendations:
        top_5 = candidates[:5]  # retrieval_score 기준 이미 정렬된 상태
        logger.info(f"[콜 2/로드맵] 상위 {len(top_5)}개 공고 기반 로드맵 생성.")
        roadmap_result = await generate_roadmap(
            profile=profile,
            gap_report=gap_report,
            demand=demand,
            top_jobs=top_5,
            model=model,
        )
        scoring_result.roadmap = roadmap_result.roadmap

    return scoring_result
