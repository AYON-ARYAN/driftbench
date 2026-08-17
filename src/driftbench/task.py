"""Benchmark task: a change request plus the hidden oracle that scores it."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

TASK_TYPES = frozenset({
    "add_endpoint",
    "add_filter_param",
    "add_pagination",
    "add_input_validation",
    "fix_bug",
    "add_auth",
    "change_field_semantics",
    "refactor_no_interface_change",
    "extend_response_field",
})


@dataclass(frozen=True)
class Task:
    task_id: str
    service: str
    task_type: str
    difficulty: str
    root: Path
    services_dir: Path
    boot_command: list[str] | None = None
    test_command: list[str] | None = None

    @property
    def prompt(self) -> str:
        return (self.root / "task.md").read_text(encoding="utf-8")

    @property
    def acceptance_test(self) -> Path:
        return self.root / "acceptance_test.py"

    @property
    def oracle_spec(self) -> Path:
        return self.root / "oracle" / "spec.yaml"

    @property
    def oracle_config(self) -> Path:
        return self.root / "oracle" / "specmatic.yaml"

    @property
    def oracle_examples(self) -> Path:
        return self.root / "oracle" / "examples"

    @property
    def service_dir(self) -> Path:
        return self.services_dir / self.service


def load_task(root: Path, services_dir: Path) -> Task:
    root = Path(root)
    meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))

    task_type = meta["task_type"]
    if task_type not in TASK_TYPES:
        raise ValueError(f"unknown task_type {task_type!r} in {root}")

    task = Task(
        task_id=meta["task_id"],
        service=meta["service"],
        task_type=task_type,
        difficulty=meta["difficulty"],
        root=root,
        services_dir=Path(services_dir),
        boot_command=meta.get("boot_command"),
        test_command=meta.get("test_command"),
    )

    for required in (task.oracle_spec, task.oracle_config, task.acceptance_test):
        if not required.exists():
            raise FileNotFoundError(f"{required.name} missing for task {task.task_id}")
    if not task.service_dir.is_dir():
        raise FileNotFoundError(f"service dir missing for task {task.task_id}")

    return task


def load_all_tasks(tasks_dir: Path, services_dir: Path) -> list[Task]:
    roots = [p.parent for p in Path(tasks_dir).glob("*/*/metadata.json")]
    return sorted(
        (load_task(r, services_dir) for r in roots),
        key=lambda t: t.task_id,
    )
