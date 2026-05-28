from fastapi import FastAPI

from app.routers import essay, recommendations

app = FastAPI(title="CareerStep AI Backend", version="0.1.0")

app.include_router(recommendations.router, prefix="/api/v1/recommend", tags=["recommendations"])
app.include_router(essay.router, prefix="/api/v1/essay", tags=["essay"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ai-backend"}
