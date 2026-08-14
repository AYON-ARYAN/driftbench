"""Invoke the Specmatic JAR and parse its CTRF report."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SpecmaticOutcome:
    ran: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    failures: list[dict] = field(default_factory=list)
    raw_report: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def contract_pass(self) -> bool:
        return self.ran and self.failed == 0 and self.total > 0


def parse_ctrf(report: dict) -> SpecmaticOutcome:
    results = report.get("results")
    if not isinstance(results, dict) or "tests" not in results:
        return SpecmaticOutcome(ran=False, error="report is not valid CTRF")

    tests = results.get("tests") or []
    summary = results.get("summary") or {}
    failures = [
        {"name": t.get("name", ""), "message": t.get("message", "")}
        for t in tests
        if t.get("status") == "failed"
    ]
    return SpecmaticOutcome(
        ran=True,
        total=int(summary.get("tests", len(tests))),
        passed=int(summary.get("passed", sum(1 for t in tests if t.get("status") == "passed"))),
        failed=int(summary.get("failed", len(failures))),
        failures=failures,
        raw_report=report,
    )


def run_specmatic(
    jar: Path,
    config: Path,
    spec: Path,
    base_url: str,
    report_dir: Path,
    examples: Path | None = None,
    timeout: int = 900,
) -> SpecmaticOutcome:
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "java", "-jar", str(jar), "test", str(spec),
        f"--config={config}",
        f"--testBaseURL={base_url}",
    ]
    if examples is not None and Path(examples).is_dir():
        command.append(f"--examples={examples}")

    try:
        proc = subprocess.run(
            command, cwd=str(report_dir), capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return SpecmaticOutcome(ran=False, error=f"specmatic timed out after {timeout}s")
    except FileNotFoundError as exc:
        return SpecmaticOutcome(ran=False, error=f"java or jar not found: {exc}")

    ctrf_files = sorted(report_dir.rglob("*ctrf*.json"))
    if not ctrf_files:
        tail = (proc.stdout + proc.stderr)[-1500:]
        return SpecmaticOutcome(ran=False, error=f"no CTRF report produced; output tail:\n{tail}")

    try:
        report = json.loads(ctrf_files[-1].read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return SpecmaticOutcome(ran=False, error=f"CTRF report unparseable: {exc}")

    return parse_ctrf(report)
