import httpx
import os

def test_genre_filter():
    port = os.environ.get("DRIFTBENCH_PORT", "5057")
    base_url = f"http://127.0.0.1:{port}"
    r = httpx.get(f"{base_url}/tracks?genre=Jazz")
    assert r.status_code == 200
    tracks = r.json()
    assert len(tracks) == 1
    assert tracks[0]["title"] == "So What"
