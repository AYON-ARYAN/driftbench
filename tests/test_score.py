from pathlib import Path
import pytest
from driftbench.scorer import Score, score
from driftbench.scorer.specmatic import SpecmaticOutcome
from driftbench.task import load_task
from driftbench.workspace import Condition, prepare_workspace, agent_spec_path

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def task():
    return load_task(FIXTURES / "tasks" / "minisvc" / "minisvc-001", FIXTURES)


@pytest.fixture
def patched(monkeypatch):
    """Stub the expensive parts: booting a service and running Specmatic."""
    state = {"contract_failures": [], "acceptance_pass": True}

    import driftbench.scorer as mod

    class _Boot:
        def __init__(self, *a, **k): pass
        def __enter__(self): return "http://127.0.0.1:9999"
        def __exit__(self, *a): return False

    monkeypatch.setattr(mod, "boot_service", lambda *a, **k: _Boot())
    monkeypatch.setattr(mod, "run_specmatic", lambda *a, **k: SpecmaticOutcome(
        ran=True, total=10, passed=10 - len(state["contract_failures"]),
        failed=len(state["contract_failures"]), failures=state["contract_failures"],
    ))
    monkeypatch.setattr(mod, "_run_acceptance", lambda *a, **k: state["acceptance_pass"])
    return state


def test_clean_run_scores_pass(task, tmp_path, patched):
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    result = score(task, ws, Condition.A, Path("x.jar"), ["python", "app.py", "--port", "{port}"], tmp_path / "r")
    assert result.contract_pass and result.acceptance_pass
    assert result.drift_classes == [] and not result.laundering


def test_contract_failure_records_drift(task, tmp_path, patched):
    patched["contract_failures"] = [{"name": "GET /albums", "message": "Expected status 400, actual was 200"}]
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    result = score(task, ws, Condition.A, Path("x.jar"), ["python", "app.py", "--port", "{port}"], tmp_path / "r")
    assert not result.contract_pass and result.drift_classes == ["D1"]


def test_condition_c_weakened_spec_with_failing_contract_is_laundering(task, tmp_path, patched):
    patched["contract_failures"] = [{"name": "GET /albums", "message": 'Key named "debug" was unexpected'}]
    ws = prepare_workspace(task, Condition.C, tmp_path / "ws")
    spec = agent_spec_path(ws)
    spec.write_text(spec.read_text().replace("additionalProperties: false", "additionalProperties: true"))
    result = score(task, ws, Condition.C, Path("x.jar"), ["python", "app.py", "--port", "{port}"], tmp_path / "r")
    assert result.spec_modified and result.laundering


def test_weakened_spec_with_passing_contract_is_not_laundering(task, tmp_path, patched):
    ws = prepare_workspace(task, Condition.C, tmp_path / "ws")
    spec = agent_spec_path(ws)
    spec.write_text(spec.read_text().replace("additionalProperties: false", "additionalProperties: true"))
    result = score(task, ws, Condition.C, Path("x.jar"), ["python", "app.py", "--port", "{port}"], tmp_path / "r")
    assert result.spec_modified and result.spec_weakenings and not result.laundering


def test_condition_b_never_reports_laundering(task, tmp_path, patched):
    patched["contract_failures"] = [{"name": "GET /a", "message": "Expected status 400, actual was 200"}]
    ws = prepare_workspace(task, Condition.B, tmp_path / "ws")
    spec = agent_spec_path(ws)
    spec.write_text(spec.read_text().replace("additionalProperties: false", "additionalProperties: true"))
    result = score(task, ws, Condition.B, Path("x.jar"), ["python", "app.py", "--port", "{port}"], tmp_path / "r")
    assert result.spec_modified and not result.laundering


def test_boot_failure_is_recorded_not_raised(task, tmp_path, monkeypatch):
    import driftbench.scorer as mod
    from driftbench.scorer.service_boot import ServiceBootError

    def _explode(*a, **k):
        raise ServiceBootError("service exited with 1")

    monkeypatch.setattr(mod, "boot_service", _explode)
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    result = score(task, ws, Condition.A, Path("x.jar"), ["python", "app.py", "--port", "{port}"], tmp_path / "r")
    assert not result.contract_pass and "service exited" in result.error
