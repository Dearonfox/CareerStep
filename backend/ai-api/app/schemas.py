from pydantic import BaseModel, Field


class ProfileInput(BaseModel):
    desired_role: str
    skills: list[str] = []
    certificates: list[str] = []
    projects: list[str] = []


class CandidateJob(BaseModel):
    job_id: str
    position_title: str
    company: str
    experience_level: str | None = None
    tech_stack: list[str] = []
    requirements: list[str] = []
    preferred: list[str] = []
    main_tasks: list[str] = []


class RecommendJobsRequest(BaseModel):
    profile: ProfileInput
    candidates: list[CandidateJob] = Field(max_length=20)
    market_demand_top: list[str] = []


class RecommendedJob(BaseModel):
    job_id: str
    position_title: str
    match_score: int = Field(ge=0, le=100)
    reason: str
    matched_skills: list[str]
    missing_skills: list[str]


class RoadmapStep(BaseModel):
    order: int
    title: str          # 예: "AWS 클라우드 기초 다지기"
    why: str            # 왜 필요한가 — 사용자 걘/목표 직점 수요 근거
    how: str            # 어떻게 — 구체적 학습 주제 + 실습/미니 프로젝트 제안
    duration: str       # 예상 소요 기간 (예: "2~3주")
    outcome: str        # 완료 시 갖추게 될 역량/산출물


class RoadmapResponse(BaseModel):
    roadmap: list[RoadmapStep]
    summary: str        # 로드맵 전체를 1~2문장으로 요약한 방향성


class RecommendJobsResponse(BaseModel):
    recommendations: list[RecommendedJob]
    strengths: list[str]
    gaps: list[str]
    roadmap: list[RoadmapStep]
    policy_violation: bool = False


class ResumeParseRequest(BaseModel):
    resume_text: str


class SkillSet(BaseModel):
    languages: list[str] = []
    frameworks: list[str] = []
    databases: list[str] = []
    cloud_devops: list[str] = []
    tools: list[str] = []
    others: list[str] = []


class Education(BaseModel):
    school: str = ""
    major: str = ""
    degree: str = ""
    graduation_status: str = ""


class Experience(BaseModel):
    company: str = ""
    position: str = ""
    period: str = ""
    description: str = ""


class ProjectDetail(BaseModel):
    name: str = ""
    summary: str = ""
    technologies: list[str] = []
    period: str = ""
    role: str = ""
    outcomes: list[str] = []


class ResumeParseResponse(BaseModel):
    target_roles: list[str] = []
    career_level: str = ""
    skills: SkillSet = Field(default_factory=SkillSet)
    certificates: list[str] = []
    education: list[Education] = []
    experience: list[Experience] = []
    projects: list[ProjectDetail] = []


class TranscriptParseRequest(BaseModel):
    transcript_text: str


class SubjectEntry(BaseModel):
    name: str = ""
    grade: str = ""
    relevance: str = ""


class TranscriptParseResponse(BaseModel):
    gpa: str = ""
    gpa_scale: str = ""
    strong_subjects: list[SubjectEntry] = []
    weak_subjects: list[SubjectEntry] = []
    total_credits: str = ""
    major: str = ""
    completed_semesters: str = ""


class PortfolioParseRequest(BaseModel):
    portfolio_text: str


class PortfolioProject(BaseModel):
    name: str = ""
    period: str = ""
    duration_months: int = 0
    team_type: str = ""
    team_size: int = 0
    my_role: str = ""
    contribution_percent: int = 0
    technologies: list[str] = []
    is_deployed: bool = False
    deploy_url: str = ""
    outcomes: list[str] = []


class PortfolioParseResponse(BaseModel):
    projects: list[PortfolioProject] = []
    total_project_count: int = 0
    solo_project_count: int = 0
    team_project_count: int = 0
    deployed_project_count: int = 0
    total_duration_months: int = 0


class EssayDraftRequest(BaseModel):
    profile: ProfileInput
    job_title: str
    company: str
    question: str


class EssayDraftResponse(BaseModel):
    draft: list[str]
    used_evidence: list[str]
    warnings: list[str]
    policy_violation: bool = False
