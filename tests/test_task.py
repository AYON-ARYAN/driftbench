import json
import pytest
from driftbench.task import Task, load_task, load_all_tasks, TASK_TYPES


def _make_task(tmp_path, task_id="svc-001", task_type="refactor_no_interface_change"):
    services = tmp_path / "services"
    (services / "svc").mkdir(parents=True, exist_ok=True)
    (services / "svc" / "app.py").write_text("# service\n")

    root = tmp_path / "tasks" / "svc" / task_id
    (root / "oracle" / "examples").mkdir(parents=True)
    (root / "task.md").write_text("Add pagination to /albums.\n")
    (root / "acceptance_test.py").write_text("def test_x(): pass\n")
    (root / "oracle" / "spec.yaml").write_text("openapi: 3.0.0\n")
    (root / "oracle" / "specmatic.yaml").write_text("version: 3\n")
    (root / "metadata.json").write_text(json.dumps({
        "task_id": task_id,
        "service": "svc",
        "task_type": task_type,
        "difficulty": "medium",
        "expected_drift_surface": ["D1", "D2"],
    }))
    return root, services


def test_load_task_reads_metadata(tmp_path):
    root, services = _make_task(tmp_path)
    task = load_task(root, services)
    assert task.task_id == "svc-001"
    assert task.service == "svc"
    assert task.difficulty == "medium"


def test_prompt_is_task_md_contents(tmp_path):
    root, services = _make_task(tmp_path)
    assert load_task(root, services).prompt == "Add pagination to /albums.\n"


def test_oracle_and_service_paths_resolve(tmp_path):
    root, services = _make_task(tmp_path)
    task = load_task(root, services)
    assert task.oracle_spec.read_text() == "openapi: 3.0.0\n"
    assert task.oracle_config.name == "specmatic.yaml"
    assert task.oracle_examples.is_dir()
    assert (task.service_dir / "app.py").exists()
    assert task.acceptance_test.name == "acceptance_test.py"


def test_unknown_task_type_rejected(tmp_path):
    root, services = _make_task(tmp_path, task_type="not_a_real_type")
    with pytest.raises(ValueError, match="unknown task_type"):
        load_task(root, services)


def test_missing_oracle_spec_rejected(tmp_path):
    root, services = _make_task(tmp_path)
    (root / "oracle" / "spec.yaml").unlink()
    with pytest.raises(FileNotFoundError, match="spec.yaml"):
        load_task(root, services)


def test_load_all_tasks_sorted(tmp_path):
    _make_task(tmp_path, task_id="svc-002")
    _make_task(tmp_path, task_id="svc-001")
    tasks = load_all_tasks(tmp_path / "tasks", tmp_path / "services")
    assert [t.task_id for t in tasks] == ["svc-001", "svc-002"]


def test_nine_task_types_defined():
    assert len(TASK_TYPES) == 9
    assert "refactor_no_interface_change" in TASK_TYPES
