from fastapi import FastAPI

from app.routers import essay, portfolio, recommendations, resume, transcript

app = FastAPI(title="CareerStep AI Backend", version="0.1.0")

app.include_router(recommendations.router, prefix="/api/v1/recommend", tags=["recommendations"])
app.include_router(essay.router, prefix="/api/v1/essay", tags=["essay"])
app.include_router(resume.router, prefix="/api/v1/resume", tags=["resume"])
app.include_router(transcript.router, prefix="/api/v1/transcript", tags=["transcript"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ai-backend"}
