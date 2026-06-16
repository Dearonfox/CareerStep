from pydantic import BaseModel, Field


class ProfileInput(BaseModel):
    desired_role: str
    skills: list[str] = []
    certificates: list[str] = []
    projects: list[str] = []


class JobInput(BaseModel):
    id: int
    title: str
    company: str
    location: str
    employment_type: str
    skills: list[str]
    description: str


class RecommendJobsRequest(BaseModel):
    profile: ProfileInput
    jobs: list[JobInput] = Field(max_length=20)


class RecommendedJob(BaseModel):
    job_id: int
    match_score: int = Field(ge=0, le=100)
    reason: str
    matched_skills: list[str]
    missing_skills: list[str]


class RoadmapStep(BaseModel):
    order: int
    title: str
    description: str


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
