from pydantic import BaseModel, Field


class PositionSummary(BaseModel):
    position_title: str = Field(description="채용하는 포지션의 직군명 또는 타이틀")
    experience_level: str | None = Field(None, description="요구하는 경력 수준 (예: 신입, 경력, 신입·경력 등). 정보가 없으면 null")
    main_tasks: list[str] = Field(..., description="담당할 주요 업무 내용. 없으면 빈 배열([])을 사용하세요.")
    requirements: list[str] = Field(..., description="자격 요건 (학력, 경력, 필수 기술 등). 없으면 빈 배열([])을 사용하세요.")
    preferred: list[str] = Field(..., description="우대 사항. 없으면 빈 배열([])을 사용하세요.")
    tech_stack: list[str] = Field(..., description="요구하거나 우대하는 기술 스택 및 툴. 없으면 빈 배열([])을 사용하세요.")
    location: str | None = Field(None, description="근무지 주소 또는 위치. 정보가 없으면 null")
    benefits: list[str] = Field(..., description="제공하는 복지 및 혜택. 없으면 빈 배열([])을 사용하세요.")

class JobSummaryResult(BaseModel):
    is_relevant: bool = Field(..., description="IT/개발 관련 직군이 포함되어 있는지 여부. 포함되어 있다면 true, 아니면 false")
    relevant_positions: list[PositionSummary] = Field(..., description="공고에 포함된 모든 관련 포지션 목록. 카테고리와 무관하게 본문에 명시된 모든 관련 포지션을 빠짐없이 추출하세요. 관련 포지션이 없으면 빈 배열([])")
    filtered_out_positions: list[str] = Field(..., description="영업, 인사, 회계, 마케팅, 법무 등 개발과 명백히 무관한 직군명만 리스트로 저장. 해당 없으면 빈 리스트([])")
    total_positions_in_posting: int = Field(..., description="원본 채용공고에 명시된 모든 모집 포지션의 총 개수")
    deadline: str | None = Field(None, description="채용 마감일. 원본 텍스트/이미지에 명시된 그대로 저장. 없으면 null")

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
