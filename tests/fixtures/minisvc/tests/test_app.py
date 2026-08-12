import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from app import app, DB
from seed import seed


@pytest.fixture(autouse=True)
def _db():
    seed(DB)
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_list_albums(client):
    resp = client.get("/albums")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3


def test_get_album(client):
    assert client.get("/albums/1").get_json()["title"] == "Kind of Blue"


def test_get_missing_album_404(client):
    assert client.get("/albums/999").status_code == 404


def test_create_album(client):
    resp = client.post("/albums", json={"title": "Maiden Voyage", "artist": "Herbie Hancock", "year": 1965})
    assert resp.status_code == 201


def test_create_album_rejects_bad_year(client):
    assert client.post("/albums", json={"title": "x", "artist": "y", "year": "nineteen"}).status_code == 400
