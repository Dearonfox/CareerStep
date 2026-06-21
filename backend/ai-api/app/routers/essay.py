from fastapi import APIRouter, Depends

from app.core.security import verify_internal_key
from app.schemas import EssayDraftRequest, EssayDraftResponse
from app.gateway import gpt_gateway
from app.services.prompts import ESSAY_DRAFT_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/draft", response_model=EssayDraftResponse)
async def draft_essay(payload: EssayDraftRequest) -> EssayDraftResponse:
    result = await gpt_gateway.chat_json(
        system_prompt=ESSAY_DRAFT_SYSTEM_PROMPT,
        payload=payload.model_dump(),
        endpoint="/essay/draft",
        response_format=EssayDraftResponse
    )
    return EssayDraftResponse.model_validate(result)
