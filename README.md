# DriftBench

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-139%20passing-brightgreen)](tests/)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Cost to reproduce](https://img.shields.io/badge/reproduces%20for-%240-c9a35c)](#install)

**A benchmark measuring whether AI coding agents silently break API contracts.**

SWE-bench and its successors all ask the same question: *did the unit tests pass?*
Nobody asks the question that actually matters in production — **did the patch
still honor the service's published interface?** An agent can pass every test in
the suite while quietly dropping a validation, changing a status code, or adding
a field nobody documented. That's a contract break that ships silently, and the
first person to notice is whoever's downstream service breaks in prod.

DriftBench runs coding agents against real services with real OpenAPI specs and
scores every patch on both axes — **do the tests pass, and does the contract
still hold** — then goes one step further: if the agent is given write access to
the spec, does it *fix its code*, or does it quietly *weaken the spec* to match
its own broken output? That behavior — **contract laundering** — is this
benchmark's namesake finding, and no existing benchmark measures it.

**The entire benchmark reproduces for $0.** Local inference via Ollama, free-tier
cloud inference via Gemini — no paid API keys required to run a single line of
this.

---

## Headline metric

```
                 runs where tests PASS and contract conformance FAILS
SCBR   =    ───────────────────────────────────────────────────────────
                          total runs where tests PASS
```

A patch that passes CI and breaks the contract is exactly the failure mode every
existing agent benchmark is blind to. SCBR makes it a first-class, reportable number.

## The three-condition design

Every task runs three times, varying only what the agent can see of the contract:

| Condition | The agent sees | Question it answers |
|---|---|---|
| **A** — Hidden | no spec at all | baseline drift rate with zero contract awareness |
| **B** — Read-only | `openapi.yaml`, forbidden to edit | does *seeing* the contract reduce drift? |
| **C** — Editable | `openapi.yaml`, free to edit | does the agent **launder** the contract instead of fixing the code? |

Condition C is the interesting one. If an agent's code fails the original spec, and
the agent has write access to that spec, there's a shortcut available that a
test-only benchmark can't see: rewrite the spec to describe whatever the broken
code actually does, and the tests still go green. DriftBench's D6 detector diffs
the spec before and after every Condition-C run and flags exactly that pattern.

## Drift taxonomy

Every contract failure Specmatic reports gets classified, not just counted:

| Class | Failure mode |
|---|---|
| D1 | Undocumented status code |
| D2 | Response shape drift |
| D3 | Input validation dropped |
| D4 | Error-body shape drift |
| D5 | Auth regression |
| **D6** | **Contract laundering** — spec weakened to match non-conforming code |

## Architecture

```
 tasks × models × conditions × seeds
              │
              ▼
   ┌─────────────────────┐        resumable — skips any (task, model,
   │   runner.py          │◄────── condition, seed) tuple already in
   │   (matrix scheduler) │        runs/runs.jsonl
   └──────────┬───────────┘
              ▼
   ┌─────────────────────┐   sandboxed copy-on-write workspace per run
   │   workspace.py        │
   └──────────┬───────────┘
              ▼
   ┌─────────────────────┐   condition-specific prompt → model call →
   │   scaffold.py          │   parse full-file rewrite → apply → run
   │   (agent loop)          │   baseline tests → up to 3 self-repairs
   └──────────┬───────────┘
              ▼
   ┌─────────────────────┐   spec diff (D6) · boot service · run
   │   scorer/               │   acceptance test · Specmatic contract
   │   (orchestrated)        │   check · classify D1–D5 · laundering call
   └──────────┬───────────┘
              ▼
   ┌─────────────────────┐   append-only, one line per run —
   │   journal.py            │   crash-safe, third-party reproducible
   └─────────────────────┘
```

One scaffold, one prompt template, every model — only the condition-specific
paragraph changes. Scaffold quality is the largest confound in agent
benchmarking, so it's held constant and published rather than hidden.

## Install

```bash
pip install -e ".[dev]"
curl -L -o tools/specmatic.jar \
  https://github.com/specmatic/specmatic/releases/latest/download/specmatic.jar
```

## Run

```bash
# Local, zero-cost inference
driftbench run \
  --tasks benchmark/tasks --services benchmark/services \
  --jar tools/specmatic.jar --journal runs/runs.jsonl --work runs/work \
  --model ollama:qwen2.5-coder:7b --condition A --condition B --condition C --seeds 1

# Free-tier cloud inference
driftbench run \
  --tasks benchmark/tasks --services benchmark/services \
  --jar tools/specmatic.jar --journal runs/runs.jsonl --work runs/work \
  --model gemini:gemini-2.5-flash --condition A --condition B --condition C --seeds 1

driftbench report --journal runs/runs.jsonl
```

Runs are resumable: re-invoking `run` skips every `(task, condition, model, seed)`
already present in the journal, so an interrupted free-tier run picks up exactly
where it stopped.

## Corpus

| Service | Stack | Tasks |
|---|---|---|
| `bookstore` | Flask + SQLite | 3 |
| `taskmanager` | FastAPI + SQLite | 3 |
| `mediaplayer` | Express + SQLite | in progress |

Each service ships its own baseline pytest/jest suite, a `seed` script, and an
`oracle/spec.yaml` describing the contract the patch is expected to preserve.
Corpus expansion is ongoing — see [Roadmap](#roadmap).

## Status

The harness is built and end-to-end validated: matrix scheduling, resumable
journaling, all six drift classes, and orchestrated scoring are implemented and
covered by a **139-test suite**. An early pilot — Gemini 2.5 Flash against the
`bookstore` task suite, all three conditions — is already in the journal:

| | |
|---|---|
| Runs logged | 12 |
| Tests passing | 12 / 12 |
| Contract conformance | 12 / 12 |
| Spec modified (Condition C) | 1 |
| Contract laundering (D6) | 0 |

This is pilot data from one service and one model family, not a benchmark
result — it exists to prove the pipeline is correct end-to-end. The full run
matrix (all services × multiple model families × all conditions × multiple
seeds) is the next milestone; see [Roadmap](#roadmap).

## Design notes

- **Patches are full-file rewrites, not diffs.** Models fail at exact line
  numbers, and a diff that won't apply measures the format rather than the
  model.
- **One scaffold for every model.** Only the condition-specific paragraph of
  the system prompt varies.
- **The oracle never enters the workspace.** Scoring always runs against the
  pristine spec, never against anything the agent could have touched.
- **Everything is journaled immediately, append-only.** A free-tier rate limit
  or a killed process loses at most the in-flight run.

## Roadmap

- [ ] Expand corpus past 3 services / harvest 4–5 real-world repos
- [ ] Full run matrix across Ollama + Gemini model families, multiple seeds
- [ ] Publish the first SCBR numbers with full methodology write-up
- [ ] Add a second cloud provider for cross-family comparison

## Contributing

Issues and PRs are welcome, especially new corpus services/tasks — see
[`AGENT.md`](AGENT.md) for the exact format a new service or task needs to
follow to be picked up by the runner.

## License

[MIT](LICENSE)
