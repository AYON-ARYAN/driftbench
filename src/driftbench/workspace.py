"""Snapshot a service into an isolated workspace with condition-appropriate spec visibility."""
from __future__ import annotations

import shutil
from enum import StrEnum
from pathlib import Path

from driftbench.task import Task

AGENT_SPEC_FILENAME = "openapi.yaml"

_EXCLUDE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".pytest_cache", "db", "*.db",
    "node_modules", ".git", "reports", "*.jsonl",
)


class Condition(StrEnum):
    A = "A"  # spec hidden
    B = "B"  # spec visible, read-only
    C = "C"  # spec visible and editable


def agent_spec_path(workspace: Path) -> Path:
    return Path(workspace) / AGENT_SPEC_FILENAME


def prepare_workspace(task: Task, condition: Condition, dest: Path) -> Path:
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(task.service_dir, dest, ignore=_EXCLUDE)

    if condition in (Condition.B, Condition.C):
        shutil.copyfile(task.oracle_spec, agent_spec_path(dest))

    return dest
