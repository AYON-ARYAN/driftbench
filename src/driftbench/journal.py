"""Append-only JSONL run journal. The sole source of resumability and of results."""
from __future__ import annotations

import json
import warnings
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

REQUIRED_FIELDS = ("task_id", "condition", "model_id", "seed", "timestamp")


class RunKey(NamedTuple):
    task_id: str
    condition: str
    model_id: str
    seed: int


class JournalError(Exception):
    """A record could not be journaled."""


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def records(self) -> Iterator[dict]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    warnings.warn(f"skipping malformed journal line {self.path}:{lineno}")

    def completed_keys(self) -> set[RunKey]:
        keys = set()
        for record in self.records():
            try:
                keys.add(RunKey(
                    record["task_id"], record["condition"],
                    record["model_id"], int(record["seed"]),
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return keys

    def append(self, record: dict) -> None:
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            raise JournalError(f"record missing required field(s): {', '.join(missing)}")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
