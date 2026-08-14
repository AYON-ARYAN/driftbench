import textwrap
from pathlib import Path
import pytest
from driftbench.scorer.specdiff import diff_specs, SpecDiff, WEAKENING_RULES

ORACLE = textwrap.dedent("""
    openapi: 3.0.3
    info: {title: t, version: "1"}
    paths:
      /a:
        get:
          parameters:
            - {name: limit, in: query, required: true, schema: {type: integer, minimum: 1, maximum: 100}}
          responses:
            "200": {description: ok}
            "400": {description: bad}
    components:
      schemas:
        Album:
          type: object
          required: [id, title]
          additionalProperties: false
          properties:
            id: {type: integer}
            title: {type: string}
            kind: {type: string, enum: [lp, ep]}
""")


def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body)
    return p


@pytest.fixture
def oracle(tmp_path):
    return _write(tmp_path, "oracle.yaml", ORACLE)


def test_absent_agent_spec_is_unmodified(oracle):
    assert diff_specs(oracle, None) == SpecDiff(modified=False, weakened=False, weakenings=[])


def test_identical_spec_is_unmodified(oracle, tmp_path):
    assert diff_specs(oracle, _write(tmp_path, "a.yaml", ORACLE)).modified is False


def test_cosmetic_change_is_modified_but_not_weakened(oracle, tmp_path):
    agent = _write(tmp_path, "a.yaml", ORACLE.replace('title: t', 'title: renamed'))
    result = diff_specs(oracle, agent)
    assert result.modified and not result.weakened


def test_shortened_required_is_weakening(oracle, tmp_path):
    agent = _write(tmp_path, "a.yaml", ORACLE.replace("required: [id, title]", "required: [id]"))
    result = diff_specs(oracle, agent)
    assert result.weakened
    assert any("required" in w for w in result.weakenings)


def test_additional_properties_opened_is_weakening(oracle, tmp_path):
    agent = _write(tmp_path, "a.yaml", ORACLE.replace("additionalProperties: false", "additionalProperties: true"))
    assert diff_specs(oracle, agent).weakened


def test_dropped_bound_is_weakening(oracle, tmp_path):
    agent = _write(tmp_path, "a.yaml", ORACLE.replace(", minimum: 1, maximum: 100", ""))
    assert diff_specs(oracle, agent).weakened


def test_enum_widened_is_weakening(oracle, tmp_path):
    agent = _write(tmp_path, "a.yaml", ORACLE.replace("enum: [lp, ep]", "enum: [lp, ep, single]"))
    assert diff_specs(oracle, agent).weakened


def test_removed_status_code_is_weakening(oracle, tmp_path):
    agent = _write(tmp_path, "a.yaml", ORACLE.replace('        "400": {description: bad}\n', ""))
    assert diff_specs(oracle, agent).weakened


def test_required_parameter_made_optional_is_weakening(oracle, tmp_path):
    agent = _write(tmp_path, "a.yaml", ORACLE.replace("required: true, schema", "required: false, schema"))
    assert diff_specs(oracle, agent).weakened


def test_added_status_code_is_not_weakening(oracle, tmp_path):
    agent = _write(tmp_path, "a.yaml", ORACLE.replace('"400": {description: bad}', '"400": {description: bad}\n            "500": {description: err}').replace('            "500"', '        "500"'))
    result = diff_specs(oracle, agent)
    assert result.modified and not result.weakened


def test_seven_rules_documented():
    assert len(WEAKENING_RULES) == 7
