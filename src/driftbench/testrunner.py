"""Run a workspace's existing test suite and capture the outcome."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestResult:
    passed: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool

    def feedback(self, limit: int = 4000) -> str:
        combined = f"{self.stdout}\n{self.stderr}".strip()
        return combined[-limit:]


def run_tests(
    workspace: Path,
    command: list[str],
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> TestResult:
    full_env = {**os.environ, **(env or {})}
    try:
        proc = subprocess.run(
            command,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=full_env,
        )
    except subprocess.TimeoutExpired as exc:
        return TestResult(
            passed=False,
            returncode=-2,
            stdout=exc.stdout or "",
            stderr=f"TIMEOUT after {timeout}s",
            timed_out=True,
        )
    except (FileNotFoundError, PermissionError) as exc:
        return TestResult(passed=False, returncode=-1, stdout="", stderr=str(exc), timed_out=False)

    return TestResult(
        passed=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        timed_out=False,
    )
