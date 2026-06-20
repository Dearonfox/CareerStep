import asyncio
from app.services.summarizer import JobSummarizer
from app.core.mongo import mongo

from app.core.config import settings

async def main():
    await mongo.connect(uri=settings.mongodb_uri)
    
    summarizer = JobSummarizer()
    print("Running batch summarize for 2 jobs...")
    result = await summarizer.run_batch(limit=2)
    
    print(f"Total processed: {result.total_processed}")
    print(f"Success: {result.success_count}")
    print(f"Failed: {result.failed_count}")
    print(f"Errors: {result.errors}")

    await mongo.close()

if __name__ == "__main__":
    asyncio.run(main())
