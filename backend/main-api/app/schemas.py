import json

from pydantic import BaseModel, EmailStr, Field
from pydantic import field_validator

from app.models import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=2, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: UserRole

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class ProfileUpsert(BaseModel):
    desired_role: str = Field(default="", max_length=100)
    skills: list[str] = []
    certificates: list[str] = []
    projects: list[str] = []


class ProfileRead(ProfileUpsert):
    id: int
    user_id: int

    # 이력서 파싱 상세
    target_roles: list[str] = []
    career_level: str = ""
    skills_detail: dict = {}
    education: list[dict] = []
    experience: list[dict] = []
    projects_detail: list[dict] = []

    # 성적표 파싱
    gpa: str = ""
    gpa_scale: str = ""
    transcript_strong_subjects: list[dict] = []
    transcript_weak_subjects: list[dict] = []
    total_credits: str = ""
    completed_semesters: str = ""

    # 포트폴리오 파싱
    portfolio_projects: list[dict] = []
    portfolio_total_count: int = 0
    portfolio_solo_count: int = 0
    portfolio_team_count: int = 0
    portfolio_deployed_count: int = 0
    portfolio_total_months: int = 0

    @field_validator(
        "skills", "certificates", "projects", "target_roles",
        mode="before",
    )
    @classmethod
    def parse_json_list(cls, value: object) -> list:
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, list):
            return value
        return []

    @field_validator("skills_detail", mode="before")
    @classmethod
    def parse_json_dict(cls, value: object) -> dict:
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, dict):
            return value
        return {}

    @field_validator(
        "education", "experience", "projects_detail",
        "transcript_strong_subjects", "transcript_weak_subjects",
        "portfolio_projects",
        mode="before",
    )
    @classmethod
    def parse_json_list_of_dict(cls, value: object) -> list:
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, list):
            return value
        return []

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    title: str
    company: str
    location: str
    employment_type: str
    skills: list[str]
    description: str


class JobRead(JobCreate):
    id: int


class AIRecommendRequest(BaseModel):
    profile: ProfileUpsert
    jobs: list[JobRead]


class EssayDraftRequest(BaseModel):
    profile: ProfileUpsert
    job_title: str
    company: str
    question: str


class UserPreferenceUpsert(BaseModel):
    job_roles: list[str] = []
    company_types: list[str] = []
    preferred_regions: list[str] = []
    target_timeline: str = ""
    weekly_hours: int = 0
    wants_cert_upgrade: bool = False
    priority_area: str = ""


class UserPreferenceRead(UserPreferenceUpsert):
    id: int
    user_id: int

    @field_validator("job_roles", "company_types", "preferred_regions", mode="before")
    @classmethod
    def parse_json_list(cls, value: object) -> list:
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, list):
            return value
        return []

    model_config = {"from_attributes": True}


class TranscriptTextRequest(BaseModel):
    transcript_text: str


class PortfolioTextRequest(BaseModel):
    portfolio_text: str
