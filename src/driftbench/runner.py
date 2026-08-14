"""Expand the run matrix, skip what is journaled, execute the rest."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from driftbench.journal import Journal, RunKey
from driftbench.providers import ProviderError, get_provider
from driftbench.scaffold import run_agent
from driftbench.scorer import score
from driftbench.task import Task, load_all_tasks
from driftbench.workspace import Condition, prepare_workspace


@dataclass(frozen=True)
class RunConfig:
    tasks_dir: Path
    services_dir: Path
    jar: Path
    journal_path: Path
    work_dir: Path
    model_specs: list[str]
    conditions: list[Condition]
    boot_command: list[str]
    test_command: list[str]
    seeds_by_model: dict[str, int] = field(default_factory=dict)
    default_seeds: int = 1

    def seeds_for(self, model_spec: str) -> int:
        return self.seeds_by_model.get(model_spec, self.default_seeds)


def expand_matrix(tasks: list[Task], config: RunConfig) -> list[RunKey]:
    matrix: list[RunKey] = []
    for task in tasks:
        for model_spec in config.model_specs:
            for condition in config.conditions:
                for seed in range(config.seeds_for(model_spec)):
                    matrix.append(RunKey(task.task_id, condition.value, model_spec, seed))
    return matrix


def pending(matrix: list[RunKey], journal: Journal) -> list[RunKey]:
    done = journal.completed_keys()
    return [key for key in matrix if key not in done]


def execute_one(key: RunKey, task: Task, config: RunConfig, provider) -> dict:
    condition = Condition(key.condition)
    slug = f"{key.task_id}_{key.condition}_{key.model_id.replace(':', '-')}_{key.seed}"
    workspace = prepare_workspace(task, condition, config.work_dir / slug)

    record: dict = {
        "task_id": key.task_id,
        "condition": key.condition,
        "model_id": key.model_id,
        "seed": key.seed,
        "timestamp": datetime.now(UTC).isoformat(),
        "task_type": task.task_type,
        "service": task.service,
    }

    scaffold = run_agent(
        task=task, workspace=workspace, provider=provider, condition=condition,
        seed=key.seed, test_command=config.test_command,
    )
    record.update({
        "patch_applied": scaffold.patch_applied,
        "iterations": scaffold.iterations,
        "changed_files": scaffold.changed_files,
        "tests_pass": bool(scaffold.test_result and scaffold.test_result.passed),
        "prompt_tokens": scaffold.prompt_tokens,
        "completion_tokens": scaffold.completion_tokens,
        "error": scaffold.error,
    })

    if not scaffold.patch_applied:
        record.update({
            "acceptance_pass": False, "contract_pass": False,
            "drift_classes": [], "laundering": False,
            "spec_modified": False, "spec_weakenings": [],
        })
        return record

    result = score(
        task=task, workspace=workspace, condition=condition, jar=config.jar,
        boot_command=config.boot_command, report_dir=config.work_dir / slug / "reports",
    )
    record.update({
        "acceptance_pass": result.acceptance_pass,
        "contract_pass": result.contract_pass,
        "drift_classes": result.drift_classes,
        "laundering": result.laundering,
        "spec_modified": result.spec_modified,
        "spec_weakenings": result.spec_weakenings,
        "specmatic_total": result.specmatic.total,
        "specmatic_failed": result.specmatic.failed,
        "specmatic_failures": result.specmatic.failures,
    })
    if result.error:
        record["error"] = result.error
    return record


def run(config: RunConfig) -> int:
    tasks = load_all_tasks(config.tasks_dir, config.services_dir)
    by_id = {task.task_id: task for task in tasks}
    journal = Journal(config.journal_path)

    todo = pending(expand_matrix(tasks, config), journal)
    providers: dict[str, object] = {}
    executed = 0

    for key in todo:
        if key.model_id not in providers:
            try:
                providers[key.model_id] = get_provider(key.model_id)
            except ProviderError as exc:
                journal.append({
                    "task_id": key.task_id, "condition": key.condition,
                    "model_id": key.model_id, "seed": key.seed,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "patch_applied": False, "tests_pass": False,
                    "acceptance_pass": False, "contract_pass": False,
                    "drift_classes": [], "laundering": False, "error": str(exc),
                })
                continue

        journal.append(execute_one(key, by_id[key.task_id], config, providers[key.model_id]))
        executed += 1

    return executed
