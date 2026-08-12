import pytest
from driftbench.patcher import parse_patch, apply_patch, PatchError, PATCH_FORMAT_INSTRUCTIONS


def test_parses_single_file():
    text = "chatter before\n### FILE: app.py\n```python\nprint('hi')\n```\ntrailing\n"
    assert parse_patch(text) == {"app.py": "print('hi')\n"}


def test_parses_multiple_files():
    text = (
        "### FILE: a.py\n```python\nA = 1\n```\n"
        "### FILE: sub/b.py\n```\nB = 2\n```\n"
    )
    assert parse_patch(text) == {"a.py": "A = 1\n", "sub/b.py": "B = 2\n"}


def test_parses_deletion():
    assert parse_patch("### DELETE: old.py\n") == {"old.py": None}


def test_no_blocks_returns_empty():
    assert parse_patch("I could not complete this task.") == {}


def test_backticks_inside_body_survive():
    text = "### FILE: d.py\n```python\ns = 'use ``x`` here'\n```\n"
    assert "``x``" in parse_patch(text)["d.py"]


def test_apply_writes_and_creates_dirs(tmp_path):
    changed = apply_patch(tmp_path, {"pkg/mod.py": "X = 1\n"})
    assert (tmp_path / "pkg" / "mod.py").read_text() == "X = 1\n"
    assert changed == ["pkg/mod.py"]


def test_apply_deletes(tmp_path):
    (tmp_path / "gone.py").write_text("x")
    apply_patch(tmp_path, {"gone.py": None})
    assert not (tmp_path / "gone.py").exists()


def test_apply_deleting_missing_file_is_not_an_error(tmp_path):
    assert apply_patch(tmp_path, {"never.py": None}) == []


def test_path_traversal_rejected(tmp_path):
    with pytest.raises(PatchError, match="escapes workspace"):
        apply_patch(tmp_path, {"../evil.py": "x"})


def test_absolute_path_rejected(tmp_path):
    with pytest.raises(PatchError, match="absolute"):
        apply_patch(tmp_path, {"/etc/passwd": "x"})


def test_format_instructions_show_both_markers():
    assert "### FILE:" in PATCH_FORMAT_INSTRUCTIONS
    assert "### DELETE:" in PATCH_FORMAT_INSTRUCTIONS
