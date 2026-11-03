from tests.helpers import signup


async def test_internal_users_count_without_session(client):
    assert (await client.get("/internal/users/count")).json() == {"count": 0}
    await signup(client)
    client.cookies.clear()
    assert (await client.get("/internal/users/count")).json() == {"count": 1}
