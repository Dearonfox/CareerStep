from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.logging import init_log_db
from app.core.mongo import mongo
from app.core.config import settings
from app.routers import essay, portfolio, recommendations, resume, summarize, transcript


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 비동기 SQLite DB 초기화
    await init_log_db()
    print("Connecting to MongoDB...", settings.mongodb_uri)
    if settings.mongodb_uri:
        await mongo.connect(settings.mongodb_uri)
        print("Connected to MongoDB, db is:", mongo.db)
    yield
    await mongo.close()


app = FastAPI(title="CareerStep AI Backend", version="0.1.0", lifespan=lifespan)

app.include_router(recommendations.router, prefix="/api/v1/recommend", tags=["recommendations"])
app.include_router(essay.router, prefix="/api/v1/essay", tags=["essay"])
app.include_router(resume.router, prefix="/api/v1/resume", tags=["resume"])
app.include_router(transcript.router, prefix="/api/v1/transcript", tags=["transcript"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(summarize.router, prefix="/api/v1/summarize", tags=["summarize"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ai-backend"}
