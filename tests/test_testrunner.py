import sys
from driftbench.testrunner import run_tests, TestResult

PY = sys.executable


def test_passing_command(tmp_path):
    result = run_tests(tmp_path, [PY, "-c", "print('ok')"])
    assert result.passed and result.returncode == 0
    assert "ok" in result.stdout


def test_failing_command(tmp_path):
    result = run_tests(tmp_path, [PY, "-c", "import sys; sys.exit(1)"])
    assert not result.passed and result.returncode == 1


def test_timeout_is_reported_not_raised(tmp_path):
    result = run_tests(tmp_path, [PY, "-c", "import time; time.sleep(5)"], timeout=1)
    assert result.timed_out and not result.passed


def test_runs_in_workspace_cwd(tmp_path):
    (tmp_path / "marker.txt").write_text("here")
    result = run_tests(tmp_path, [PY, "-c", "import os; print(os.listdir('.'))"])
    assert "marker.txt" in result.stdout


def test_env_is_passed_through(tmp_path):
    result = run_tests(tmp_path, [PY, "-c", "import os; print(os.environ['DB_X'])"], env={"DB_X": "42"})
    assert "42" in result.stdout


def test_missing_executable_is_reported_not_raised(tmp_path):
    result = run_tests(tmp_path, ["definitely-not-a-real-binary-xyz"])
    assert not result.passed and result.returncode == -1


def test_feedback_truncates_from_the_tail():
    result = TestResult(passed=False, returncode=1, stdout="A" * 9000, stderr="TAIL", timed_out=False)
    feedback = result.feedback(limit=100)
    assert len(feedback) <= 100
    assert "TAIL" in feedback
