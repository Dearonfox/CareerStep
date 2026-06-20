def test_signup_returns_token_pair(client):
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "new@example.com", "password": "password123", "name": "New User"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["role"] == "USER"


def test_signup_duplicate_email_returns_409(client):
    payload = {"email": "dup@example.com", "password": "password123", "name": "Dup"}
    client.post("/api/v1/auth/signup", json=payload)
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 409


def test_login_success(client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "login@example.com", "password": "password123", "name": "Login"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_wrong_password_returns_401(client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "wrong@example.com", "password": "password123", "name": "Wrong"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "incorrect"},
    )
    assert response.status_code == 401


def test_refresh_issues_new_token_pair(client, auth_headers):
    _, tokens = auth_headers
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


def test_refresh_rotates_old_token_and_rejects_reuse(client, auth_headers):
    _, tokens = auth_headers
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200

    # 회전된(폐기된) 기존 토큰으로 다시 시도하면 거부되어야 함
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401


def test_refresh_with_unknown_token_returns_401(client):
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "no-such-token"})
    assert response.status_code == 401


def test_logout_deletes_refresh_token(client, auth_headers):
    _, tokens = auth_headers
    response = client.post(
        "/api/v1/auth/logout",
        params={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200

    # 로그아웃 후 같은 토큰으로 갱신 시도하면 거부되어야 함
    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 401


def test_change_password_updates_login_password(client, auth_headers):
    headers, _ = auth_headers

    response = client.patch(
        "/api/v1/auth/password",
        headers=headers,
        json={"current_password": "password123", "new_password": "newpassword123"},
    )
    assert response.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "tester@example.com", "password": "password123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "tester@example.com", "password": "newpassword123"},
    )
    assert new_login.status_code == 200


def test_change_password_rejects_wrong_current_password(client, auth_headers):
    headers, _ = auth_headers

    response = client.patch(
        "/api/v1/auth/password",
        headers=headers,
        json={"current_password": "wrongpassword", "new_password": "newpassword123"},
    )
    assert response.status_code == 400
