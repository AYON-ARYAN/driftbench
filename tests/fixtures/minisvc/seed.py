"""Deterministic seed. No network, no randomness."""
import sqlite3
from pathlib import Path

ALBUMS = [
    (1, "Kind of Blue", "Miles Davis", 1959),
    (2, "Blue Train", "John Coltrane", 1957),
    (3, "Head Hunters", "Herbie Hancock", 1973),
]


def seed(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE albums (id INTEGER PRIMARY KEY, title TEXT NOT NULL, "
        "artist TEXT NOT NULL, year INTEGER NOT NULL)"
    )
    conn.executemany("INSERT INTO albums VALUES (?,?,?,?)", ALBUMS)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed(Path(__file__).parent / "db" / "minisvc.db")
