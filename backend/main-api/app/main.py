from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import Base, engine
from app import models
from app.routers import activities, admin, ai_proxy, auth, jobs, preferences, profiles

app = FastAPI(title="CareerStep Main Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["profiles"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(activities.router, prefix="/api/v1/activities", tags=["activities"])
app.include_router(ai_proxy.router, prefix="/api/v1/ai", tags=["ai-proxy"])
app.include_router(preferences.router, prefix="/api/v1/preferences", tags=["preferences"])


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_profile_columns()


def ensure_profile_columns() -> None:
    """Add profile columns introduced after the initial deployment.

    SQLAlchemy create_all creates missing tables, but it does not migrate
    existing tables. Render/MySQL deployments created before the profile
    parser merge need these columns before /profiles/me can be queried.
    """
    inspector = inspect(engine)
    if "profiles" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("profiles")}
    dialect = engine.dialect.name
    string_type = "VARCHAR(20)" if dialect == "mysql" else "VARCHAR(20)"
    short_string_type = "VARCHAR(10)" if dialect == "mysql" else "VARCHAR(10)"
    integer_type = "INT" if dialect == "mysql" else "INTEGER"
    text_type = "TEXT"

    migrations = {
        "target_roles": (text_type, "'[]'"),
        "career_level": (string_type, "''"),
        "skills_detail": (text_type, "'{}'"),
        "education": (text_type, "'[]'"),
        "experience": (text_type, "'[]'"),
        "projects_detail": (text_type, "'[]'"),
        "gpa": (short_string_type, "''"),
        "gpa_scale": (short_string_type, "''"),
        "transcript_strong_subjects": (text_type, "'[]'"),
        "transcript_weak_subjects": (text_type, "'[]'"),
        "total_credits": (string_type, "''"),
        "completed_semesters": (short_string_type, "''"),
        "portfolio_projects": (text_type, "'[]'"),
        "portfolio_total_count": (integer_type, "0"),
        "portfolio_solo_count": (integer_type, "0"),
        "portfolio_team_count": (integer_type, "0"),
        "portfolio_deployed_count": (integer_type, "0"),
        "portfolio_total_months": (integer_type, "0"),
    }

    with engine.begin() as connection:
        for column_name, (column_type, default_value) in migrations.items():
            if column_name in existing_columns:
                continue
            quoted_column = f"`{column_name}`" if dialect == "mysql" else f'"{column_name}"'
            connection.execute(text(f"ALTER TABLE profiles ADD COLUMN {quoted_column} {column_type}"))
            connection.execute(text(f"UPDATE profiles SET {quoted_column} = {default_value} WHERE {quoted_column} IS NULL"))


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "main-backend"}
