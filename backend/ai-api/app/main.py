from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.logging import init_log_db
from app.routers import essay, recommendations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 비동기 SQLite DB 초기화
    await init_log_db()
    yield


app = FastAPI(title="CareerStep AI Backend", version="0.1.0", lifespan=lifespan)

app.include_router(recommendations.router, prefix="/api/v1/recommend", tags=["recommendations"])
app.include_router(essay.router, prefix="/api/v1/essay", tags=["essay"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ai-backend"}
