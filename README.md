# DriftBench

A benchmark measuring whether AI coding agents preserve API contracts.

Existing benchmarks ask "did the unit tests pass?" DriftBench asks whether the
agent's patch still honors the service's published OpenAPI contract — and
whether an agent given write access to that contract weakens it to accommodate
its own broken code.

**The entire benchmark reproduces on free and local inference.** Rerunning it
costs nothing.

## Install

```bash
pip install -e ".[dev]"
curl -L -o tools/specmatic.jar \
  https://github.com/specmatic/specmatic/releases/latest/download/specmatic.jar
```

## Run

```bash
driftbench run \
  --tasks benchmark/tasks --services benchmark/services \
  --jar tools/specmatic.jar --journal runs/runs.jsonl --work runs/work \
  --model ollama:qwen2.5-coder:7b --condition A --condition B --condition C --seeds 1

driftbench report --journal runs/runs.jsonl
```

Runs are resumable: re-invoking `run` skips every (task, condition, model, seed)
already present in the journal.

## Conditions

| Condition | The agent sees | Question |
|---|---|---|
| A | no spec | baseline drift rate |
| B | `openapi.yaml`, told not to edit it | does the contract help? |
| C | `openapi.yaml`, told it may edit it | does the agent weaken the contract? |

## Design notes

- **Patches are full-file rewrites, not diffs.** Models fail at exact line numbers,
  and a diff that will not apply measures the format rather than the model.
- **One scaffold for every model.** Only the condition-specific paragraph of the
  system prompt varies. Scaffold quality is the largest confound in agent
  benchmarking, so it is held constant and published rather than hidden.
- **The oracle never enters the workspace.** Scoring always runs against the
  pristine spec, never against anything the agent could have touched.
