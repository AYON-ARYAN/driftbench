import httpx
import os

def test_get_user():
    port = os.environ.get("DRIFTBENCH_PORT", "5056")
    base_url = f"http://127.0.0.1:{port}"
    r = httpx.get(f"{base_url}/users/1")
    assert r.status_code == 200
    user = r.json()
    assert user["name"] == "Alice"
    assert user["email"] == "alice@example.com"
