from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, func
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

    user: Mapped[User] = relationship(back_populates="profile")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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
