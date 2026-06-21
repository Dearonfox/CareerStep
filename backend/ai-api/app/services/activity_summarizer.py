import asyncio
from datetime import date, datetime
from app.core.mongo import mongo
from app.core.config import settings
from app.gateway import gpt_gateway
from app.services.prompts import ACTIVITY_SUMMARIZE_TEXT_SYSTEM_PROMPT, ACTIVITY_SUMMARIZE_IMAGE_SYSTEM_PROMPT
from app.services.image_tiler import prepare_image_inputs
from app.schemas_summarize import ActivitySummaryResult, SummarizeBatchResult


def _is_expired(deadline_date_str: str) -> bool:
    """application_deadline_date(YYYY-MM-DD)가 오늘보다 이전이면 True. 빈 값/파싱 실패는 만료로 보지 않음."""
    if not deadline_date_str:
        return False
    try:
        deadline = datetime.strptime(deadline_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return False
    return deadline < date.today()

class ActivitySummarizer:
    """MongoDB activities 컬렉션에서 status: 'detailed' 게시글을 읽어 GPT로 요약/관련성 판단 후 결과 저장"""

    async def run_batch(self, limit: int = None) -> SummarizeBatchResult:
        """배치 요약 실행"""
        batch_size = limit or settings.summarize_batch_size
        cursor = mongo.activities.find({"status": "detailed"}).limit(batch_size)
        articles = await cursor.to_list(length=batch_size)

        if not articles:
            return SummarizeBatchResult()

        tasks = [self._summarize_one(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        batch_result = SummarizeBatchResult(total_processed=len(articles))
        for res in results:
            if isinstance(res, Exception):
                batch_result.failed_count += 1
                batch_result.errors.append({"error": str(res)})
            else:
                batch_result.success_count += 1
                if not res.get("is_relevant", True):
                    batch_result.skipped_not_relevant += 1
                elif _is_expired(res.get("application_deadline_date", "")):
                    batch_result.skipped_expired += 1

        return batch_result

    async def _summarize_one(self, article: dict) -> dict:
        """단일 게시글 요약 처리"""
        try:
            if article.get("is_image_job"):
                result = await self._summarize_image(article)
            else:
                result = await self._summarize_text(article)

            if not result.get("is_relevant", True):
                # 대외활동이 아니라고 GPT가 최종 판단한 글은 DB에서 바로 제거
                await mongo.activities.delete_one({"_id": article["_id"]})
                return result

            if _is_expired(result.get("application_deadline_date", "")):
                # 신청 마감일이 이미 지난 공고도 제거
                await mongo.activities.delete_one({"_id": article["_id"]})
                return result

            await mongo.activities.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "summary": result,
                    # 조회/정렬 편의를 위해 최상위 필드에도 마감일을 복사해둠
                    "application_deadline": result.get("application_deadline", ""),
                    "application_deadline_date": result.get("application_deadline_date", ""),
                    "status": "summarized",
                    "summarized_at": datetime.now().isoformat()
                }}
            )
            return result
        except Exception as e:
            await mongo.activities.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "status": "summary_failed",
                    "summary_error": str(e),
                    "summarized_at": datetime.now().isoformat()
                }}
            )
            raise e

    async def _summarize_text(self, article: dict) -> dict:
        payload = {
            "board_name": article.get("board_name", ""),
            "category": article.get("category", ""),
            "title": article.get("title", ""),
            "post_date": article.get("post_date", ""),
            "detail_markdown": article.get("detail_markdown", "")
        }
        return await gpt_gateway.chat_json(
            system_prompt=ACTIVITY_SUMMARIZE_TEXT_SYSTEM_PROMPT,
            payload=payload,
            endpoint="/activities/summarize/text",
            response_format=ActivitySummaryResult,
            model="gpt-4.1-mini",
            estimated_tokens=2000
        )

    async def _summarize_image(self, article: dict) -> dict:
        raw_urls = article.get("image_urls", [])
        prepared_urls = await prepare_image_inputs(raw_urls)

        model = "gpt-4.1-mini"

        text_payload = {
            "board_name": article.get("board_name", ""),
            "category": article.get("category", ""),
            "title": article.get("title", ""),
            "post_date": article.get("post_date", "")
        }
        return await gpt_gateway.chat_vision_json(
            system_prompt=ACTIVITY_SUMMARIZE_IMAGE_SYSTEM_PROMPT,
            text_payload=text_payload,
            image_urls=prepared_urls,
            endpoint="/activities/summarize/image",
            response_format=ActivitySummaryResult,
            model=model
        )
