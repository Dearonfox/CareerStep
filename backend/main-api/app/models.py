from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    profile: Mapped["Profile | None"] = relationship(back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    # 추천 엔진 호환용 단순 필드 (desired_role = target_roles[0])
    desired_role: Mapped[str] = mapped_column(String(100), default="")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    certificates: Mapped[str] = mapped_column(Text, default="[]")
    projects: Mapped[str] = mapped_column(Text, default="[]")

    # 이력서 파싱 결과 상세 필드
    target_roles: Mapped[str] = mapped_column(Text, default="[]")
    career_level: Mapped[str] = mapped_column(String(20), default="")
    skills_detail: Mapped[str] = mapped_column(Text, default="{}")
    education: Mapped[str] = mapped_column(Text, default="[]")
    experience: Mapped[str] = mapped_column(Text, default="[]")
    projects_detail: Mapped[str] = mapped_column(Text, default="[]")

    # 성적표 파싱 결과
    gpa: Mapped[str] = mapped_column(String(10), default="")
    gpa_scale: Mapped[str] = mapped_column(String(10), default="")
    transcript_strong_subjects: Mapped[str] = mapped_column(Text, default="[]")
    transcript_weak_subjects: Mapped[str] = mapped_column(Text, default="[]")
    total_credits: Mapped[str] = mapped_column(String(20), default="")
    completed_semesters: Mapped[str] = mapped_column(String(10), default="")

    # 포트폴리오 파싱 결과
    portfolio_projects: Mapped[str] = mapped_column(Text, default="[]")
    portfolio_total_count: Mapped[int] = mapped_column(Integer, default=0)
    portfolio_solo_count: Mapped[int] = mapped_column(Integer, default=0)
    portfolio_team_count: Mapped[int] = mapped_column(Integer, default=0)
    portfolio_deployed_count: Mapped[int] = mapped_column(Integer, default=0)
    portfolio_total_months: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="profile")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # 희망 목적지
    job_roles: Mapped[str] = mapped_column(Text, default="[]")
    company_types: Mapped[str] = mapped_column(Text, default="[]")
    preferred_regions: Mapped[str] = mapped_column(Text, default="[]")

    # 타임라인 및 제약조건
    target_timeline: Mapped[str] = mapped_column(String(50), default="")
    weekly_hours: Mapped[int] = mapped_column(Integer, default=0)
    wants_cert_upgrade: Mapped[bool] = mapped_column(Boolean, default=False)

    # 우선순위 영역
    priority_area: Mapped[str] = mapped_column(String(20), default="")

    user: Mapped[User] = relationship()


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mongo_id: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    company: Mapped[str] = mapped_column(String(150))
    location: Mapped[str] = mapped_column(String(150))
    employment_type: Mapped[str] = mapped_column(String(80))
    skills: Mapped[str] = mapped_column(Text, default="[]")
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
