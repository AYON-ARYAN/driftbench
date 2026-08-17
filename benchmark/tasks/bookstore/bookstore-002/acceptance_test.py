import httpx
import os

def test_pagination():
    port = os.environ.get("DRIFTBENCH_PORT", "5055")
    base_url = f"http://127.0.0.1:{port}"
    r = httpx.get(f"{base_url}/books?limit=1&offset=1")
    assert r.status_code == 200
    books = r.json()
    assert len(books) == 1
    assert books[0]["title"] == "Foundation"
