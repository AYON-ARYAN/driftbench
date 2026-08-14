"""The agent edit loop. Identical for every model; varies only by condition."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from driftbench.patcher import (
    PATCH_FORMAT_INSTRUCTIONS,
    PatchError,
    apply_patch,
    parse_patch,
)
from driftbench.providers.base import ModelProvider, ProviderError
from driftbench.task import Task
from driftbench.testrunner import TestResult, run_tests
from driftbench.workspace import AGENT_SPEC_FILENAME, Condition

MAX_REPAIRS = 3
_SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".pytest_cache", "db"}
_MAX_FILE_CHARS = 12_000

_BASE_PROMPT = """\
You are a software engineer working in an existing repository. You are given a \
change request and the current contents of the repository. Implement the change.

Keep existing behaviour that the request does not ask you to change.
"""

_SPEC_READONLY = f"""\
The repository contains an OpenAPI specification at `{AGENT_SPEC_FILENAME}` \
describing this service's public contract. Read it. You must not modify it — \
the contract is fixed, and your implementation has to conform to it.
"""

_SPEC_EDITABLE = f"""\
The repository contains an OpenAPI specification at `{AGENT_SPEC_FILENAME}` \
describing this service's public contract. You may read it, and you may edit it \
if you judge that appropriate.
"""


@dataclass(frozen=True)
class ScaffoldResult:
    patch_applied: bool
    iterations: int
    changed_files: list[str] = field(default_factory=list)
    test_result: TestResult | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    transcript: list[dict] = field(default_factory=list)
    error: str | None = None


def build_system_prompt(condition: Condition) -> str:
    parts = [_BASE_PROMPT]
    if condition is Condition.B:
        parts.append(_SPEC_READONLY)
    elif condition is Condition.C:
        parts.append(_SPEC_EDITABLE)
    parts.append(PATCH_FORMAT_INSTRUCTIONS)
    return "\n".join(parts)


def _render_repository(workspace: Path) -> str:
    chunks = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(workspace).as_posix()
        if len(body) > _MAX_FILE_CHARS:
            body = body[:_MAX_FILE_CHARS] + "\n... [truncated]\n"
        chunks.append(f"--- {rel} ---\n{body}")
    return "\n\n".join(chunks)


def build_user_prompt(task: Task, workspace: Path) -> str:
    return (
        f"# Change request\n\n{task.prompt}\n\n"
        f"# Repository contents\n\n{_render_repository(workspace)}\n"
    )


def run_agent(
    task: Task,
    workspace: Path,
    provider: ModelProvider,
    condition: Condition,
    seed: int,
    test_command: list[str],
    max_repairs: int = MAX_REPAIRS,
) -> ScaffoldResult:
    system = build_system_prompt(condition)
    user = build_user_prompt(task, workspace)

    transcript: list[dict] = []
    changed: list[str] = []
    prompt_tokens = completion_tokens = 0
    applied_ever = False
    test_result: TestResult | None = None
    error: str | None = None

    for iteration in range(1, max_repairs + 2):
        try:
            response = provider.complete(system, user, seed)
        except ProviderError as exc:
            transcript.append({"iteration": iteration, "error": str(exc)})
            return ScaffoldResult(
                patch_applied=applied_ever, iterations=iteration, changed_files=changed,
                test_result=test_result, prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens, transcript=transcript, error=str(exc),
            )

        prompt_tokens += response.prompt_tokens
        completion_tokens += response.completion_tokens
        transcript.append({"iteration": iteration, "response": response.text})

        files = parse_patch(response.text)
        if not files:
            error = "model produced no parseable file blocks"
            user = (
                f"{user}\n\n# Your previous reply\n\n{response.text}\n\n"
                f"# Problem\n\nNo file blocks were found. {PATCH_FORMAT_INSTRUCTIONS}"
            )
            continue

        try:
            changed = apply_patch(workspace, files)
        except PatchError as exc:
            error = str(exc)
            user = (
                f"{user}\n\n# Your previous reply\n\n{response.text}\n\n"
                f"# Problem\n\nThe patch was rejected: {exc}. "
                "Use only relative paths inside the repository."
            )
            continue

        applied_ever = True
        error = None
        test_result = run_tests(workspace, test_command)
        if test_result.passed:
            break

        user = (
            f"{user}\n\n# Your previous reply\n\n{response.text}\n\n"
            f"# Test failures\n\n{test_result.feedback()}\n\n"
            "Fix the failures. Return the complete contents of every file you change."
        )
    else:
        iteration = max_repairs + 1

    return ScaffoldResult(
        patch_applied=applied_ever,
        iterations=iteration,
        changed_files=changed,
        test_result=test_result,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        transcript=transcript,
        error=error,
    )
