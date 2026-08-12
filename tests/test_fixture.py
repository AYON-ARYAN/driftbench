from pathlib import Path
from driftbench.task import load_task

FIXTURES = Path(__file__).parent / "fixtures"


def test_fixture_task_loads():
    task = load_task(FIXTURES / "tasks" / "minisvc" / "minisvc-001", FIXTURES)
    assert task.service == "minisvc"
    assert task.task_type == "add_pagination"
    assert "limit" in task.prompt


def test_fixture_service_has_entrypoint():
    assert (FIXTURES / "minisvc" / "app.py").exists()
    assert (FIXTURES / "minisvc" / "seed.py").exists()
