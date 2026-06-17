from fastapi import APIRouter, Depends

from app.core.logging import write_ai_log
from app.core.security import verify_internal_key
from app.schemas import PortfolioParseRequest, PortfolioParseResponse
from app.services.openai_client import request_json
from app.services.prompts import PORTFOLIO_PARSE_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/parse", response_model=PortfolioParseResponse)
def parse_portfolio(payload: PortfolioParseRequest) -> PortfolioParseResponse:
    result = request_json(PORTFOLIO_PARSE_SYSTEM_PROMPT, payload.model_dump())
    response = PortfolioParseResponse.model_validate(result)
    write_ai_log("/portfolio/parse", payload.model_dump(), response.model_dump())
    return response
