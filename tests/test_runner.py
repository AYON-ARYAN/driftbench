from pathlib import Path
import pytest
from driftbench.journal import Journal, RunKey
from driftbench.runner import RunConfig, expand_matrix, pending, execute_one
from driftbench.task import load_task
from driftbench.workspace import Condition

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def task():
    return load_task(FIXTURES / "tasks" / "minisvc" / "minisvc-001", FIXTURES)


def _config(tmp_path, **overrides):
    base = dict(
        tasks_dir=FIXTURES / "tasks", services_dir=FIXTURES, jar=tmp_path / "s.jar",
        journal_path=tmp_path / "runs.jsonl", work_dir=tmp_path / "work",
        model_specs=["ollama:a", "ollama:b"],
        conditions=[Condition.A, Condition.B, Condition.C],
        seeds_by_model={"ollama:a": 3}, default_seeds=1,
        boot_command=["python", "app.py", "--port", "{port}"],
        test_command=["python", "-m", "pytest", "tests", "-q"],
    )
    base.update(overrides)
    return RunConfig(**base)


def test_matrix_size_respects_per_model_seeds(task, tmp_path):
    matrix = expand_matrix([task], _config(tmp_path))
    # model a: 3 conditions x 3 seeds = 9; model b: 3 conditions x 1 seed = 3
    assert len(matrix) == 12


def test_matrix_is_deterministic(task, tmp_path):
    config = _config(tmp_path)
    assert expand_matrix([task], config) == expand_matrix([task], config)


def test_matrix_entries_are_runkeys(task, tmp_path):
    first = expand_matrix([task], _config(tmp_path))[0]
    assert isinstance(first, RunKey)
    assert first.task_id == "minisvc-001"


def test_pending_excludes_journaled(task, tmp_path):
    config = _config(tmp_path)
    matrix = expand_matrix([task], config)
    journal = Journal(config.journal_path)
    journal.append({
        "task_id": matrix[0].task_id, "condition": matrix[0].condition,
        "model_id": matrix[0].model_id, "seed": matrix[0].seed,
        "timestamp": "2026-08-12T00:00:00Z",
    })
    assert len(pending(matrix, journal)) == len(matrix) - 1


def test_pending_with_empty_journal_is_everything(task, tmp_path):
    config = _config(tmp_path)
    matrix = expand_matrix([task], config)
    assert pending(matrix, Journal(config.journal_path)) == matrix


def test_execute_one_builds_a_complete_record(task, tmp_path, monkeypatch):
    import driftbench.runner as mod
    from driftbench.scaffold import ScaffoldResult
    from driftbench.scorer import Score
    from driftbench.testrunner import TestResult

    monkeypatch.setattr(mod, "run_agent", lambda *a, **k: ScaffoldResult(
        patch_applied=True, iterations=2, changed_files=["app.py"],
        test_result=TestResult(passed=True, returncode=0, stdout="", stderr="", timed_out=False),
        prompt_tokens=100, completion_tokens=50,
    ))
    monkeypatch.setattr(mod, "score", lambda *a, **k: Score(
        contract_pass=False, acceptance_pass=True, drift_classes=["D2"], laundering=False,
    ))

    key = RunKey("minisvc-001", "C", "ollama:a", 0)
    record = execute_one(key, task, _config(tmp_path), provider=object())

    for field in ("task_id", "condition", "model_id", "seed", "timestamp",
                  "patch_applied", "tests_pass", "acceptance_pass",
                  "contract_pass", "drift_classes", "laundering",
                  "iterations", "prompt_tokens", "completion_tokens"):
        assert field in record, f"{field} missing from journal record"
    assert record["tests_pass"] is True and record["contract_pass"] is False
    assert record["drift_classes"] == ["D2"]


def test_execute_one_records_scaffold_failure_without_scoring(task, tmp_path, monkeypatch):
    import driftbench.runner as mod
    from driftbench.scaffold import ScaffoldResult

    monkeypatch.setattr(mod, "run_agent", lambda *a, **k: ScaffoldResult(
        patch_applied=False, iterations=4, error="model produced no parseable file blocks",
    ))

    def _should_not_run(*a, **k):
        raise AssertionError("scoring must be skipped when no patch applied")

    monkeypatch.setattr(mod, "score", _should_not_run)

    record = execute_one(RunKey("minisvc-001", "A", "ollama:a", 0), task, _config(tmp_path), provider=object())
    assert record["patch_applied"] is False
    assert record["contract_pass"] is False
    assert record["error"] is not None
