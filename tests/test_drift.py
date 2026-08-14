from driftbench.scorer.drift import DriftClass, classify, classify_failure, DRIFT_LABELS
from driftbench.scorer.specmatic import SpecmaticOutcome


def _outcome(failures):
    return SpecmaticOutcome(ran=True, total=10, passed=10 - len(failures),
                            failed=len(failures), failures=failures)


def test_undocumented_status_is_d1():
    assert classify_failure("GET /albums", "Expected status 400, actual was 200") is DriftClass.D1


def test_response_not_in_spec_is_d1():
    assert classify_failure("POST /albums", 'API response 500 not found in spec') is DriftClass.D1


def test_unexpected_key_is_d2():
    assert classify_failure("GET /albums", 'Key named "debug" was unexpected') is DriftClass.D2


def test_missing_key_is_d2():
    assert classify_failure("GET /albums", 'Expected key named "year" was missing') is DriftClass.D2


def test_type_mismatch_is_d2():
    assert classify_failure("GET /albums", 'Expected number, actual was string "1959"') is DriftClass.D2


def test_accepted_invalid_input_is_d3():
    assert classify_failure(
        "POST /albums NEGATIVE", "Expected status 400, actual was 201"
    ) is DriftClass.D3


def test_error_body_shape_is_d4():
    assert classify_failure(
        "GET /albums/999", 'In response body: Expected key named "message" was missing'
    ) is DriftClass.D4


def test_auth_regression_is_d5():
    assert classify_failure(
        "GET /albums (invalid token)", "Expected status 401, actual was 200"
    ) is DriftClass.D5


def test_unrecognised_message_returns_none():
    assert classify_failure("GET /a", "something entirely novel") is None


def test_classify_dedupes_and_sorts():
    result = classify(_outcome([
        {"name": "GET /a", "message": 'Key named "debug" was unexpected'},
        {"name": "GET /b", "message": 'Key named "extra" was unexpected'},
        {"name": "GET /c", "message": "Expected status 400, actual was 200"},
    ]))
    assert result == [DriftClass.D1, DriftClass.D2]


def test_classify_of_clean_run_is_empty():
    assert classify(_outcome([])) == []


def test_every_class_has_a_label():
    assert set(DRIFT_LABELS) == set(DriftClass)
