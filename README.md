# DriftBench

A benchmark measuring whether AI coding agents preserve API contracts.

Existing benchmarks ask "did the unit tests pass?" DriftBench asks whether the
agent's patch still honors the service's published OpenAPI contract — and
whether an agent given write access to that contract weakens it to accommodate
its own broken code.

**The entire benchmark reproduces on free and local inference.** Rerunning it
costs nothing.

Status: under construction.
