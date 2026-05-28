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
    desired_role: str = Field(min_length=1, max_length=100)
    skills: list[str] = []
    certificates: list[str] = []
    projects: list[str] = []


class ProfileRead(ProfileUpsert):
    id: int
    user_id: int

    @field_validator("skills", "certificates", "projects", mode="before")
    @classmethod
    def parse_json_list(cls, value: object) -> list[str]:
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
