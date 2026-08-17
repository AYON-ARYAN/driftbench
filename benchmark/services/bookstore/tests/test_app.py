import pytest
from app import app, DB
from seed import seed

@pytest.fixture
def client():
    seed(DB)
    with app.test_client() as c:
        yield c

def test_healthz(client):
    assert client.get("/healthz").status_code == 200

def test_list_books(client):
    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.get_json()) == 3

def test_filter_books(client):
    r = client.get("/books?author=Frank Herbert")
    assert r.status_code == 200
    assert len(r.get_json()) == 1

def test_get_book(client):
    r = client.get("/books/1")
    assert r.status_code == 200
    assert r.get_json()["title"] == "The Hobbit"

def test_get_missing_book(client):
    assert client.get("/books/999").status_code == 404

def test_create_book(client):
    r = client.post("/books", json={
        "title": "Test Book", "author": "Tester", "year": 2026, "genre": "Tech", "stock": 5
    })
    assert r.status_code == 201
    assert r.get_json()["id"] == 4

def test_create_order_success(client):
    r = client.post("/orders", json={"book_id": 1, "quantity": 2})
    assert r.status_code == 201
    assert r.get_json()["quantity"] == 2

def test_create_order_insufficient_stock(client):
    r = client.post("/orders", json={"book_id": 3, "quantity": 1})
    assert r.status_code == 400
