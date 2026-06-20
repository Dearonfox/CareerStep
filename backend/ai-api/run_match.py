import argparse
import asyncio
import json
import os
from app.services.demand_aggregator import aggregate_demand
from app.services.matcher import retrieve_candidates, match_jobs
from app.core.mongo import mongo

def load_samples():
    with open("demand_profiles.json", "r", encoding="utf-8") as f:
        # Wait, demand_profiles.json is just demand, I need raw jobs to extract positions!
        pass
        
    # We should use summarized_samples directory if "samples" is chosen.
    jobs = []
    sample_dir = "summarized_samples"
    if os.path.exists(sample_dir):
        for fname in os.listdir(sample_dir):
            if fname.endswith(".json"):
                with open(os.path.join(sample_dir, fname), "r", encoding="utf-8") as f:
                    jobs.append(json.load(f))
    return jobs

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["samples", "mongo"], default="samples")
    args = parser.parse_args()
    
    if args.source == "samples":
        jobs = load_samples()
    else:
        # DB 연결 초기화
        from app.core.config import settings
        await mongo.connect(settings.mongodb_uri)
        cursor = mongo.job_raw.find({"status": "routed"})
        jobs = await cursor.to_list(length=None)
        await mongo.close()
        
    if not jobs:
        print("No jobs found.")
        return
        
    demand = aggregate_demand(jobs)
    
    positions = []
    for job in jobs:
        summary = job.get("summary", {})
        rels = summary.get("relevant_positions", [])
        for p in rels:
            pos_dict = dict(p)
            # MongoDB나 샘플에서 job_id가 없을 경우 _id 사용
            j_id = job.get("job_id") or job.get("_id", "")
            pos_dict["job_id"] = str(j_id)
            pos_dict["company_name"] = job.get("company_name", "")
            positions.append(pos_dict)
            
    profile = {
        "desired_role": "백엔드 개발자",
        "skills": ["Java", "스프링부트"],
        "certificates": ["정보처리기사"],
        "projects": ["쇼핑몰 API 개발"]
    }
    
    print("=" * 50)
    print("1. 후보 검색 (LLM 없이 결정론적 풀 확보)")
    candidates = retrieve_candidates(profile, positions, demand)
    print(f"후보 {len(candidates)}개 검색 완료:")
    for c in candidates:
        print(f"  - [{c['job_id']}] {c['company']} - {c['position_title']} (score: {c.get('_retrieval_score', 0):.2f})")
        
    from app.core.config import settings
    api_key = settings.openai_api_key
    if not api_key or api_key in ("sk-change-me", "sk-test-key-not-real"):
        print("\nOPENAI_API_KEY가 없어 매칭 채점은 생략합니다. (.env의 OPENAI_API_KEY 확인)")
        return

    print("\n2. 일괄 채점 (LLM 1회) + 로드맵 생성 (LLM 1회) = 총 2콜")
    response = await match_jobs(profile, positions, demand, model=settings.openai_model, include_roadmap=True)
    
    report_lines = []
    report_lines.append("# AI 추천 리포트\n")
    report_lines.append("## 추천 포지션\n")
    for rec in response.recommendations:
        report_lines.append(f"### Job ID: {rec.job_id} - {rec.position_title} (매칭 점수: {rec.match_score}점)")
        report_lines.append(f"**추천 사유**: {rec.reason}")
        report_lines.append(f"**보유 스킬**: {', '.join(rec.matched_skills)}")
        report_lines.append(f"**부족 스킬**: {', '.join(rec.missing_skills)}\n")
        
    report_lines.append("## 종합 강점\n")
    for s in response.strengths:
        report_lines.append(f"- {s}")
        
    report_lines.append("\n## 핵심 갭\n")
    for g in response.gaps:
        report_lines.append(f"- {g}")
        
    report_lines.append("\n## 로드맵\n")
    if response.roadmap:
        for step in response.roadmap:
            report_lines.append(f"### {step.order}. {step.title}")
            report_lines.append(f"**왜 필요한가**: {step.why}")
            report_lines.append(f"**어떻게 학습할까**: {step.how}")
            report_lines.append(f"**예상 기간**: {step.duration}")
            report_lines.append(f"**완료 후 역량**: {step.outcome}\n")
    else:
        report_lines.append("_로드맵이 생성되지 않았습니다._\n")
        
    with open("match_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print("match_report.md 생성 완료.")

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
