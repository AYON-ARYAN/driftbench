import sqlite3
from pathlib import Path

BOOKS = [
    (1, "The Hobbit", "J.R.R. Tolkien", 1937, "Fantasy", 10),
    (2, "Foundation", "Isaac Asimov", 1951, "Sci-Fi", 5),
    (3, "Dune", "Frank Herbert", 1965, "Sci-Fi", 0),
]

def seed(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT NOT NULL, "
        "author TEXT NOT NULL, year INTEGER NOT NULL, genre TEXT NOT NULL, stock INTEGER NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL, quantity INTEGER NOT NULL)"
    )
    conn.executemany("INSERT INTO books VALUES (?,?,?,?,?,?)", BOOKS)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed(Path(__file__).parent / "db" / "bookstore.db")
