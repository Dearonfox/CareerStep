from pymongo import MongoClient
from pymongo import ReplaceOne
from pymongo.server_api import ServerApi
from config import MONGODB_URI

class MongoDBClient:
    def __init__(self):
        self.uri = MONGODB_URI
        self.client = None
        self.db = None
        self.collection = None

        if not self.uri:
            print("❌ MongoDB Atlas URI가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
            return

        try:
            # PyMongo Atlas 가이드라인 준수: ServerApi('1') 지정
            self.client = MongoClient(self.uri, server_api=ServerApi('1'))
            self.db = self.client["careerstep"]
            self.collection = self.db["job_raw"]
            
            # 연결 상태 확인 (Ping)
            self.client.admin.command('ping')
            print("⚡ MongoDB Atlas 클라우드 연결에 성공했습니다!")
        except Exception as e:
            print(f"❌ MongoDB Atlas 연결 실패: {e}")

    def upsert_jobs(self, jobs: list[dict]) -> int:
        """
        고유 ID(job_id)를 MongoDB 도큐먼트 기본 식별자(_id)로 지정하여
        중복 없이 Upsert(없으면 삽입, 있으면 대체) 처리
        """
        if self.collection is None:
            print("❌ 데이터베이스가 연결되어 있지 않아 적재를 취소합니다.")
            return 0

        if not jobs:
            print("ℹ️ 적재할 공고 데이터가 없습니다.")
            return 0

        operations = []
        for job in jobs:
            doc = job.copy()
            # job_id를 고유 _id 필드로 치환 (중복 제거)
            doc["_id"] = doc["job_id"]
            
            # pipeline pending 상태 지정
            doc["status"] = "pending"
            doc["inserted_at"] = doc.get("scraped_at")
            
            # replace_one upsert 연산 객체 추가
            operations.append(
                ReplaceOne({"_id": doc["_id"]}, doc, upsert=True)
            )

        try:
            # bulk_write를 사용하여 한 번의 네트워크 요청으로 묶어서 적재
            result = self.collection.bulk_write(operations, ordered=False)
            # 신규 삽입 및 수정된 개수 합산 반환
            upserted_count = result.upserted_count + result.modified_count
            print(f"✅ MongoDB Atlas 적재 완료: 신규/변경 {upserted_count}개 (매칭 {result.matched_count}개)")
            return upserted_count
        except Exception as e:
            print(f"❌ bulk_write 실행 중 예외 발생: {e}")
            return 0

    def close(self):
        if self.client:
            self.client.close()
            print("🔌 MongoDB Atlas 연결 종료")
