import sys
import shutil
from pathlib import Path
import pytest
from driftbench.journal import Journal, RunKey
from driftbench.providers.base import ModelResponse
from driftbench.runner import RunConfig, execute_one
from driftbench.task import load_task
from driftbench.workspace import Condition

FIXTURES = Path(__file__).parent / "fixtures"
JAR = Path(__file__).resolve().parents[1] / "tools" / "specmatic.jar"
PY = str(Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python")

pytestmark = pytest.mark.skipif(
    not JAR.exists() or shutil.which("java") is None,
    reason="requires tools/specmatic.jar and java",
)

CORRECT_PAGINATION = '''\
### FILE: app.py
```python
import argparse
import sqlite3
import sys
from pathlib import Path

from flask import Flask, jsonify, request

from seed import seed

DB = Path(__file__).parent / "db" / "minisvc.db"
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


@app.get("/albums")
def list_albums():
    raw_limit = request.args.get("limit", "20")
    raw_offset = request.args.get("offset", "0")
    try:
        limit, offset = int(raw_limit), int(raw_offset)
    except ValueError:
        return _bad("limit and offset must be integers")
    if not 1 <= limit <= 100:
        return _bad("limit out of range")
    if offset < 0:
        return _bad("offset out of range")
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, title, artist, year FROM albums ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return jsonify([dict(r) for r in rows]), 200


@app.get("/albums/<album_id>")
def get_album(album_id):
    try:
        album_id_val = int(album_id)
    except ValueError:
        return jsonify({"error": "not_found", "message": "album_id must be an integer"}), 404
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, title, artist, year FROM albums WHERE id = ?", (album_id_val,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "not_found", "message": "no such album"}), 404
    return jsonify(dict(row)), 200


@app.post("/albums")
def create_album():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _bad("body must be an object")
    
    # Strict schema validation
    allowed = {"title", "artist", "year"}
    if set(body.keys()) - allowed:
        return _bad("additional properties not allowed")
        
    title, artist, year = body.get("title"), body.get("artist"), body.get("year")
    if not isinstance(title, str) or not title:
        return _bad("title required")
    if not isinstance(artist, str) or not artist:
        return _bad("artist required")
    if not isinstance(year, int) or isinstance(year, bool):
        return _bad("year must be an integer")
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
```
'''

DRIFTING_PAGINATION = CORRECT_PAGINATION.replace(
    'return jsonify([dict(r) for r in rows]), 200',
    'return jsonify([dict(r) | {"debug": True} for r in rows]), 200',
)


class ScriptedProvider:
    def __init__(self, text):
        self.model_id = "scripted:e2e"
        self._text = text

    def complete(self, system, user, seed):
        return ModelResponse(text=self._text, prompt_tokens=1, completion_tokens=1)


def _config(tmp_path):
    return RunConfig(
        tasks_dir=FIXTURES / "tasks", services_dir=FIXTURES, jar=JAR,
        journal_path=tmp_path / "runs.jsonl", work_dir=tmp_path / "work",
        model_specs=["scripted:e2e"], conditions=[Condition.A],
        boot_command=[PY, "app.py", "--port", "{port}"],
        test_command=[PY, "-m", "pytest", "tests", "-q"],
    )


@pytest.fixture
def task():
    return load_task(FIXTURES / "tasks" / "minisvc" / "minisvc-001", FIXTURES)


def test_correct_patch_scores_clean(task, tmp_path):
    record = execute_one(
        RunKey("minisvc-001", "A", "scripted:e2e", 0), task, _config(tmp_path),
        ScriptedProvider(CORRECT_PAGINATION),
    )
    assert record["patch_applied"] and record["tests_pass"]
    assert record["acceptance_pass"], record.get("error")
    assert record["contract_pass"], record.get("specmatic_failures")
    assert record["drift_classes"] == []


def test_silent_contract_breakage_is_caught(task, tmp_path):
    """The whole thesis in one test: tests pass, contract does not."""
    record = execute_one(
        RunKey("minisvc-001", "A", "scripted:e2e", 0), task, _config(tmp_path),
        ScriptedProvider(DRIFTING_PAGINATION),
    )
    assert record["tests_pass"] and record["acceptance_pass"]
    assert not record["contract_pass"]
    assert "D2" in record["drift_classes"]


def test_journal_round_trip(task, tmp_path):
    config = _config(tmp_path)
    record = execute_one(
        RunKey("minisvc-001", "A", "scripted:e2e", 0), task, config,
        ScriptedProvider(CORRECT_PAGINATION),
    )
    journal = Journal(config.journal_path)
    journal.append(record)
    assert RunKey("minisvc-001", "A", "scripted:e2e", 0) in journal.completed_keys()
