"""DriftBench command line."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Annotated

import typer

from driftbench.journal import Journal
from driftbench.runner import RunConfig, run as run_matrix
from driftbench.workspace import Condition

app = typer.Typer(add_completion=False, help="Measure whether AI agents preserve API contracts.")


@app.command()
def run(
    tasks: Annotated[Path, typer.Option("--tasks")],
    services: Annotated[Path, typer.Option("--services")],
    jar: Annotated[Path, typer.Option("--jar")],
    journal: Annotated[Path, typer.Option("--journal")],
    work: Annotated[Path, typer.Option("--work")],
    model: Annotated[list[str], typer.Option("--model", help="e.g. ollama:qwen2.5-coder:7b")] = None,
    condition: Annotated[list[str], typer.Option("--condition")] = None,
    seeds: Annotated[int, typer.Option("--seeds")] = 1,
    boot: Annotated[str, typer.Option("--boot")] = "python3 app.py --port {port}",
    test: Annotated[str, typer.Option("--test")] = "python3 -m pytest tests -q",
) -> None:
    """Execute the pending run matrix, resuming from the journal."""
    if not model:
        typer.echo("error: at least one --model is required", err=True)
        raise typer.Exit(code=2)

    conditions = [Condition(c) for c in (condition or ["A", "B", "C"])]
    config = RunConfig(
        tasks_dir=tasks, services_dir=services, jar=jar, journal_path=journal, work_dir=work,
        model_specs=list(model), conditions=conditions, default_seeds=seeds,
        boot_command=boot.split(), test_command=test.split(),
    )
    executed = run_matrix(config)
    typer.echo(f"executed {executed} run(s); journal: {journal}")


@app.command()
def report(journal: Annotated[Path, typer.Option("--journal")]) -> None:
    """Print SCBR and breakdowns from a run journal."""
    rows = list(Journal(journal).records())
    if not rows:
        typer.echo("no runs found in journal")
        raise typer.Exit(code=0)

    test_passing = [r for r in rows if r.get("tests_pass")]
    broken = [r for r in test_passing if not r.get("contract_pass")]

    typer.echo(f"runs journaled:        {len(rows)}")
    typer.echo(f"patches applied:       {sum(1 for r in rows if r.get('patch_applied'))}")
    typer.echo(f"tests passing:         {len(test_passing)}")
    if test_passing:
        typer.echo(f"SCBR:                  {100 * len(broken) / len(test_passing):.1f}% "
                   f"({len(broken)}/{len(test_passing)})")

    by_condition: dict[str, list[dict]] = defaultdict(list)
    for row in test_passing:
        by_condition[row.get("condition", "?")].append(row)

    typer.echo("\nby condition (SCBR, laundering):")
    for name in sorted(by_condition):
        group = by_condition[name]
        failed = sum(1 for r in group if not r.get("contract_pass"))
        laundered = sum(1 for r in group if r.get("laundering"))
        rate = 100 * failed / len(group)
        typer.echo(f"  {name}: {rate:5.1f}%  ({failed}/{len(group)})   laundering: {laundered}")

    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in test_passing:
        by_model[row.get("model_id", "?")].append(row)

    typer.echo("\nby model (SCBR):")
    for name in sorted(by_model):
        group = by_model[name]
        failed = sum(1 for r in group if not r.get("contract_pass"))
        typer.echo(f"  {name}: {100 * failed / len(group):5.1f}%  ({failed}/{len(group)})")

    drift = Counter(cls for row in rows for cls in row.get("drift_classes", []))
    if drift:
        typer.echo("\ndrift classes:")
        for cls, count in sorted(drift.items()):
            typer.echo(f"  {cls}: {count}")
