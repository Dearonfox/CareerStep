from pymongo import MongoClient
from pymongo import ReplaceOne
from pymongo.server_api import ServerApi
from config import MONGODB_URI
from datetime import datetime

class MongoDBClient:
    def __init__(self):
        self.uri = MONGODB_URI
        self.client = None
        self.db = None
        self.collection = None

        if not self.uri:
            print("[오류] MongoDB Atlas URI가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
            return

        try:
            # PyMongo Atlas 가이드라인 준수: ServerApi('1') 지정
            self.client = MongoClient(self.uri, server_api=ServerApi('1'))
            self.db = self.client["careerstep"]
            self.collection = self.db["job_raw"]
            
            # 연결 상태 확인 (Ping)
            self.client.admin.command('ping')
            print("[연결] MongoDB Atlas 클라우드 연결에 성공했습니다!")
        except Exception as e:
            print(f"[오류] MongoDB Atlas 연결 실패: {e}")

    def upsert_jobs(self, jobs: list[dict]) -> int:
        """
        고유 ID(job_id)를 MongoDB 도큐먼트 기본 식별자(_id)로 지정하여
        중복 없이 Upsert(없으면 삽입, 있으면 대체) 처리
        """
        if self.collection is None:
            print("[오류] 데이터베이스가 연결되어 있지 않아 적재를 취소합니다.")
            return 0

        if not jobs:
            print("[정보] 적재할 공고 데이터가 없습니다.")
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
            print(f"[완료] MongoDB Atlas 적재 완료: 신규/변경 {upserted_count}개 (매칭 {result.matched_count}개)")
            return upserted_count
        except Exception as e:
            print(f"[오류] bulk_write 실행 중 예외 발생: {e}")
            return 0

    def update_job_detail(self, job_id: str, detail_data: dict) -> bool:
        """
        특정 공고 ID의 도큐먼트에 마크다운 상세 요강과 이미지 판별 플래그를 추가/업데이트하고
        status 값을 detailed (또는 에러 시 failed)로 갱신
        """
        if self.collection is None:
            print("[오류] 데이터베이스 연결이 없습니다.")
            return False

        # 업데이트할 필드 맵 구성
        update_fields = {
            "detail_markdown": detail_data.get("detail_markdown", ""),
            "is_image_job": detail_data.get("is_image_job", False),
            "image_urls": detail_data.get("image_urls", []),
            "detailed_at": datetime.now().isoformat()
        }

        # 에러 발생 케이스 대응
        if detail_data.get("error_message"):
            update_fields["status"] = "failed"
            update_fields["error_message"] = detail_data["error_message"]
        else:
            update_fields["status"] = "detailed"
            update_fields["error_message"] = None  # 기존 에러 초기화

        try:
            result = self.collection.update_one(
                {"_id": job_id},
                {"$set": update_fields}
            )
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            print(f"[오류] MongoDB 상세 정보 업데이트 실패 (ID: {job_id}): {e}")
            return False

    def upsert_activities(self, activities: list[dict]) -> int:
        """
        CSAI 대외활동 데이터를 csai_activities 컬렉션에 upsert.
        _id = board_code_article_id 기준으로 중복 방지.
        """
        if self.client is None:
            print("[오류] 데이터베이스가 연결되어 있지 않아 적재를 취소합니다.")
            return 0

        if not activities:
            print("[정보] 적재할 활동 데이터가 없습니다.")
            return 0

        collection = self.db["csai_activities"]
        operations = []
        for activity in activities:
            doc = activity.copy()
            doc["_id"] = f"{doc['board_code']}_{doc['article_id']}"
            doc["source"] = "jbnu_csai"
            doc.setdefault("scraped_at", datetime.now().isoformat())
            operations.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))

        try:
            result = collection.bulk_write(operations, ordered=False)
            upserted_count = result.upserted_count + result.modified_count
            print(f"[완료] CSAI 활동 적재 완료: 신규/변경 {upserted_count}개 (매칭 {result.matched_count}개)")
            return upserted_count
        except Exception as e:
            print(f"[오류] bulk_write 실행 중 예외 발생: {e}")
            return 0

    def delete_pending_jobs(self) -> int:
        """
        수집 중단 시 불완전하게 적재된 pending 상태의 도큐먼트를 삭제(롤백)합니다.
        """
        if self.collection is None:
            return 0
        try:
            result = self.collection.delete_many({"status": "pending"})
            return result.deleted_count
        except Exception as e:
            print(f"[오류] pending 도큐먼트 롤백 삭제 중 예외 발생: {e}")
            return 0

    def close(self):
        if self.client:
            self.client.close()
            print("[종료] MongoDB Atlas 연결 종료")
