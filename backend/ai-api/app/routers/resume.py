from fastapi import APIRouter, Depends

from app.core.logging import write_ai_log
from app.core.security import verify_internal_key
from app.schemas import ResumeParseRequest, ResumeParseResponse
from app.gateway import gpt_gateway
from app.services.prompts import RESUME_PARSE_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/parse", response_model=ResumeParseResponse)
async def parse_resume(payload: ResumeParseRequest) -> ResumeParseResponse:
    result = await gpt_gateway.chat_json(
        system_prompt=RESUME_PARSE_SYSTEM_PROMPT,
        payload=payload.model_dump(),
        endpoint="/resume/parse",
        response_format=ResumeParseResponse
    )
    response = ResumeParseResponse.model_validate(result)
    write_ai_log("/resume/parse", payload.model_dump(), response.model_dump())
    return response
