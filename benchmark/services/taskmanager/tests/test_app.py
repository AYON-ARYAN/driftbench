import pytest
from fastapi.testclient import TestClient
from app import app, DB
from seed import seed

@pytest.fixture
def client():
    seed(DB)
    return TestClient(app)

def test_healthz(client):
    assert client.get("/healthz").status_code == 200

def test_list_tasks(client):
    r = client.get("/tasks")
    assert r.status_code == 200
    assert len(r.json()) == 2

def test_filter_tasks(client):
    r = client.get("/tasks?status=completed")
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_get_task(client):
    r = client.get("/tasks/1")
    assert r.status_code == 200
    assert r.json()["title"] == "Implement Auth"

def test_get_missing_task(client):
    assert client.get("/tasks/999").status_code == 404

def test_create_task(client):
    r = client.post("/tasks", json={
        "title": "New Task", "description": "Details", "status": "pending", "assignee_id": 1
    })
    assert r.status_code == 201
    assert r.json()["id"] == 3

def test_create_task_invalid_assignee(client):
    r = client.post("/tasks", json={
        "title": "New Task", "assignee_id": 999
    })
    assert r.status_code == 400

def test_list_users(client):
    r = client.get("/users")
    assert r.status_code == 200
    assert len(r.json()) == 2
