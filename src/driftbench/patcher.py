"""Parse a model's full-file-rewrite output and apply it to a workspace."""
from __future__ import annotations

import re
from pathlib import Path

PATCH_FORMAT_INSTRUCTIONS = """\
Return every file you changed in full, using exactly this format:

### FILE: relative/path/to/file.py
```python
<the complete new contents of the file>
```

Rules:
- Give the COMPLETE file contents, not a diff and not an excerpt.
- Paths are relative to the repository root. Never absolute, never containing "..".
- To delete a file, write a single line: ### DELETE: relative/path/to/file.py
- Include no file you did not change.
"""

_FILE_BLOCK = re.compile(
    r"^### FILE:[ \t]*(?P<path>\S+)[ \t]*\r?\n"
    r"```[A-Za-z0-9_+-]*[ \t]*\r?\n"
    r"(?P<body>.*?)"
    r"\r?\n```[ \t]*(?:\r?\n|$)",
    re.MULTILINE | re.DOTALL,
)
_DELETE_LINE = re.compile(r"^### DELETE:[ \t]*(?P<path>\S+)[ \t]*\r?$", re.MULTILINE)

_MALFORMED_FILE_HEADER = re.compile(r"^### FILE:([^\r\n]*)\r?$", re.MULTILINE)
_MALFORMED_DELETE_HEADER = re.compile(r"^### DELETE:([^\r\n]*)\r?$", re.MULTILINE)


class PatchError(Exception):
    """The model's patch could not be safely applied."""


def parse_patch(text: str) -> dict[str, str | None]:
    files: dict[str, str | None] = {}
    for match in _FILE_BLOCK.finditer(text):
        files[match.group("path")] = match.group("body") + "\n"
    for match in _DELETE_LINE.finditer(text):
        files.setdefault(match.group("path"), None)
    return files


def _unmatched_headers(pattern: re.Pattern[str], text: str, parsed_paths: set[str]) -> list[str]:
    """Find header lines matching `pattern` that don't correspond to a parsed path.

    A header line is malformed if it has no clean `\\S+` path token (empty,
    whitespace-only, or a path followed by trailing text such as a comment
    or a second token), or if its path token was never accepted by the
    well-formed block/line regex (e.g. an unterminated fence).
    """
    malformed = []
    for match in pattern.finditer(text):
        header_content = match.group(1).strip()
        path_match = re.match(r"^(\S+)", header_content)
        if path_match is None:
            # No non-whitespace path token at all (empty or whitespace-only).
            malformed.append(match.group(0))
            continue
        path = path_match.group(1)
        has_trailing_text = len(header_content) > len(path)
        if path not in parsed_paths or has_trailing_text:
            malformed.append(match.group(0))
    return malformed


def malformed_headers(text: str) -> list[str]:
    """Return raw header lines that look like ### FILE: or ### DELETE: but don't parse.

    This detects partial responses where a model started an instruction but
    did not properly format it or left it incomplete (missing closing fence,
    empty path, extra tokens after the path, etc). Returns the raw header
    line text for each such malformed directive. Well-formed headers of
    either line ending never appear here.
    """
    parsed_files = {m.group("path") for m in _FILE_BLOCK.finditer(text)}
    parsed_deletes = {m.group("path") for m in _DELETE_LINE.finditer(text)}

    return _unmatched_headers(_MALFORMED_FILE_HEADER, text, parsed_files) + _unmatched_headers(
        _MALFORMED_DELETE_HEADER, text, parsed_deletes
    )


def _resolve(workspace: Path, rel: str) -> Path:
    if not rel or not rel.strip():
        raise PatchError(f"empty path rejected: {rel!r}")
    if Path(rel).is_absolute():
        raise PatchError(f"absolute path rejected: {rel}")
    target = (workspace / rel).resolve()
    workspace_resolved = workspace.resolve()
    if not target.is_relative_to(workspace_resolved):
        raise PatchError(f"path escapes workspace: {rel}")
    if target == workspace_resolved:
        raise PatchError(f"path is workspace root: {rel}")
    return target


def apply_patch(workspace: Path, files: dict[str, str | None]) -> list[str]:
    workspace = Path(workspace)
    changed: list[str] = []

    resolved = {rel: _resolve(workspace, rel) for rel in files}

    for rel, target in resolved.items():
        body = files[rel]
        if body is None:
            if target.exists():
                target.unlink()
                changed.append(rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        changed.append(rel)

    return changed
