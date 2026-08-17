import httpx
import os

def test_tasks_auth():
    port = os.environ.get("DRIFTBENCH_PORT", "5056")
    base_url = f"http://127.0.0.1:{port}"
    
    # 1. Reject without token
    r_unauth = httpx.post(f"{base_url}/tasks", json={"title": "Unauthorized task"})
    assert r_unauth.status_code == 401
    
    # 2. Accept with valid token
    headers = {"Authorization": "Bearer agent-secret-token"}
    r_auth = httpx.post(f"{base_url}/tasks", json={"title": "Authorized task"}, headers=headers)
    assert r_auth.status_code == 201
