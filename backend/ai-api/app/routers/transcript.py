from fastapi import APIRouter, Depends

from app.core.logging import write_ai_log
from app.core.security import verify_internal_key
from app.schemas import TranscriptParseRequest, TranscriptParseResponse
from app.services.openai_client import request_json
from app.services.prompts import TRANSCRIPT_PARSE_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/parse", response_model=TranscriptParseResponse)
def parse_transcript(payload: TranscriptParseRequest) -> TranscriptParseResponse:
    result = request_json(TRANSCRIPT_PARSE_SYSTEM_PROMPT, payload.model_dump())
    response = TranscriptParseResponse.model_validate(result)
    write_ai_log("/transcript/parse", payload.model_dump(), response.model_dump())
    return response
