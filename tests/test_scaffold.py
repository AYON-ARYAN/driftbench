import sys
from pathlib import Path
import pytest
from driftbench.providers.base import ModelResponse
from driftbench.scaffold import build_system_prompt, run_agent, ScaffoldResult
from driftbench.task import load_task
from driftbench.workspace import Condition, prepare_workspace

FIXTURES = Path(__file__).parent / "fixtures"
PY = sys.executable


class ScriptedProvider:
    """Returns queued responses in order; records the prompts it was given."""

    def __init__(self, responses):
        self.model_id = "scripted:test"
        self._responses = list(responses)
        self.calls = []

    def complete(self, system, user, seed):
        self.calls.append({"system": system, "user": user, "seed": seed})
        return ModelResponse(text=self._responses.pop(0), prompt_tokens=5, completion_tokens=9)


@pytest.fixture
def task():
    return load_task(FIXTURES / "tasks" / "minisvc" / "minisvc-001", FIXTURES)


PASSING = "### FILE: t.py\n```python\ndef test_ok():\n    assert True\n```\n"
FAILING = "### FILE: t.py\n```python\ndef test_ok():\n    assert False\n```\n"


def test_system_prompt_condition_a_never_mentions_a_spec_file():
    prompt = build_system_prompt(Condition.A)
    assert "openapi.yaml" not in prompt


def test_system_prompt_condition_b_forbids_editing_the_spec():
    prompt = build_system_prompt(Condition.B)
    assert "openapi.yaml" in prompt
    assert "must not" in prompt.lower() or "do not" in prompt.lower()


def test_system_prompt_condition_c_permits_editing_the_spec():
    prompt = build_system_prompt(Condition.C)
    assert "openapi.yaml" in prompt
    assert "may" in prompt.lower()


def test_successful_first_attempt_stops_immediately(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    provider = ScriptedProvider([PASSING])
    result = run_agent(task, ws, provider, Condition.A, seed=0, test_command=[PY, "-m", "pytest", "t.py", "-q"])
    assert result.patch_applied and result.test_result.passed
    assert result.iterations == 1
    assert len(provider.calls) == 1


def test_failure_triggers_repair_and_can_succeed(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    provider = ScriptedProvider([FAILING, PASSING])
    result = run_agent(task, ws, provider, Condition.A, seed=0, test_command=[PY, "-m", "pytest", "t.py", "-q"])
    assert result.iterations == 2 and result.test_result.passed
    assert "assert False" not in provider.calls[1]["user"] or "FAILED" in provider.calls[1]["user"]


def test_repairs_are_capped(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    provider = ScriptedProvider([FAILING] * 6)
    result = run_agent(task, ws, provider, Condition.A, seed=0,
                       test_command=[PY, "-m", "pytest", "t.py", "-q"], max_repairs=2)
    assert result.iterations == 3          # first attempt + 2 repairs
    assert not result.test_result.passed


def test_unparseable_output_records_no_patch_applied(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    provider = ScriptedProvider(["I cannot do this."] * 4)
    result = run_agent(task, ws, provider, Condition.A, seed=0, test_command=[PY, "-c", "pass"])
    assert not result.patch_applied
    assert result.error is not None


def test_unsafe_path_is_recorded_not_raised(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    provider = ScriptedProvider(["### FILE: ../evil.py\n```\nx=1\n```\n"] * 4)
    result = run_agent(task, ws, provider, Condition.A, seed=0, test_command=[PY, "-c", "pass"])
    assert not result.patch_applied
    assert "escapes workspace" in result.error


def test_token_counts_accumulate(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    provider = ScriptedProvider([FAILING, PASSING])
    result = run_agent(task, ws, provider, Condition.A, seed=0, test_command=[PY, "-m", "pytest", "t.py", "-q"])
    assert result.prompt_tokens == 10 and result.completion_tokens == 18


def test_seed_is_forwarded(task, tmp_path):
    ws = prepare_workspace(task, Condition.A, tmp_path / "ws")
    provider = ScriptedProvider([PASSING])
    run_agent(task, ws, provider, Condition.A, seed=7, test_command=[PY, "-m", "pytest", "t.py", "-q"])
    assert provider.calls[0]["seed"] == 7
