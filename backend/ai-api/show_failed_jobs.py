import asyncio
from app.core.config import settings
from app.core.mongo import mongo

async def main():
    await mongo.connect(settings.mongodb_uri)
    
    # 실패한 공고는 상태가 업데이트되지 않고 계속 'detailed'로 남아있음
    # 방금 전 성공한 18건은 'summarized'로 바뀌었으므로, 현재 가장 위에 잡히는 'detailed' 2건이 실패한 공고일 확률이 높음
    cursor = mongo.job_raw.find({"status": "detailed"}).limit(2)
    jobs = await cursor.to_list(length=2)
    
    for i, job in enumerate(jobs):
        print(f"\n======================================")
        print(f"실패 추정 데이터 #{i+1}")
        print(f"ID: {job.get('_id')}")
        print(f"제목: {job.get('title')}")
        print(f"회사: {job.get('company_name')}")
        print(f"이미지 공고 여부: {job.get('is_image_job')}")
        print(f"URL: {job.get('url')}")
        
        if job.get('is_image_job'):
            print(f"이미지 URL들: {job.get('image_urls')}")
        else:
            print(f"텍스트 일부(500자): {str(job.get('detail_markdown'))[:500]}...")
            
    await mongo.close()

if __name__ == "__main__":
    asyncio.run(main())
