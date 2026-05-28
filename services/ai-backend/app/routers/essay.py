from fastapi import APIRouter, Depends

from app.core.logging import write_ai_log
from app.core.security import verify_internal_key
from app.schemas import EssayDraftRequest, EssayDraftResponse
from app.services.openai_client import request_json
from app.services.prompts import ESSAY_DRAFT_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/draft", response_model=EssayDraftResponse)
def draft_essay(payload: EssayDraftRequest) -> EssayDraftResponse:
    result = request_json(ESSAY_DRAFT_SYSTEM_PROMPT, payload.model_dump())
    response = EssayDraftResponse.model_validate(result)
    write_ai_log("/essay/draft", payload.model_dump(), response.model_dump())
    return response
