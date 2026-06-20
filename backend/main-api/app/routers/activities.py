import re
import zlib

from fastapi import APIRouter
from pymongo import DESCENDING, MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from app.core.config import settings
from app.schemas import ActivityRead

router = APIRouter()

ACTIVITY_COLLECTION_CANDIDATES = [
    "activity_raw",
    "activities_raw",
    "activities",
    "activity",
    "contest_raw",
    "contest",
    "external_activity_raw",
    "external_activities",
]


def compact_text(value: object, max_length: int = 160) -> str:
    text_value = str(value or "")
    text_value = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", text_value)
    text_value = re.sub(r"https?://\S+", " ", text_value)
    text_value = re.sub(r"[#>*_`|\\]+", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    if len(text_value) <= max_length:
        return text_value
    return text_value[:max_length].rstrip() + "..."


def first_text(document: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = document.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def first_list(document: dict, *keys: str) -> list[str]:
    for key in keys:
        value = document.get(key)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in re.split(r"[,#/|]", value) if item.strip()]
    return []


def serialize_mongo_activity(activity: dict) -> ActivityRead:
    raw_id = str(activity.get("activity_id") or activity.get("contest_id") or activity.get("_id") or "")
    activity_id = int(raw_id) if raw_id.isdigit() else zlib.crc32(raw_id.encode("utf-8"))
    start_date = first_text(activity, "start_date", "startDate", "recruit_start")
    end_date = first_text(activity, "end_date", "endDate", "deadline", "deadline_raw", "recruit_end")
    period = first_text(activity, "period", "date_range")
    if not period:
        period = " - ".join([date for date in [start_date, end_date] if date]) or "일정 미정"

    description = compact_text(
        first_text(activity, "description", "summary", "detail_markdown", "content", "body")
    )

    return ActivityRead(
        id=activity_id,
        title=first_text(activity, "title", "name", "activity_name", "contest_name", default="제목 없음"),
        organizer=first_text(activity, "organizer", "host", "company_name", "organization", default="주최 미정"),
        period=period,
        category=first_text(activity, "category", "type", "field", default="대외활동"),
        tags=first_list(activity, "tags", "skills", "keywords", "fields")[:6],
        status=first_text(activity, "status", "recruit_status", default="모집 정보"),
        url=first_text(activity, "detail_url", "url", "link", "homepage_url"),
        description=description,
    )


def find_activity_collection(client: MongoClient):
    database = client["careerstep"]
    collection_names = set(database.list_collection_names())
    for name in ACTIVITY_COLLECTION_CANDIDATES:
        if name in collection_names:
            return database[name]

    for name in collection_names:
        lowered = name.lower()
        if "activity" in lowered or "contest" in lowered:
            return database[name]
    return None


def list_mongo_activities(limit: int = 60) -> list[ActivityRead]:
    if not settings.mongodb_uri:
        return []

    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
        collection = find_activity_collection(client)
        if collection is None:
            return []

        cursor = collection.find({}).sort(
            [("scraped_at", DESCENDING), ("inserted_at", DESCENDING), ("_id", DESCENDING)]
        ).limit(limit)
        return [serialize_mongo_activity(activity) for activity in cursor]
    except (PyMongoError, ServerSelectionTimeoutError):
        return []
    finally:
        client.close()


@router.get("", response_model=list[ActivityRead])
def list_activities() -> list[ActivityRead]:
    return list_mongo_activities()
