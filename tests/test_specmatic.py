import json
import sys
from pathlib import Path
import httpx
import pytest
from driftbench.scorer.service_boot import boot_service, free_port, ServiceBootError
from driftbench.scorer.specmatic import parse_ctrf, SpecmaticOutcome

FIXTURES = Path(__file__).parent / "fixtures"


def test_free_port_is_usable():
    port = free_port()
    assert 1024 < port < 65536


def test_boot_service_serves_and_shuts_down(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "srv.py").write_text(
        "import sys\n"
        "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
        "class H(BaseHTTPRequestHandler):\n"
        "    def do_GET(self):\n"
        "        self.send_response(200); self.end_headers(); self.wfile.write(b'{}')\n"
        "    def log_message(self, *a): pass\n"
        "HTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()\n"
    )
    port = free_port()
    with boot_service(workspace, [sys.executable, "srv.py", "{port}"], port) as base_url:
        assert httpx.get(f"{base_url}/healthz").status_code == 200
    with pytest.raises(httpx.ConnectError):
        httpx.get(f"{base_url}/healthz", timeout=1.0)


def test_boot_service_raises_when_health_never_passes(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "dead.py").write_text("import time; time.sleep(30)\n")
    with pytest.raises(ServiceBootError, match="health"):
        with boot_service(workspace, [sys.executable, "dead.py"], free_port(), timeout=2.0):
            pass


def test_parse_ctrf_counts_results():
    report = {"results": {"summary": {"tests": 10, "passed": 8, "failed": 2},
                          "tests": [
                              {"name": "GET /albums -> 200", "status": "passed"},
                              {"name": "GET /albums -> 400", "status": "failed",
                               "message": "Expected status 400, actual was 200"},
                          ]}}
    outcome = parse_ctrf(report)
    assert outcome.ran and (outcome.total, outcome.passed, outcome.failed) == (10, 8, 2)
    assert len(outcome.failures) == 1
    assert "Expected status 400" in outcome.failures[0]["message"]


def test_parse_ctrf_handles_missing_summary():
    outcome = parse_ctrf({"results": {"tests": []}})
    assert outcome.ran and outcome.total == 0


def test_parse_ctrf_rejects_garbage():
    outcome = parse_ctrf({})
    assert not outcome.ran and outcome.error is not None
