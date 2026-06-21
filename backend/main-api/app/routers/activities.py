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

NESTED_SUMMARY_KEYS = ("summary", "summarized", "ai_summary", "extracted", "parsed")


def compact_text(value: object, max_length: int = 160) -> str:
    text_value = str(value or "")
    text_value = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", text_value)
    text_value = re.sub(r"https?://\S+", " ", text_value)
    text_value = re.sub(r"[#>*_`|\\]+", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    if len(text_value) <= max_length:
        return text_value
    return text_value[:max_length].rstrip() + "..."


def stringify_summary_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def text_from_structured_summary(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return stringify_summary_value(value)
    if not isinstance(value, dict):
        return str(value or "").strip()

    for key in ("description", "summary", "summary_text", "overview", "content", "body", "details"):
        nested_value = value.get(key)
        if nested_value:
            return text_from_structured_summary(nested_value)

    readable_parts = []
    field_labels = [
        ("activity_period", "활동 기간"),
        ("recruitment_period", "모집 기간"),
        ("eligibility", "지원 대상"),
        ("benefits", "혜택"),
        ("selection_process", "선발 절차"),
        ("location", "장소"),
    ]
    for key, label in field_labels:
        nested_value = value.get(key)
        text_value = stringify_summary_value(nested_value) if nested_value else ""
        if text_value:
            readable_parts.append(f"{label}: {text_value}")

    return " · ".join(readable_parts)


def nested_text(document: dict, key: str) -> str:
    lookup_keys = [key]
    if key == "category":
        lookup_keys.append("activity_type")

    for lookup_key in lookup_keys:
        value = document.get(lookup_key)
        if value is not None and text_from_structured_summary(value):
            return text_from_structured_summary(value)

    for summary_key in NESTED_SUMMARY_KEYS:
        summary = document.get(summary_key)
        if isinstance(summary, dict):
            for lookup_key in lookup_keys:
                value = summary.get(lookup_key)
                if value is not None and text_from_structured_summary(value):
                    return text_from_structured_summary(value)
    return ""


def first_text(document: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = nested_text(document, key)
        if value:
            return value
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
    period = first_text(activity, "period", "date_range", "activity_period", "recruitment_period")
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
