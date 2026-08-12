from pathlib import Path
import pytest
from driftbench.task import load_task
from driftbench.workspace import Condition, prepare_workspace, agent_spec_path, AGENT_SPEC_FILENAME

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def task():
    return load_task(FIXTURES / "tasks" / "minisvc" / "minisvc-001", FIXTURES)


def test_condition_a_has_no_spec(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "a")
    assert (ws / "app.py").exists()
    assert not agent_spec_path(ws).exists()


@pytest.mark.parametrize("condition", [Condition.B, Condition.C])
def test_conditions_b_and_c_place_the_spec(task, condition, tmp_path):
    ws = prepare_workspace(task, condition, tmp_path / condition.value)
    assert agent_spec_path(ws).read_text() == task.oracle_spec.read_text()
    assert agent_spec_path(ws).name == AGENT_SPEC_FILENAME


@pytest.mark.parametrize("condition", list(Condition))
def test_oracle_never_reaches_the_workspace(task, condition, tmp_path):
    ws = prepare_workspace(task, condition, tmp_path / condition.value)
    assert not (ws / "oracle").exists()
    assert "specmatic.yaml" not in {p.name for p in ws.rglob("*")}
    assert "acceptance_test.py" not in {p.name for p in ws.rglob("*")}


def test_workspace_is_an_independent_copy(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "a")
    (ws / "app.py").write_text("# clobbered\n")
    assert "clobbered" not in (task.service_dir / "app.py").read_text()


def test_existing_destination_is_replaced(task, tmp_path):
    dest = tmp_path / "a"
    dest.mkdir()
    (dest / "stale.txt").write_text("old")
    ws = prepare_workspace(task, Condition.A, dest)
    assert not (ws / "stale.txt").exists()


def test_db_artifacts_are_not_copied(task, tmp_path):
    stale_db = task.service_dir / "db" / "minisvc.db"
    stale_db.parent.mkdir(exist_ok=True)
    stale_db.write_bytes(b"stale")
    try:
        ws = prepare_workspace(task, Condition.A, tmp_path / "a")
        assert not (ws / "db" / "minisvc.db").exists()
    finally:
        stale_db.unlink()
