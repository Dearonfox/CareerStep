import asyncio
import json
import os
from app.core.config import settings
from app.core.mongo import mongo

async def main():
    await mongo.connect(settings.mongodb_uri)
    
    # 저장할 폴더 생성
    output_dir = "summarized_samples"
    os.makedirs(output_dir, exist_ok=True)
    
    # 최근에 요약된 20건 가져오기
    cursor = mongo.job_raw.find({"status": "summarized"}).sort("summarized_at", -1).limit(20)
    jobs = await cursor.to_list(length=20)
    
    for i, job in enumerate(jobs):
        company = job.get("company_name", "Unknown")
        title = job.get("title", "No Title")
        # 파일명에서 사용할 수 없는 문자 제거
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        filename = f"{output_dir}/sample_{i+1:02d}_{company}_{safe_title[:30]}.json"
        
        # 저장할 데이터 구성
        export_data = {
            "_id": str(job.get("_id")),
            "company_name": company,
            "title": title,
            "is_image_job": job.get("is_image_job", False),
            "url": job.get("url"),
            "summarized_at": job.get("summarized_at"),
            "summary": job.get("summary", {})
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
            
    print(f"총 {len(jobs)}건의 요약 데이터가 '{output_dir}' 폴더에 저장되었습니다.")
            
    await mongo.close()

if __name__ == "__main__":
    asyncio.run(main())
