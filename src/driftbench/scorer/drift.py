"""Classify Specmatic failures into the D1-D5 drift taxonomy."""
from __future__ import annotations

import re
from enum import StrEnum

from driftbench.scorer.specmatic import SpecmaticOutcome


class DriftClass(StrEnum):
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"
    D5 = "D5"


DRIFT_LABELS = {
    DriftClass.D1: "undocumented status code",
    DriftClass.D2: "response shape drift",
    DriftClass.D3: "input validation dropped",
    DriftClass.D4: "error-body shape drift",
    DriftClass.D5: "auth regression",
}

_AUTH_NAME = re.compile(r"(invalid[_ -]?token|unauthori[sz]ed|401)", re.I)
_NEGATIVE_NAME = re.compile(r"(NEGATIVE|resiliency|mutat)", re.I)
_ERROR_PATH = re.compile(r"/\d+\b|not[_ ]?found|error", re.I)

_STATUS_MISMATCH = re.compile(
    r"Expected status (?P<expected>\d{3}),? actual was (?P<actual>\d{3})", re.I
)
_STATUS_NOT_IN_SPEC = re.compile(r"response \d{3} not found in spec", re.I)
_SHAPE_PATTERNS = (
    re.compile(r"Key named \"[^\"]+\" was unexpected", re.I),
    re.compile(r"Expected key named \"[^\"]+\" was missing", re.I),
    re.compile(r"Expected (string|number|boolean|integer|object|array), actual was", re.I),
)


def classify_failure(name: str, message: str) -> DriftClass | None:
    status = _STATUS_MISMATCH.search(message)
    if status:
        expected, actual = status.group("expected"), status.group("actual")
        if expected == "401" or _AUTH_NAME.search(name):
            return DriftClass.D5
        # A 4xx-expected/2xx-actual result is dropped validation only when it came
        # from a negative or resiliency scenario. The same message text on an
        # ordinary positive scenario is an undocumented-status result instead.
        if expected.startswith("4") and actual.startswith("2") and _NEGATIVE_NAME.search(name):
            return DriftClass.D3
        return DriftClass.D1

    if _STATUS_NOT_IN_SPEC.search(message):
        return DriftClass.D1

    if any(pattern.search(message) for pattern in _SHAPE_PATTERNS):
        if _ERROR_PATH.search(name) or "error" in message.lower():
            return DriftClass.D4
        return DriftClass.D2

    return None


def classify(outcome: SpecmaticOutcome) -> list[DriftClass]:
    found = {
        cls
        for failure in outcome.failures
        if (cls := classify_failure(failure.get("name", ""), failure.get("message", "")))
        is not None
    }
    return sorted(found, key=lambda c: c.value)
