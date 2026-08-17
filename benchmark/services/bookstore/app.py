import argparse
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, request
from seed import seed

DB = Path(__file__).parent / "db" / "bookstore.db"
app = Flask(__name__)

def _conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def _bad(msg):
    return jsonify({"error": "bad_request", "message": msg}), 400

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

@app.get("/books")
def list_books():
    author = request.args.get("author")
    query = "SELECT id, title, author, year, genre, stock FROM books"
    params = []
    if author:
        query += " WHERE author = ?"
        params.append(author)
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows]), 200

@app.get("/books/<int:book_id>")
def get_book(book_id):
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, title, author, year, genre, stock FROM books WHERE id = ?", (book_id,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "not_found", "message": "no such book"}), 404
    return jsonify(dict(row)), 200

@app.post("/books")
def create_book():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _bad("body must be an object")
    allowed = {"title", "author", "year", "genre", "stock"}
    if set(body.keys()) - allowed:
        return _bad("additional properties not allowed")
    title, author, year = body.get("title"), body.get("author"), body.get("year")
    genre, stock = body.get("genre"), body.get("stock")
    if not isinstance(title, str) or not title: return _bad("title required")
    if not isinstance(author, str) or not author: return _bad("author required")
    if not isinstance(year, int) or isinstance(year, bool): return _bad("year must be an integer")
    if not isinstance(genre, str) or not genre: return _bad("genre required")
    if not isinstance(stock, int) or isinstance(stock, bool) or stock < 0: return _bad("stock must be non-negative")
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, genre, stock) VALUES (?,?,?,?,?)",
            (title, author, year, genre, stock)
        )
        new_id = cur.lastrowid
    return jsonify({"id": new_id, "title": title, "author": author, "year": year, "genre": genre, "stock": stock}), 201

@app.post("/orders")
def create_order():
    body = request.get_json(silent=True)
    if not isinstance(body, dict): return _bad("body must be an object")
    allowed = {"book_id", "quantity"}
    if set(body.keys()) - allowed: return _bad("additional properties not allowed")
    book_id, qty = body.get("book_id"), body.get("quantity")
    if not isinstance(book_id, int): return _bad("book_id must be integer")
    if not isinstance(qty, int) or qty <= 0: return _bad("quantity must be positive")
    with _conn() as conn:
        row = conn.execute("SELECT stock FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None: return jsonify({"error": "not_found", "message": "no such book"}), 404
        if row["stock"] < qty: return _bad("insufficient stock")
        conn.execute("UPDATE books SET stock = stock - ? WHERE id = ?", (qty, book_id))
        cur = conn.execute("INSERT INTO orders (book_id, quantity) VALUES (?,?)", (book_id, qty))
        new_id = cur.lastrowid
    return jsonify({"id": new_id, "book_id": book_id, "quantity": qty}), 201

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5055)
    args = parser.parse_args()
    seed(DB)
    app.run(host="127.0.0.1", port=args.port)
