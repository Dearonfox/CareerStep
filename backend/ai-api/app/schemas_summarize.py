from pydantic import BaseModel, Field


class PositionSummary(BaseModel):
    position_title: str
    experience_level: str = ""
    main_tasks: list[str] = []
    requirements: list[str] = []
    preferred: list[str] = []
    tech_stack: list[str] = []
    location: str = ""
    benefits: list[str] = []

class JobSummaryResult(BaseModel):
    is_relevant: bool = True
    relevant_positions: list[PositionSummary] = []
    filtered_out_positions: list[str] = []
    total_positions_in_posting: int = 0
    deadline: str = ""

class SummarizeBatchResult(BaseModel):
    total_processed: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_not_relevant: int = 0
    estimated_cost_usd: float = 0.0
    errors: list[dict] = []

class SummarizeRunRequest(BaseModel):
    limit: int | None = Field(None, description="처리할 최대 공고 수 (None이면 batch_size 기본값 사용)")
    dry_run: bool = Field(False, description="True이면 실제 GPT 호출 없이 대상 목록만 반환")

class SummarizeStatusResponse(BaseModel):
    total_jobs: int
    detailed: int
    summarized: int
    failed: int
    not_relevant: int
