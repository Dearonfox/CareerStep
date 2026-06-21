from fastapi import APIRouter, Depends

from app.core.logging import write_ai_log
from app.core.security import verify_internal_key
from app.gateway import gpt_gateway
from app.schemas import TranscriptParseRequest, TranscriptParseResponse
from app.services.prompts import TRANSCRIPT_PARSE_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/parse", response_model=TranscriptParseResponse)
async def parse_transcript(payload: TranscriptParseRequest) -> TranscriptParseResponse:
    result = await gpt_gateway.chat_json(
        system_prompt=TRANSCRIPT_PARSE_SYSTEM_PROMPT,
        payload=payload.model_dump(),
        endpoint="/transcript/parse",
    )
    response = TranscriptParseResponse.model_validate(result)
    await write_ai_log("/transcript/parse", payload.model_dump(), response.model_dump())
    return response
