import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),        # Google API key
    re.compile(r"gsk_[0-9A-Za-z]{20,}"),          # Groq key
    re.compile(r"sk-[0-9A-Za-z]{20,}"),           # OpenAI-style key
]


def test_no_secrets_in_tracked_files():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    offenders = []
    for rel in tracked:
        path = REPO / rel
        if not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(body):
                offenders.append(rel)
    assert offenders == [], f"secret-like strings in tracked files: {offenders}"


def test_gitignore_covers_env_and_keys():
    body = (REPO / ".gitignore").read_text()
    for required in [".env", "*_api_key", "*_credentials", "*.jsonl"]:
        assert required in body, f"{required} missing from .gitignore"


def test_package_imports():
    import driftbench
    assert isinstance(driftbench.__version__, str)
