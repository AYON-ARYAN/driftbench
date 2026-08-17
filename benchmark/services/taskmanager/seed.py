import sqlite3
from pathlib import Path

USERS = [
    (1, "Alice", "alice@example.com"),
    (2, "Bob", "bob@example.com"),
]

TASKS = [
    (1, "Implement Auth", "Secure endpoints", "pending", 1, "2026-08-31"),
    (2, "Refactor DB", "Optimize pool", "completed", 2, "2026-08-15"),
]

def seed(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE)"
    )
    conn.execute(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, "
        "description TEXT, status TEXT NOT NULL, assignee_id INTEGER, due_date TEXT, "
        "FOREIGN KEY(assignee_id) REFERENCES users(id))"
    )
    conn.executemany("INSERT INTO users VALUES (?,?,?)", USERS)
    conn.executemany("INSERT INTO tasks VALUES (?,?,?,?,?,?)", TASKS)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed(Path(__file__).parent / "db" / "taskmanager.db")
