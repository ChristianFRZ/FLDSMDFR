async def request_role(client, user):
    return await client.post("/api/composer-requests", json={"message": "hago música"}, headers=user.headers)


async def test_request_starts_pending(client, listener):
    r = await request_role(client, listener)
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


async def test_one_pending_request(client, listener):
    await request_role(client, listener)
    r = await request_role(client, listener)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "request_pending"


async def test_can_request_again_after_rejection(client, admin, listener):
    rid = (await request_role(client, listener)).json()["id"]
    await client.post(f"/api/admin/composer-requests/{rid}/reject", json={"reason": "aún no"}, headers=admin.headers)
    assert (await request_role(client, listener)).status_code == 201


async def test_composer_cannot_request(client, composer):
    r = await request_role(client, composer)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "already_composer"


async def test_role_changes_only_on_approval(client, admin, listener):
    rid = (await request_role(client, listener)).json()["id"]
    assert (await client.get("/api/users/me", headers=listener.headers)).json()["role"] == "listener"
    r = await client.post(f"/api/admin/composer-requests/{rid}/approve", json={}, headers=admin.headers)
    assert r.status_code == 200
    assert (await client.get("/api/users/me", headers=listener.headers)).json()["role"] == "composer"
    row = (await client.get("/api/admin/audit?action=composer_approved", headers=admin.headers)).json()["items"][0]
    assert row["target_id"] == listener.id


async def test_reject_requires_reason(client, admin, listener):
    rid = (await request_role(client, listener)).json()["id"]
    r = await client.post(f"/api/admin/composer-requests/{rid}/reject", json={}, headers=admin.headers)
    assert r.status_code == 422


async def test_reject_keeps_role_and_audits_reason(client, admin, listener):
    rid = (await request_role(client, listener)).json()["id"]
    await client.post(f"/api/admin/composer-requests/{rid}/reject", json={"reason": "aún no"}, headers=admin.headers)
    assert (await client.get("/api/users/me", headers=listener.headers)).json()["role"] == "listener"
    row = (await client.get("/api/admin/audit?action=composer_rejected", headers=admin.headers)).json()["items"][0]
    assert row["detail"]["reason"] == "aún no"


async def test_review_twice_409(client, admin, listener):
    rid = (await request_role(client, listener)).json()["id"]
    await client.post(f"/api/admin/composer-requests/{rid}/approve", json={}, headers=admin.headers)
    r = await client.post(f"/api/admin/composer-requests/{rid}/reject", json={"reason": "x"}, headers=admin.headers)
    assert r.status_code == 409


async def test_my_requests(client, listener):
    await request_role(client, listener)
    r = await client.get("/api/composer-requests/mine", headers=listener.headers)
    assert [x["status"] for x in r.json()] == ["pending"]


async def test_admin_list_says_who_asked(client, listener, admin):
    await request_role(client, listener)
    r = await client.get("/api/admin/composer-requests?status=pending", headers=admin.headers)
    item = r.json()["items"][0]
    assert item["user_email"] == listener.email
    assert item["user_name"] == listener.email.split("@")[0]
