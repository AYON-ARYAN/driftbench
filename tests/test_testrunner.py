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


def test_workspace_as_file_is_reported_not_raised(tmp_path):
    # workspace pointing to a file (not a directory) should not raise NotADirectoryError
    workspace_file = tmp_path / "workspace.txt"
    workspace_file.write_text("this is a file")
    result = run_tests(workspace_file, [PY, "-c", "print('ok')"])
    assert not result.passed and result.returncode == -1


def test_empty_command_list_is_reported_not_raised(tmp_path):
    # empty command list should not raise IndexError
    result = run_tests(tmp_path, [])
    assert not result.passed and result.returncode == -1


def test_timeout_with_stdout_is_str_not_bytes(tmp_path):
    # command that writes to stdout then times out: stdout should be str, not bytes
    # use -u flag to make output unbuffered so it's captured before timeout
    result = run_tests(
        tmp_path,
        [PY, "-u", "-c", "print('hello-before-timeout'); import time; time.sleep(5)"],
        timeout=1,
    )
    assert result.timed_out and not result.passed
    assert isinstance(result.stdout, str)
    assert "hello-before-timeout" in result.stdout


def test_feedback_after_timeout_contains_real_text(tmp_path):
    # feedback() should contain the actual written text, not a bytes-repr
    # use -u flag to make output unbuffered so it's captured before timeout
    result = run_tests(
        tmp_path,
        [PY, "-u", "-c", "print('test-output'); import time; time.sleep(5)"],
        timeout=1,
    )
    feedback = result.feedback()
    assert "test-output" in feedback
    assert "b'" not in feedback  # should not contain bytes-repr
