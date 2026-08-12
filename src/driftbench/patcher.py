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
_DELETE_LINE = re.compile(r"^### DELETE:[ \t]*(?P<path>\S+)[ \t]*$", re.MULTILINE)


class PatchError(Exception):
    """The model's patch could not be safely applied."""


def parse_patch(text: str) -> dict[str, str | None]:
    files: dict[str, str | None] = {}
    for match in _FILE_BLOCK.finditer(text):
        files[match.group("path")] = match.group("body") + "\n"
    for match in _DELETE_LINE.finditer(text):
        files.setdefault(match.group("path"), None)
    return files


def _resolve(workspace: Path, rel: str) -> Path:
    if Path(rel).is_absolute():
        raise PatchError(f"absolute path rejected: {rel}")
    target = (workspace / rel).resolve()
    if not target.is_relative_to(workspace.resolve()):
        raise PatchError(f"path escapes workspace: {rel}")
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
