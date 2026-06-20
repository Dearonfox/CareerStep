import asyncio
import json
import sys
from app.core.mongo import mongo
from app.core.config import settings
from app.services.router import process_routing_for_job

async def test_routing_on_db():
    sys.stdout.reconfigure(encoding='utf-8')
    print("Connecting to MongoDB...")
    await mongo.connect(settings.mongodb_uri)
    print("Fetching 20 'summarized' jobs from MongoDB...")
    
    cursor = mongo.job_raw.find({"summary": {"$exists": True}}).limit(20)
    jobs = await cursor.to_list(length=20)
    
    if not jobs:
        print("No summarized jobs found in DB.")
        return

    output_lines = []
    output_lines.append("# 라우팅 결과 테스트 (20개 샘플)\n")
    output_lines.append(f"총 {len(jobs)}개의 공고에 대해 라우팅 로직을 실행했습니다.\n")
    
    for job in jobs:
        output_lines.append(f"## {job.get('company_name')} - {job.get('title')}")
        output_lines.append(f"**Job ID:** `{job.get('job_id')}`\n")
        
        routed_job = process_routing_for_job(job)
        summary = routed_job.get("summary", {})
        positions = summary.get("relevant_positions", [])
        
        if not positions:
            output_lines.append("> [!WARNING]\n> 추출된 포지션이 없습니다.\n")
            
        for idx, pos in enumerate(positions, 1):
            output_lines.append(f"### [포지션 {idx}] {pos.get('position_title')}")
            output_lines.append(f"- **기술 스택:** `{pos.get('tech_stack')}`")
            output_lines.append(f"- **주요 업무:** `{pos.get('main_tasks')}`")
            
            routed_roles = pos.get("routed_roles", [])
            roles_str = json.dumps(routed_roles, ensure_ascii=False)
            output_lines.append(f"- 🎯 **라우팅 결과:** `{roles_str}`\n")
            
        output_lines.append("---\n")
        
    with open("routing_test_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        
    print("Results saved to routing_test_results.md")

if __name__ == "__main__":
    asyncio.run(test_routing_on_db())
