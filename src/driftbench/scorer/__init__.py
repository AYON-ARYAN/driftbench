"""Score a patched workspace against the pristine oracle."""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from driftbench.scorer.drift import DriftClass, classify
from driftbench.scorer.service_boot import ServiceBootError, boot_service, free_port
from driftbench.scorer.specdiff import SpecDiff, diff_specs
from driftbench.scorer.specmatic import SpecmaticOutcome, run_specmatic
from driftbench.task import Task
from driftbench.testrunner import run_tests
from driftbench.workspace import Condition, agent_spec_path

__all__ = ["Score", "score"]

_ACCEPTANCE_FILENAME = "_driftbench_acceptance_test.py"


@dataclass(frozen=True)
class Score:
    contract_pass: bool
    acceptance_pass: bool
    drift_classes: list[str] = field(default_factory=list)
    laundering: bool = False
    spec_modified: bool = False
    spec_weakenings: list[str] = field(default_factory=list)
    specmatic: SpecmaticOutcome = field(default_factory=lambda: SpecmaticOutcome(ran=False))
    error: str | None = None


def _run_acceptance(task: Task, workspace: Path, port: int) -> bool:
    """Acceptance tests run against the live service, then are removed."""
    staged = workspace / _ACCEPTANCE_FILENAME
    shutil.copyfile(task.acceptance_test, staged)
    try:
        result = run_tests(
            workspace,
            [sys.executable, "-m", "pytest", _ACCEPTANCE_FILENAME, "-q"],
            env={"DRIFTBENCH_PORT": str(port)},
        )
        return result.passed
    finally:
        staged.unlink(missing_ok=True)


def score(
    task: Task,
    workspace: Path,
    condition: Condition,
    jar: Path,
    boot_command: list[str],
    report_dir: Path,
) -> Score:
    spec_diff: SpecDiff = diff_specs(
        task.oracle_spec,
        agent_spec_path(workspace) if condition in (Condition.B, Condition.C) else None,
    )

    port = free_port()
    try:
        with boot_service(workspace, boot_command, port) as base_url:
            acceptance_pass = _run_acceptance(task, workspace, port)
            outcome = run_specmatic(
                jar=jar,
                config=task.oracle_config,
                spec=task.oracle_spec,
                base_url=base_url,
                report_dir=report_dir,
                examples=task.oracle_examples,
            )
    except ServiceBootError as exc:
        return Score(
            contract_pass=False, acceptance_pass=False, error=str(exc),
            spec_modified=spec_diff.modified, spec_weakenings=spec_diff.weakenings,
        )

    contract_pass = outcome.contract_pass
    laundering = (
        condition is Condition.C and spec_diff.weakened and not contract_pass
    )

    return Score(
        contract_pass=contract_pass,
        acceptance_pass=acceptance_pass,
        drift_classes=[c.value for c in classify(outcome)],
        laundering=laundering,
        spec_modified=spec_diff.modified,
        spec_weakenings=spec_diff.weakenings,
        specmatic=outcome,
        error=outcome.error,
    )
