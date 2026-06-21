from app.routers.activities import serialize_mongo_activity


def test_serialize_mongo_activity_uses_structured_summary_fields():
    activity = {
        "_id": "abc123",
        "title": "[BK21] 2026 Competition",
        "status": "summarized",
        "summary": {
            "is_relevant": True,
            "activity_type": "공모전",
            "organizer": "전북대학교",
            "eligibility": ["전북대학교 소속 대학원생", "수료생 참여 가능"],
            "activity_period": "2026. 7. 1. ~ 2026. 8. 1.",
        },
    }

    result = serialize_mongo_activity(activity)

    assert result.category == "공모전"
    assert result.organizer == "전북대학교"
    assert result.period == "2026. 7. 1. ~ 2026. 8. 1."
    assert "{'is_relevant'" not in result.description
    assert "지원 대상: 전북대학교 소속 대학원생, 수료생 참여 가능" in result.description
