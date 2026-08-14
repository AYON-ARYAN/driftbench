import json
from pathlib import Path
from typer.testing import CliRunner
from driftbench.cli import app

runner = CliRunner()


def _journal(tmp_path, rows):
    path = tmp_path / "runs.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def _row(**kw):
    base = {"task_id": "t1", "condition": "A", "model_id": "ollama:m", "seed": 0,
            "timestamp": "2026-08-12T00:00:00Z", "patch_applied": True,
            "tests_pass": True, "acceptance_pass": True, "contract_pass": True,
            "drift_classes": [], "laundering": False}
    base.update(kw)
    return base


def test_report_computes_scbr(tmp_path):
    path = _journal(tmp_path, [
        _row(task_id="t1", contract_pass=True),
        _row(task_id="t2", contract_pass=False, drift_classes=["D1"]),
        _row(task_id="t3", contract_pass=False, drift_classes=["D2"]),
        _row(task_id="t4", tests_pass=False, contract_pass=False),   # excluded: tests failed
    ])
    result = runner.invoke(app, ["report", "--journal", str(path)])
    assert result.exit_code == 0
    assert "66.7%" in result.stdout          # 2 of 3 test-passing runs break the contract


def test_report_breaks_down_by_condition(tmp_path):
    path = _journal(tmp_path, [
        _row(condition="A", contract_pass=False, drift_classes=["D1"]),
        _row(condition="B", contract_pass=True),
        _row(condition="C", contract_pass=False, laundering=True, drift_classes=["D2"]),
    ])
    result = runner.invoke(app, ["report", "--journal", str(path)])
    for token in ("A", "B", "C", "laundering"):
        assert token in result.stdout


def test_report_on_empty_journal_does_not_crash(tmp_path):
    result = runner.invoke(app, ["report", "--journal", str(tmp_path / "none.jsonl")])
    assert result.exit_code == 0
    assert "no runs" in result.stdout.lower()


def test_run_requires_at_least_one_model(tmp_path):
    result = runner.invoke(app, ["run", "--tasks", str(tmp_path), "--services", str(tmp_path),
                                 "--jar", str(tmp_path / "s.jar"), "--journal", str(tmp_path / "j.jsonl"),
                                 "--work", str(tmp_path / "w")])
    assert result.exit_code != 0
