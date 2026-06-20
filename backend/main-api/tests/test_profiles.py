def test_get_profile_without_data_returns_null(client, auth_headers):
    headers, _ = auth_headers
    response = client.get("/api/v1/profiles/me", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_get_profile_requires_auth(client):
    response = client.get("/api/v1/profiles/me")
    assert response.status_code in (401, 403)


def test_upsert_then_get_profile_roundtrip(client, auth_headers):
    headers, _ = auth_headers
    payload = {
        "desired_role": "백엔드 개발자",
        "skills": ["Python", "FastAPI"],
        "certificates": ["정보처리기사"],
        "projects": ["CareerStep"],
    }

    put_response = client.put("/api/v1/profiles/me", json=payload, headers=headers)
    assert put_response.status_code == 200
    body = put_response.json()
    assert body["desired_role"] == "백엔드 개발자"
    assert body["skills"] == ["Python", "FastAPI"]

    get_response = client.get("/api/v1/profiles/me", headers=headers)
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["desired_role"] == "백엔드 개발자"
    assert fetched["certificates"] == ["정보처리기사"]


def test_upsert_profile_twice_updates_same_row(client, auth_headers):
    headers, _ = auth_headers
    client.put(
        "/api/v1/profiles/me",
        json={"desired_role": "A", "skills": [], "certificates": [], "projects": []},
        headers=headers,
    )
    second = client.put(
        "/api/v1/profiles/me",
        json={"desired_role": "B", "skills": ["Go"], "certificates": [], "projects": []},
        headers=headers,
    )
    assert second.json()["desired_role"] == "B"
    assert second.json()["skills"] == ["Go"]
