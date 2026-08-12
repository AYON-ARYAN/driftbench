import argparse
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request

from seed import seed

DB = Path(__file__).parent / "db" / "minisvc.db"
app = Flask(__name__)


def _conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@app.get("/albums")
def list_albums():
    with _conn() as conn:
        rows = conn.execute("SELECT id, title, artist, year FROM albums ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows]), 200


@app.get("/albums/<int:album_id>")
def get_album(album_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, title, artist, year FROM albums WHERE id = ?", (album_id,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "not_found", "message": "no such album"}), 404
    return jsonify(dict(row)), 200


@app.post("/albums")
def create_album():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "bad_request", "message": "body must be an object"}), 400
    title, artist, year = body.get("title"), body.get("artist"), body.get("year")
    if not isinstance(title, str) or not title:
        return jsonify({"error": "bad_request", "message": "title required"}), 400
    if not isinstance(artist, str) or not artist:
        return jsonify({"error": "bad_request", "message": "artist required"}), 400
    if not isinstance(year, int) or isinstance(year, bool):
        return jsonify({"error": "bad_request", "message": "year must be an integer"}), 400
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO albums (title, artist, year) VALUES (?,?,?)", (title, artist, year)
        )
        new_id = cur.lastrowid
    return jsonify({"id": new_id, "title": title, "artist": artist, "year": year}), 201


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5055)
    args = parser.parse_args()
    seed(DB)
    app.run(host="127.0.0.1", port=args.port)
