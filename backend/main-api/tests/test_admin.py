def test_non_admin_cannot_list_users(client, auth_headers):
    headers, _ = auth_headers
    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 403


def test_bootstrap_grants_admin_role_once(client, auth_headers):
    headers, _ = auth_headers
    response = client.post("/api/v1/admin/bootstrap", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_bootstrap_fails_if_admin_already_exists(client, auth_headers):
    headers, _ = auth_headers
    client.post("/api/v1/admin/bootstrap", headers=headers)

    other_signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "second@example.com", "password": "password123", "name": "Second"},
    )
    other_headers = {"Authorization": f"Bearer {other_signup.json()['access_token']}"}

    response = client.post("/api/v1/admin/bootstrap", headers=other_headers)
    assert response.status_code == 409


def test_admin_can_list_users_after_bootstrap(client, auth_headers):
    headers, _ = auth_headers
    client.post("/api/v1/admin/bootstrap", headers=headers)
    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_admin_cannot_delete_own_account(client, auth_headers):
    headers, _ = auth_headers
    client.post("/api/v1/admin/bootstrap", headers=headers)

    me = client.get("/api/v1/admin/users", headers=headers).json()[0]
    response = client.delete(f"/api/v1/admin/users/{me['id']}", headers=headers)
    assert response.status_code == 400
