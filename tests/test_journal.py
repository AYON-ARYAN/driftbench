import json
import pytest
from driftbench.journal import Journal, RunKey, JournalError, REQUIRED_FIELDS


def _record(task_id="t1", condition="A", model_id="ollama:m", seed=0):
    return {"task_id": task_id, "condition": condition, "model_id": model_id,
            "seed": seed, "timestamp": "2026-08-12T00:00:00Z", "contract_pass": True}


def test_append_then_read_back(tmp_path):
    journal = Journal(tmp_path / "runs.jsonl")
    journal.append(_record())
    assert [r["task_id"] for r in journal.records()] == ["t1"]


def test_completed_keys_reflect_appends(tmp_path):
    journal = Journal(tmp_path / "runs.jsonl")
    journal.append(_record(task_id="t1"))
    journal.append(_record(task_id="t2", seed=1))
    assert journal.completed_keys() == {
        RunKey("t1", "A", "ollama:m", 0),
        RunKey("t2", "A", "ollama:m", 1),
    }


def test_missing_journal_has_no_keys(tmp_path):
    assert Journal(tmp_path / "absent.jsonl").completed_keys() == set()


def test_append_creates_parent_directories(tmp_path):
    journal = Journal(tmp_path / "deep" / "nested" / "runs.jsonl")
    journal.append(_record())
    assert journal.path.exists()


def test_append_rejects_missing_required_field(tmp_path):
    journal = Journal(tmp_path / "runs.jsonl")
    bad = _record()
    del bad["seed"]
    with pytest.raises(JournalError, match="seed"):
        journal.append(bad)
    assert not journal.path.exists()


def test_malformed_line_is_skipped_not_fatal(tmp_path):
    path = tmp_path / "runs.jsonl"
    path.write_text(json.dumps(_record()) + "\n{ this is not json\n" + json.dumps(_record(task_id="t3")) + "\n")
    assert {r["task_id"] for r in Journal(path).records()} == {"t1", "t3"}


def test_append_is_additive_across_instances(tmp_path):
    path = tmp_path / "runs.jsonl"
    Journal(path).append(_record(task_id="t1"))
    Journal(path).append(_record(task_id="t2"))
    assert len(list(Journal(path).records())) == 2


def test_required_fields_are_the_run_key_plus_timestamp():
    assert REQUIRED_FIELDS == ("task_id", "condition", "model_id", "seed", "timestamp")
