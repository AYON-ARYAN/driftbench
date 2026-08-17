import httpx
import os

def test_refactor_behavior():
    port = os.environ.get("DRIFTBENCH_PORT", "5056")
    base_url = f"http://127.0.0.1:{port}"
    r = httpx.get(f"{base_url}/healthz")
    assert r.status_code == 200
    r_tasks = httpx.get(f"{base_url}/tasks")
    assert r_tasks.status_code == 200
    assert len(r_tasks.json()) == 2
