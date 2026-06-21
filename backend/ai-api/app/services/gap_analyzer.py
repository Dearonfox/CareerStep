"""
Gap 분석기 (Gap Analyzer)

사용자의 보유 스킬과 이미 산출된 시장 수요 분포(demand)를 비교하여,
해당 직무에 대한 정량적인 적합도, 보유 스킬, 부족 스킬, 강점을 도출하는 순수 로직 모듈.

- LLM, 네트워크, DB 호출 없이 결정론적으로 동작합니다.
- `app/services/demand_aggregator.py`의 출력물을 기준으로 합니다.
"""

from typing import Any, Dict, List, Optional
from collections import Counter

from app.services.alias_dict import normalize_text
from app.services.router import ROLE_KEYWORDS

CORE_PCT_THRESHOLD = 0.10   # 공고의 10% 이상이 요구하는 스킬을 '핵심 수요'로 본다
CORE_MIN_SKILLS = 5         # 임계값 통과 스킬이 이보다 적으면(희소 직군)
CORE_FALLBACK_TOP_K = 8     # 상위 K개를 core 로 사용

def core_skills(tech_stack: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """직군의 전체 수요 스택에서 '핵심 스킬'만 추출한다."""
    core = [t for t in tech_stack if t.get("pct", 0.0) >= CORE_PCT_THRESHOLD]
    if len(core) < CORE_MIN_SKILLS:
        core = tech_stack[:CORE_FALLBACK_TOP_K]   # 이미 pct 내림차순
    return core


def resolve_role(desired_role: str, demand: Dict[str, Any]) -> Optional[str]:
    """
    사용자의 자유 입력 직무명(desired_role)을 수요 데이터의 표준 직군명으로 해석한다.
    
    1. 정규화 후 `demand["roles"]` 키와 정확히 일치하면 반환
    2. 불일치 시 `router.ROLE_KEYWORDS`를 활용해 키워드 교집합이 가장 큰 표준 직군명 반환
    3. 일치하는 키워드가 하나도 없으면 None 반환
    """
    if not desired_role:
        return None
        
    normalized_input = normalize_text(desired_role)
    roles_demand = demand.get("roles", {})
    
    # 1. 완전 일치 (직군명도 내부적으로 띄어쓰기가 없거나 정규화된 형태일 수 있음)
    # demand keys are like "백엔드개발자", "프론트엔드개발자" etc.
    # normalize_text removes spaces and lowercases.
    for role_key in roles_demand.keys():
        if normalize_text(role_key) == normalized_input:
            return role_key

    # 2. 키워드 매칭 스코어링
    best_role = None
    best_score = 0
    
    compressed_input = normalized_input.replace(" ", "")
    
    for role_key, keywords in ROLE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            norm_kw = normalize_text(kw).replace(" ", "")
            if norm_kw and norm_kw in compressed_input:
                score += 1
                
        if score > best_score:
            best_score = score
            best_role = role_key

    if best_score > 0 and best_role in roles_demand:
        return best_role
        
    # fallback
    if best_score > 0:
        return best_role # 수요 데이터에는 없을지라도 해석은 성공한 경우
        
    return None


def analyze_gap(profile: Dict[str, Any], demand: Dict[str, Any], role: Optional[str] = None) -> Dict[str, Any]:
    """
    사용자 프로필과 수요 분포를 비교하여 Gap 리포트를 생성한다.
    
    반환 스키마:
    {
      "role": "백엔드개발자",
      "role_resolved": true,
      "position_count": 24,
      "readiness_score": 0.62,
      "matched_skills": [{"skill": "java", "pct": 0.75}, ...],
      "missing_skills": [{"skill": "aws", "pct": 0.5}],
      "extra_skills": ["mysql"],
      "top_strengths": [{"skill": "java", "pct": 0.75}],
      "notes": []
    }
    """
    notes = []
    
    # 1. 직군 해석
    if not role:
        desired_role = profile.get("desired_role", "")
        role = resolve_role(desired_role, demand)
        
    if not role:
        notes.append("희망 직군을 표준 직군으로 해석하지 못했습니다.")
        # 직군 해석 실패 시 빈 결과 반환
        return {
            "role": None,
            "role_resolved": False,
            "position_count": 0,
            "readiness_score": 0.0,
            "matched_skills": [],
            "missing_core_skills": [],
            "missing_tail_count": 0,
            "extra_skills": [],
            "top_strengths": [],
            "notes": notes
        }
        
    # 2. 직군 수요 데이터 존재 확인
    roles_demand = demand.get("roles", {})
    role_demand = roles_demand.get(role)
    
    if not role_demand:
        notes.append("해당 직군의 수요 데이터가 없습니다.")
        return {
            "role": role,
            "role_resolved": True,
            "position_count": 0,
            "readiness_score": 0.0,
            "matched_skills": [],
            "missing_core_skills": [],
            "missing_tail_count": 0,
            "extra_skills": [],
            "top_strengths": [],
            "notes": notes
        }

    # 3. 사용자 스킬 정규화 및 중복 제거
    raw_skills = profile.get("skills", [])
    user_skills = {normalize_text(s) for s in raw_skills if str(s).strip()}
    
    # 4. 수요 스킬 매칭
    tech_stack = role_demand.get("tech_stack", [])
    
    # 핵심(core) 수요 추출
    c_skills = core_skills(tech_stack)
    core_skills_map = {item["skill"]: item["pct"] for item in c_skills}
    core_skill_set = set(core_skills_map.keys())
    
    demand_skills_map = {item["skill"]: item["pct"] for item in tech_stack}
    demand_skill_set = set(demand_skills_map.keys())
    
    # 보유 ∩ 전체수요
    matched_set = user_skills.intersection(demand_skill_set)
    matched_skills = [{"skill": s, "pct": demand_skills_map[s]} for s in matched_set]
    matched_skills.sort(key=lambda x: x["pct"], reverse=True)
    
    # 보유 ∩ core (강점)
    top_strengths_set = user_skills.intersection(core_skill_set)
    top_strengths = [{"skill": s, "pct": core_skills_map[s]} for s in top_strengths_set]
    top_strengths.sort(key=lambda x: x["pct"], reverse=True)
    
    # core 중 미보유
    missing_core_set = core_skill_set.difference(user_skills)
    missing_core_skills = [{"skill": s, "pct": core_skills_map[s]} for s in missing_core_set]
    missing_core_skills.sort(key=lambda x: x["pct"], reverse=True)
    
    # 전체 미보유 중 core가 아닌 꼬리 개수
    missing_all_set = demand_skill_set.difference(user_skills)
    missing_tail_count = len(missing_all_set) - len(missing_core_set)
    
    # 추가 보유 (보유 - 전체수요)
    extra_set = user_skills.difference(demand_skill_set)
    extra_skills = list(extra_set)
    
    # 5. readiness_score 계산 (core 기준)
    matched_core_pct_sum = sum(item["pct"] for item in top_strengths)
    total_core_pct_sum = sum(item["pct"] for item in c_skills)
    
    if total_core_pct_sum > 0:
        readiness_score = round(matched_core_pct_sum / total_core_pct_sum, 3)
    else:
        readiness_score = 0.0
        
    return {
        "role": role,
        "role_resolved": True,
        "position_count": role_demand.get("position_count", 0),
        "readiness_score": readiness_score,
        "matched_skills": matched_skills,
        "missing_core_skills": missing_core_skills,
        "missing_tail_count": missing_tail_count,
        "extra_skills": extra_skills,
        "top_strengths": top_strengths,
        "notes": notes
    }


def rank_roles_by_fit(profile: Dict[str, Any], demand: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
    """
    모든 직군에 대해 readiness_score를 계산하여 적합도 높은 순으로 정렬해 반환한다.
    position_count가 3 미만인 직군은 신뢰도가 낮으므로 결과에서 제외한다.
    """
    roles_demand = demand.get("roles", {})
    ranked = []
    
    for role_key, role_demand in roles_demand.items():
        if role_demand.get("position_count", 0) < 3:
            continue
            
        report = analyze_gap(profile, demand, role=role_key)
        ranked.append({
            "role": role_key,
            "readiness_score": report["readiness_score"],
            "position_count": report["position_count"]
        })
        
    ranked.sort(key=lambda x: x["readiness_score"], reverse=True)
    return ranked[:top_n]


def render_markdown(report: Dict[str, Any]) -> str:
    """
    analyze_gap의 결과를 사람이 읽을 수 있는 마크다운 형태로 변환한다.
    """
    lines = []
    role = report.get("role") or "알 수 없음"
    resolved = report.get("role_resolved", False)
    pos_count = report.get("position_count", 0)
    score = report.get("readiness_score", 0.0)
    
    lines.append(f"# 직무 적합도 리포트: {role}")
    
    for note in report.get("notes", []):
        lines.append(f"> ⚠️ **참고**: {note}")
        
    if not resolved or pos_count == 0:
        return "\n".join(lines)
        
    lines.append(f"\n- **분석 기준**: {role} 시장 공고 {pos_count}건")
    lines.append(f"- **종합 적합도(핵심 수요 스킬 기준)**: **{score * 100:.1f}%**\n")
    
    # 강점
    strengths = report.get("top_strengths", [])
    if strengths:
        lines.append("## 🌟 주요 강점 (핵심 수요 보유)")
        for item in strengths:
            pct = item["pct"] * 100
            bar = "█" * max(1, round(item["pct"] * 20))
            lines.append(f"- **{item['skill']}** ({pct:.1f}%의 공고에서 요구됨) {bar}")
        lines.append("")
        
    # 보유 스킬 (매칭)
    matched = report.get("matched_skills", [])
    if matched:
        lines.append("## ✅ 보유 스킬 (전체 시장 요구 일치)")
        for item in matched:
            pct = item["pct"] * 100
            bar = "█" * max(1, round(item["pct"] * 20))
            lines.append(f"- {item['skill']:<12} {pct:5.1f}% {bar}")
        lines.append("")
        
    # 부족 스킬 (미싱)
    missing = report.get("missing_core_skills", [])
    if missing:
        lines.append("## 🎯 학습 우선순위 (부족한 핵심 스킬)")
        for item in missing:
            pct = item["pct"] * 100
            bar = "▒" * max(1, round(item["pct"] * 20))
            lines.append(f"- {item['skill']:<12} {pct:5.1f}% {bar}")
        lines.append("")
        
    missing_tail = report.get("missing_tail_count", 0)
    if missing_tail > 0:
        lines.append(f"- 그 외 {missing_tail}개의 비핵심 스킬\n")
        
    # 추가 스킬
    extra = report.get("extra_skills", [])
    if extra:
        lines.append("## ➕ 추가 보유 스킬 (타 직무 전이 가능성)")
        lines.append(f"- {', '.join(extra)}")
        
    return "\n".join(lines)
