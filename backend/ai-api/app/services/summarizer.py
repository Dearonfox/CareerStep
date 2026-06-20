import asyncio
from datetime import datetime
from app.core.mongo import mongo
from app.core.config import settings
from app.gateway import gpt_gateway
from app.services.prompts import SUMMARIZE_TEXT_SYSTEM_PROMPT, SUMMARIZE_IMAGE_SYSTEM_PROMPT
from app.services.image_tiler import prepare_image_inputs
from app.schemas_summarize import SummarizeBatchResult, JobSummaryResult

class JobSummarizer:
    """MongoDB에서 status: 'detailed' 공고를 읽어 GPT로 요약한 뒤 결과를 저장"""

    async def run_batch(self, limit: int = None) -> SummarizeBatchResult:
        """배치 요약 실행"""
        batch_size = limit or settings.summarize_batch_size
        cursor = mongo.job_raw.find({"status": "detailed"}).limit(batch_size)
        jobs = await cursor.to_list(length=batch_size)

        if not jobs:
            return SummarizeBatchResult()

        tasks = [self._summarize_one(job) for job in jobs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        batch_result = SummarizeBatchResult(total_processed=len(jobs))
        for res in results:
            if isinstance(res, Exception):
                batch_result.failed_count += 1
                batch_result.errors.append({"error": str(res)})
            else:
                batch_result.success_count += 1
                if not res.get("is_relevant", True):
                    batch_result.skipped_not_relevant += 1

        return batch_result

    async def _summarize_one(self, job: dict) -> dict:
        """단일 공고 요약 처리"""
        try:
            if job.get("is_image_job"):
                result = await self._summarize_image(job)
            else:
                result = await self._summarize_text(job)

            # MongoDB 업데이트
            await mongo.job_raw.update_one(
                {"_id": job["_id"]},
                {"$set": {
                    "summary": result,
                    "status": "summarized",
                    "summarized_at": datetime.now().isoformat()
                }}
            )
            return result
        except Exception as e:
            await mongo.job_raw.update_one(
                {"_id": job["_id"]},
                {"$set": {
                    "status": "summary_failed",
                    "summary_error": str(e),
                    "summarized_at": datetime.now().isoformat()
                }}
            )
            raise e

    async def _summarize_text(self, job: dict) -> dict:
        payload = {
            "company_name": job.get("company_name", ""),
            "title": job.get("title", ""),
            "detail_markdown": job.get("detail_markdown", "")
        }
        return await gpt_gateway.chat_json(
            system_prompt=SUMMARIZE_TEXT_SYSTEM_PROMPT,
            payload=payload,
            endpoint="/summarize/text",
            response_format=JobSummaryResult,
            model="gpt-4.1-mini",
            estimated_tokens=2000
        )

    async def _summarize_image(self, job: dict) -> dict:
        raw_urls = job.get("image_urls", [])
        prepared_urls = await prepare_image_inputs(raw_urls)
        
        # 비용 최적화: 타일 수가 2개 이하일 때만 4.1-mini, 그 외엔 fallback 모델(여기선 4.1-mini 그대로 사용)
        model = "gpt-4.1-mini"
        if len(prepared_urls) > 2:
            model = "gpt-4.1-mini" # User requested to use gpt-4.1-mini explicitly for all
        
        text_payload = {
            "company_name": job.get("company_name", ""),
            "title": job.get("title", "")
        }
        return await gpt_gateway.chat_vision_json(
            system_prompt=SUMMARIZE_IMAGE_SYSTEM_PROMPT,
            text_payload=text_payload,
            image_urls=prepared_urls,
            endpoint="/summarize/image",
            response_format=JobSummaryResult,
            model=model
        )
