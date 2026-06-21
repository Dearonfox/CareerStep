from pymongo import AsyncMongoClient

class MongoManager:
    """PyMongo AsyncMongoClient 기반 비동기 MongoDB 관리자"""
    
    def __init__(self):
        self.client: AsyncMongoClient | None = None
        self.db = None

    async def connect(self, uri: str):
        self.client = AsyncMongoClient(uri)
        self.db = self.client["careerstep"]
        # 연결 상태 확인
        await self.client.admin.command("ping")

    async def close(self):
        if self.client:
            self.client.close()

    @property
    def job_raw(self):
        return self.db["job_raw"]

    @property
    def activities(self):
        return self.db["activities"]

mongo = MongoManager()  # 싱글톤
