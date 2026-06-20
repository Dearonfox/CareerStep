import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    """테스트마다 격리된 인메모리 SQLite DB를 제공합니다."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield TestingSessionLocal
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def fake_redis(monkeypatch):
    """app.core.redis의 모듈 단위 redis_client를 인메모리 dict로 대체합니다."""

    class FakeRedisClient:
        def __init__(self):
            self.store: dict[str, str] = {}

        def setex(self, key: str, _ttl: int, value: str) -> None:
            self.store[key] = value

        def get(self, key: str) -> str | None:
            return self.store.get(key)

        def delete(self, key: str) -> None:
            self.store.pop(key, None)

    fake_client = FakeRedisClient()
    monkeypatch.setattr("app.core.redis.redis_client", fake_client)
    return fake_client


@pytest.fixture()
def client(db_session, fake_redis):
    def override_get_db():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # TestClient(app)를 컨텍스트 매니저로 쓰지 않음 — startup 이벤트가 실제 MySQL engine으로
    # Base.metadata.create_all을 호출하는데, 테스트는 인메모리 SQLite만 써야 하므로 건너뜀
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """회원가입 후 Authorization 헤더와 토큰 쌍을 반환합니다."""
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "tester@example.com", "password": "password123", "name": "Tester"},
    )
    tokens = response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return headers, tokens
