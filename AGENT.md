# DriftBench Agent Context & Developer Guide

Welcome to the **DriftBench** repository! This document is designed specifically for AI agents, developers, and researchers who want to understand the codebase, context, architecture, and how to continue development or run benchmarks.

---

## 📖 1. What is DriftBench?

**DriftBench** is a research benchmark designed to measure and expose a critical, unmeasured vulnerability in AI coding agents: **Silent Contract Breakage**.

### The Core Thesis:
Traditional developer leaderboards (like SWE-bench) evaluate AI coding agents on a single metric: *Did the unit tests pass?* 

However, unit tests only verify specific paths. They rarely verify if the agent's code modifications preserved the service's published **API contract** (its OpenAPI/Swagger specification). An agent can easily introduce undocumented response fields, drop critical input validations, or change response status codes. These changes pass traditional unit-testing CI suites, but **silently break downstream microservices in production**.

### Headline Metric — Silent Contract Breakage Rate (SCBR):
$$SCBR = \frac{\text{Runs where unit tests PASS and contract conformance FAILS}}{\text{Total runs where unit tests PASS}}$$

### Experimental Design (3 Conditions):
To study how specification visibility affects agent behavior, every task is run under three conditions:
*   **Condition A (Hidden):** The agent never sees the OpenAPI specification file.
*   **Condition B (Read-Only):** The agent sees `openapi.yaml` but is strictly forbidden from editing it.
*   **Condition C (Editable):** The agent has full write-access to `openapi.yaml`. (Tests whether the agent engages in **Contract Laundering (D6)** — editing the spec to match its lazy/non-conforming code instead of fixing the code).

---

## 📂 2. Repository Architecture

```
/
├── README.md               # Quick start, installation, and run instructions
├── AGENT.md                # This context-loading file for AI developers
├── pyproject.toml          # Declarative python packaging metadata
├── src/                    # Core Benchmark Engine
│   └── driftbench/
│       ├── providers/      # Model Provider Protocol & Clients
│       │   ├── base.py     # Agnostic ModelProvider Protocol & ModelResponse
│       │   ├── ollama.py   # Local Ollama client
│       │   └── gemini.py   # Google AI Studio cloud Gemini client
│       ├── scorer/         # API Contract Scorer Engine
│       │   ├── service_boot.py # Subprocess service boot lifecycles & health checks
│       │   ├── specmatic.py   # Subprocess Specmatic tester and CTRF json report parser
│       │   ├── specdiff.py    # D6 Spec-weakening and modification analyzer
│       │   └── drift.py       # Regex taxonomy failure classifier
│       ├── cli.py          # Typer CLI application commands (run, report)
│       ├── journal.py      # Append-only JSONL run journal manager
│       ├── runner.py       # Resumable matrix scheduler
│       ├── scaffold.py     # Model-agnostic self-healing edit-and-repair loop
│       └── workspace.py    # Sandbox copy-on-write workspace creator
├── tests/                  # Complete 139-test unit & integration suite
├── tools/                  # Pinned offline executable Specmatic jar file
└── benchmark/              # Benchmark Corpus Dataset
    ├── services/           # Corpus Baseline Microservices
    │   ├── bookstore/      # Flask SQLite Bookstore Service (8 pytest suite)
    │   └── taskmanager/    # FastAPI SQLite TaskManager Service (8 pytest suite)
    └── tasks/              # Corpus Task Suites
        ├── bookstore/      # bookstore-001, bookstore-002, bookstore-003
        └── taskmanager/    # taskmanager-001, taskmanager-002, taskmanager-003
```

---

## 🔄 3. Core Benchmarking Workflow

When `driftbench run` is invoked:

1.  **Matrix Expansion (`src/driftbench/runner.py`):**
    Expands the full matrix `(tasks × models × conditions × seeds)`.
2.  **Resumability Checking (`src/driftbench/journal.py`):**
    Loads `runs/runs.jsonl`, reads all completed run keys, and filters them out so the runner only executes pending tasks.
3.  **Workspace Sandboxing (`src/driftbench/workspace.py`):**
    Creates a temporary, isolated workspace directory for the task to prevent file collisions.
4.  **Agent Scaffold Loop (`src/driftbench/scaffold.py`):**
    *   Generates system prompts based on the experimental condition.
    *   Queries the model provider (Ollama or Gemini).
    *   Parses the model's full-file rewrite blocks and applies the patches.
    *   Executes the service's baseline test suite.
    *   **Self-Healing/Repair:** If the tests fail, it feeds the stderr trace back to the model and retries (up to 3 repairs).
5.  **Orchestrated Scoring (`src/driftbench/scorer/`):**
    *   **Spec Diff (D6):** Measures if the model modified/weakened the OpenAPI spec.
    *   **Service Boot:** Boots the service on a free port and polls `/healthz` until healthy.
    *   **Acceptance Test:** Copies and runs the task's custom natural-language acceptance test.
    *   **Contract Conformance:** Invokes Specmatic and parses the results.
    *   **Drift Taxonomy (D1–D5):** Classifies contract test failures into specific categories.
    *   **Laundering Determination:** Computes if the spec was weakened and the code failed the original contract.
6.  **Journal Logging:**
    Appends the unified run record to `runs/runs.jsonl` immediately.

---

## 🚀 4. How to Continue Development & Add to Corpus

### Adding a New Service to the Corpus:
1.  Create a folder under `benchmark/services/<service_name>`.
2.  Include `requirements.txt` (Python) or `package.json` (Node.js), database seed scripts `seed.py` / `seed.js`, and baseline tests under `tests/`.
3.  Ensure the baseline tests pass completely with `pytest` or `npm test`.

### Adding a New Task:
1.  Create a folder under `benchmark/tasks/<service_name>/<task_id>/`.
2.  Create **`metadata.json`** specifying the custom commands:
    ```json
    {
      "task_id": "service-001",
      "service": "service_name",
      "task_type": "add_endpoint",
      "difficulty": "easy",
      "boot_command": ["/Users/ayonaryan/code/driftbench/.venv/bin/python", "app.py", "--port", "{port}"],
      "test_command": ["/Users/ayonaryan/code/driftbench/.venv/bin/python", "-m", "pytest", "tests", "-q"]
    }
    ```
3.  Include `task.md` (natural language instruction), `baseline.sha` (git commit reference), `acceptance_test.py` (NL test suite), and the target `oracle/spec.yaml` representing the OpenAPI specification *after* the change.
4.  Include any JSON examples under `oracle/examples/` to supply Specmatic with path parameters for dynamic tests.

---

## 📊 5. How to Run & Report

### Run the Benchmark Matrix:
```bash
# Execute local open-weight model
driftbench run \
  --tasks benchmark/tasks --services benchmark/services \
  --jar tools/specmatic.jar --journal runs/runs.jsonl --work runs/work \
  --model ollama:qwen2.5-coder:3b --condition A --seeds 1

# Execute Cloud-based state-of-the-art model
driftbench run \
  --tasks benchmark/tasks --services benchmark/services \
  --jar tools/specmatic.jar --journal runs/runs.jsonl --work runs/work \
  --model gemini:gemini-2.5-flash --condition A --condition B --condition C --seeds 1
```

### Compile the SCBR Evaluation Report:
```bash
driftbench report --journal runs/runs.jsonl
```
