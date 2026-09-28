import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer

from backend.server import create_app


@pytest_asyncio.fixture
async def client(tmp_path):
    app = create_app()
    app["db"].close()
    from backend import store
    app["db"] = store.connect(tmp_path / "t.db")
    async with TestClient(TestServer(app)) as c:
        yield c


pytestmark = pytest.mark.asyncio


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status == 200
    assert (await r.json())["ok"] is True


async def test_account_crud_via_api(client):
    r = await client.post("/api/accounts", json={
        "name": "acc1", "page_id": "42", "proxy": "http://h:9",
        "cookie": "c_user=1; xs=2",
    })
    assert r.status == 201
    data = await r.json()
    assert data["name"] == "acc1"

    r = await client.get("/api/accounts")
    assert len(await r.json()) == 1

    r = await client.put("/api/accounts/acc1", json={"page_id": "55"})
    assert (await r.json())["page_id"] == "55"

    r = await client.delete("/api/accounts/acc1")
    assert (await r.json())["ok"] is True


async def test_run_start_missing_account(client):
    r = await client.post("/api/runs/ghost/start", json={"mode": "uid"})
    assert r.status == 404


async def test_run_bad_mode(client):
    await client.post("/api/accounts", json={"name": "a", "page_id": "1"})
    r = await client.post("/api/runs/a/start", json={"mode": "bogus"})
    assert r.status == 400


async def test_settings_roundtrip(client):
    r = await client.put("/api/settings", json={"delay_min": 3})
    assert r.status == 200
    assert (await r.json())["delay_min"] == "3"
