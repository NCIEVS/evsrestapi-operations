import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

import pytest


SUPERVISOR = Path(__file__).resolve().parents[1] / "bin" / "process_supervisor.py"


@pytest.mark.parametrize("selection", [None, "bash"])
def test_shell_bootstrap_pins_the_invoking_bash(tmp_path, selection):
    bash = os.environ.get("OPS_BASH", "bash")
    env = dict(os.environ, EVS_OPS_HOME=SUPERVISOR.parents[1].as_posix())
    if selection is None:
        env.pop("OPS_BASH", None)
    else:
        env["OPS_BASH"] = selection
    probe = 'source "$EVS_OPS_HOME/bin/ops-common.sh"\nprintf "%s" "$OPS_BASH"\n'
    result = subprocess.run([bash, "-c", probe], env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    selected = Path(result.stdout)
    assert selected.is_absolute(), result.stdout
    if os.name == "nt":
        assert "\\" not in result.stdout
    assert selected.is_file(), result.stdout
    checked = subprocess.run([str(selected), "-c", 'printf selected-bash'],
                             capture_output=True, text=True, timeout=15)
    assert checked.returncode == 0 and checked.stdout == "selected-bash", checked.stderr


@pytest.mark.parametrize("selection", [None, "bash"])
def test_devreset_bootstrap_reaches_usage_without_wsl_or_backends(tmp_path, selection):
    bash = os.environ.get("OPS_BASH", "bash")
    env = dict(os.environ, EVS_OPS_HOME=SUPERVISOR.parents[1].as_posix(),
               OPS_PYTHON=sys.executable, OPS_STATE_DIR=str(tmp_path / "state"),
               APP_HOME=str(tmp_path / "empty config"), PYTHONUTF8="1")
    env.pop("EVS_OPS_LOCK_TOKEN", None)
    if selection is None:
        env.pop("OPS_BASH", None)
    else:
        env["OPS_BASH"] = selection
    # No data-directory argument: devreset must stop at usage before any mutation.
    result = subprocess.run([bash, SUPERVISOR.with_name("devreset.sh").as_posix()],
                            env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Usage:" in result.stdout
    assert "wsl:" not in result.stderr.lower()
    assert "No such file or directory" not in result.stderr


def test_command_environment_preserves_arguments_and_is_not_inherited(tmp_path):
    arguments = ["single'quote", 'double"quote', "", "line\nbreak", "é漢🚀"]
    command = [sys.executable, "-c",
               "import json,os,sys; assert not any(k.startswith('EVS_OPS_COMMAND_ARG') for k in os.environ); print(json.dumps(sys.argv[1:]))",
               *arguments]
    env = dict(os.environ, OPS_STATE_DIR=str(tmp_path), PYTHONUTF8="1", EVS_OPS_COMMAND_ARGC=str(len(command)))
    env.update({f"EVS_OPS_COMMAND_ARG_{i}": arg for i, arg in enumerate(command)})
    result = subprocess.run([sys.executable, str(SUPERVISOR), "--command-env"], env=env,
                            capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == arguments


def test_bash_arguments_survive_supervisor_and_nested_scripts(tmp_path):
    script = tmp_path / "arguments with spaces.sh"
    script.write_text('printf \'%s\\0\' "$@"\n', encoding="utf-8", newline="\n")
    arguments = ["space value", "single'quote", 'double"quote', "$(literal)", "semi;colon", "", "Unicode é漢🚀"]
    env = dict(os.environ, OPS_STATE_DIR=str(tmp_path / "state"), PYTHONUTF8="1")
    bash = os.environ.get("OPS_BASH", "bash")
    result = subprocess.run([sys.executable, str(SUPERVISOR), "--", bash, str(script), *arguments],
                            env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split("\0") == arguments + [""]
    script.write_text('source "$EVS_OPS_HOME/bin/ops-common.sh"\nops_lock "$@"\nprintf \'%s\\0\' "$@"\n',
                      encoding="utf-8", newline="\n")
    env.update(EVS_OPS_HOME=str(SUPERVISOR.parents[1]), OPS_PYTHON=sys.executable, OPS_BASH=bash,
               APP_HOME=str(tmp_path / "empty config"))
    env.pop("EVS_OPS_LOCK_TOKEN", None)
    result = subprocess.run([bash, "-c", "exec bash " + shlex.join([str(script), *arguments])],
                            env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split("\0") == arguments + [""]


def wait_ready(path, process):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.exists():
            return json.loads(path.read_text())
        if process.poll() is not None:
            break
        time.sleep(0.02)
    raise AssertionError("supervisor did not acknowledge startup")


def test_lock_contention_and_release(tmp_path):
    env = dict(os.environ, OPS_STATE_DIR=str(tmp_path))
    ready = tmp_path / "ready.json"
    process = subprocess.Popen([sys.executable, str(SUPERVISOR), "--ready-file", str(ready), "--", sys.executable, "-c", "import time; time.sleep(2)"], env=env)
    try:
        assert wait_ready(ready, process)["state"] == "RUNNING"
        other = subprocess.run([sys.executable, str(SUPERVISOR), "--", sys.executable, "-c", "raise SystemExit(0)"], env=env, capture_output=True)
        assert other.returncode == 75
        process.wait(timeout=5)
        result = subprocess.run([sys.executable, str(SUPERVISOR), "--", sys.executable, "-c", "raise SystemExit(7)"], env=env, capture_output=True)
        assert result.returncode == 7
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def test_nested_lock_and_read_only(tmp_path):
    env = dict(os.environ, OPS_STATE_DIR=str(tmp_path))
    script = tmp_path / "nested.py"
    script.write_text("import os, subprocess, sys\nsubprocess.run([sys.executable, sys.argv[1], '--check-lock'], check=True)\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(SUPERVISOR), "--", sys.executable, str(script), str(SUPERVISOR)], env=env, capture_output=True)
    assert result.returncode == 0, result.stderr
    env["EVS_OPS_LOCK_TOKEN"] = "not-a-real-lock"
    result = subprocess.run([sys.executable, str(SUPERVISOR), "--check-lock"], env=env)
    assert result.returncode == 1


def test_read_only_can_run_with_a_mutation(tmp_path):
    env = dict(os.environ, OPS_STATE_DIR=str(tmp_path))
    ready = tmp_path / "ready.json"
    process = subprocess.Popen([sys.executable, str(SUPERVISOR), "--ready-file", str(ready), "--", sys.executable, "-c", "import time; time.sleep(1)"], env=env)
    try:
        wait_ready(ready, process)
        result = subprocess.run([sys.executable, str(SUPERVISOR), "--read-only", "--", sys.executable, "-c", "raise SystemExit(0)"], env=env)
        assert result.returncode == 0
    finally:
        process.wait(timeout=5)


@pytest.mark.skipif(os.name == "nt", reason="Unix process groups")
def test_shutdown_kills_descendants_after_worker_exits(tmp_path):
    env = dict(os.environ, OPS_STATE_DIR=str(tmp_path))
    descendant = tmp_path / "descendant.pid"
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import pathlib, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid))\n"
        "time.sleep(60)\n", encoding="utf-8")
    process = subprocess.Popen([sys.executable, str(SUPERVISOR), "--", sys.executable, str(worker), str(descendant)], env=env)
    pid = None
    try:
        deadline = time.monotonic() + 5
        while not descendant.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert descendant.exists()
        pid = int(descendant.read_text())
        time.sleep(0.2)  # Let the descendant install its signal handler.
        process.terminate()
        assert process.wait(timeout=15) == 130
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            status = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True)
            if status.returncode != 0 or status.stdout.strip().startswith("Z"):
                break
            time.sleep(0.05)
        else:
            pytest.fail("descendant survived supervisor shutdown after its worker exited")
        assert not (tmp_path / "mutation-owner.json").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if pid is not None:
            import signal

            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
