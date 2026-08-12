"""Did the requested change actually happen? Run against the live service."""
import os
import httpx

BASE = f"http://127.0.0.1:{os.environ['DRIFTBENCH_PORT']}"


def test_limit_applies():
    resp = httpx.get(f"{BASE}/albums", params={"limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_offset_applies():
    resp = httpx.get(f"{BASE}/albums", params={"limit": 2, "offset": 2})
    assert resp.status_code == 200
    assert [a["id"] for a in resp.json()] == [3]


def test_defaults_return_all_three():
    assert len(httpx.get(f"{BASE}/albums").json()) == 3


def test_bad_limit_rejected():
    assert httpx.get(f"{BASE}/albums", params={"limit": "many"}).status_code == 400
    assert httpx.get(f"{BASE}/albums", params={"limit": 0}).status_code == 400
