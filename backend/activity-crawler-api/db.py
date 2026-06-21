from datetime import datetime

from pymongo import MongoClient, ReplaceOne
from pymongo.server_api import ServerApi

from config import MONGODB_URI


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
            self.collection = self.db["activities"]

            self.client.admin.command('ping')
            print("[연결] MongoDB Atlas 클라우드 연결에 성공했습니다!")
        except Exception as e:
            print(f"[오류] MongoDB Atlas 연결 실패: {e}")

    def upsert_activities(self, activities: list[dict]) -> int:
        """
        고유 ID(board_code + article_id)를 MongoDB 도큐먼트 기본 식별자(_id)로 지정하여
        중복 없이 Upsert(없으면 삽입, 있으면 대체) 처리
        """
        if self.collection is None:
            print("[오류] 데이터베이스가 연결되어 있지 않아 적재를 취소합니다.")
            return 0

        if not activities:
            print("[정보] 적재할 게시글 데이터가 없습니다.")
            return 0

        operations = []
        for activity in activities:
            doc = activity.copy()
            doc["_id"] = f"{doc['board_code']}_{doc['article_id']}"
            doc["source"] = "jbnu_csai"
            doc["status"] = "pending"
            doc["inserted_at"] = datetime.now().isoformat()

            operations.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))

        try:
            result = self.collection.bulk_write(operations, ordered=False)
            upserted_count = result.upserted_count + result.modified_count
            print(f"[완료] MongoDB Atlas 적재 완료: 신규/변경 {upserted_count}개 (매칭 {result.matched_count}개)")
            return upserted_count
        except Exception as e:
            print(f"[오류] bulk_write 실행 중 예외 발생: {e}")
            return 0

    def update_activity_detail(self, board_code: str, article_id: str, detail_data: dict) -> bool:
        """
        특정 게시글 도큐먼트에 마크다운 본문, 이미지/첨부파일 정보를 추가/업데이트하고
        status 값을 detailed (또는 에러 시 failed)로 갱신
        """
        if self.collection is None:
            print("[오류] 데이터베이스 연결이 없습니다.")
            return False

        update_fields = {
            "detail_markdown": detail_data.get("detail_markdown", ""),
            "is_image_job": detail_data.get("is_image_job", False),
            "image_urls": detail_data.get("image_urls", []),
            "attachments": detail_data.get("attachments", []),
            "category": detail_data.get("category", "기타"),
            "detailed_at": datetime.now().isoformat(),
        }

        if detail_data.get("error_message"):
            update_fields["status"] = "failed"
            update_fields["error_message"] = detail_data["error_message"]
        else:
            update_fields["status"] = "detailed"
            update_fields["error_message"] = None

        try:
            result = self.collection.update_one(
                {"_id": f"{board_code}_{article_id}"},
                {"$set": update_fields},
            )
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            print(f"[오류] MongoDB 상세 정보 업데이트 실패 (ID: {board_code}_{article_id}): {e}")
            return False

    def close(self):
        if self.client:
            self.client.close()
            print("[종료] MongoDB Atlas 연결 종료")
