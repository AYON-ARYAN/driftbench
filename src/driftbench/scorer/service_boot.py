"""Boot a patched service on a free port, wait for health, guarantee teardown."""
from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx


class ServiceBootError(Exception):
    """The service did not become healthy."""


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def boot_service(
    workspace: Path,
    command_template: list[str],
    port: int,
    health_path: str = "/healthz",
    timeout: float = 30.0,
) -> Iterator[str]:
    command = [part.format(port=port) for part in command_template]
    base_url = f"http://127.0.0.1:{port}"
    env = {**os.environ, "DRIFTBENCH_PORT": str(port), "PYTHONUNBUFFERED": "1"}

    proc = subprocess.Popen(
        command, cwd=str(workspace), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise ServiceBootError(
                    f"service exited with {proc.returncode} before health check passed"
                )
            try:
                if httpx.get(f"{base_url}{health_path}", timeout=1.0).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.25)
        else:
            raise ServiceBootError(f"health check never passed within {timeout}s")

        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
