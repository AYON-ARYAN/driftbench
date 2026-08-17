import argparse
import sqlite3
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from seed import seed

DB = Path(__file__).parent / "db" / "taskmanager.db"
app = FastAPI()

def _conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

class TaskIn(BaseModel):
    title: str = Field(..., min_length=1)
    description: str | None = None
    status: str = "pending"
    assignee_id: int | None = None
    due_date: str | None = None

    class Config:
        extra = "forbid"

class UserIn(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)

    class Config:
        extra = "forbid"

@app.on_event("startup")
def startup():
    seed(DB)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/tasks")
def list_tasks(status: str | None = None, assignee_id: int | None = None):
    query = "SELECT id, title, description, status, assignee_id, due_date FROM tasks"
    params = []
    conds = []
    if status:
        conds.append("status = ?")
        params.append(status)
    if assignee_id is not None:
        conds.append("assignee_id = ?")
        params.append(assignee_id)
    if conds:
        query += " WHERE " + " AND ".join(conds)
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, title, description, status, assignee_id, due_date FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="no such task")
    return dict(row)

@app.post("/tasks", status_code=201)
def create_task(task: TaskIn):
    with _conn() as conn:
        if task.assignee_id is not None:
            user = conn.execute("SELECT id FROM users WHERE id = ?", (task.assignee_id,)).fetchone()
            if user is None:
                raise HTTPException(status_code=400, detail="assignee not found")
        cur = conn.execute(
            "INSERT INTO tasks (title, description, status, assignee_id, due_date) VALUES (?,?,?,?,?)",
            (task.title, task.description, task.status, task.assignee_id, task.due_date)
        )
        new_id = cur.lastrowid
    return {"id": new_id, **task.dict()}

@app.get("/users")
def list_users():
    with _conn() as conn:
        rows = conn.execute("SELECT id, name, email FROM users").fetchall()
    return [dict(r) for r in rows]

@app.post("/users", status_code=201)
def create_user(user: UserIn):
    with _conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (name, email) VALUES (?,?)", (user.name, user.email)
            )
            new_id = cur.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="email already registered")
    return {"id": new_id, "name": user.name, "email": user.email}

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5056)
    args = parser.parse_args()
    seed(DB)
    uvicorn.run(app, host="127.0.0.1", port=args.port)
