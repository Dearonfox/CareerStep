from fastapi import APIRouter, Depends

from app.core.logging import write_ai_log
from app.core.security import verify_internal_key
from app.schemas import ResumeParseRequest, ResumeParseResponse
from app.services.openai_client import request_json
from app.services.prompts import RESUME_PARSE_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/parse", response_model=ResumeParseResponse)
def parse_resume(payload: ResumeParseRequest) -> ResumeParseResponse:
    result = request_json(RESUME_PARSE_SYSTEM_PROMPT, payload.model_dump())
    response = ResumeParseResponse.model_validate(result)
    write_ai_log("/resume/parse", payload.model_dump(), response.model_dump())
    return response
