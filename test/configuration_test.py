import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
ADMIN_KEY = "synthetic-key-0123456789abcdef0123456789"


def script(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + content, encoding="utf-8", newline="\n")
    path.chmod(0o755)
    return path


def environment(tmp_path):
    tools = tmp_path / "mock tools"
    for name in ("curl", "java", "jq"):
        script(tools / name, '[[ "$1" != --help ]] || exit 0\nexit 88\n')
    # Set PATH inside Bash as well: Git Bash can prepend its own tools on startup.
    startup = script(tmp_path / "bash startup.sh", 'export PATH="$(cd -- "$OPS_TEST_TOOLS" && pwd):$PATH"\n')
    jdk = tmp_path / "selected JDK with spaces"
    script(jdk / "bin/java", 'echo selected-jdk\n')
    env = dict(os.environ, EVS_OPS_HOME=str(REPO), OPS_STATE_DIR=str(tmp_path / "state"),
               OPS_PYTHON=sys.executable, OPS_BASH=os.environ.get("OPS_BASH", "bash"),
               OPS_TEST_TOOLS=str(tools), BASH_ENV=str(startup), JAVA_HOME=str(jdk),
               GRAPH_DB_HOST="configuration-only.invalid", GRAPH_DB_PORT="1",
               GRAPH_DB_USERNAME="synthetic", GRAPH_DB_PASSWORD="synthetic",
               ES_SCHEME="http", ES_HOST="configuration-only.invalid", ES_PORT="1")
    env.pop("EVS_OPS_LOCK_TOKEN", None)
    env.pop("OPS_CONFIG_ENV_FILE", None)
    return env, jdk


@pytest.mark.parametrize("from_config", [False, True])
def test_java_home_selects_jdk_before_path_fallback(tmp_path, from_config):
    env, jdk = environment(tmp_path)
    app_home = tmp_path / "configuration home with spaces"
    config = app_home / "config/setenv.sh"
    config.parent.mkdir(parents=True)
    config.write_text("export JAVA_HOME=" + shlex.quote(str(jdk if from_config else tmp_path / "unused JDK")) + "\n",
                      encoding="utf-8", newline="\n")
    env["APP_HOME"] = str(app_home)
    if from_config:
        env.pop("JAVA_HOME")
    probe = script(tmp_path / "probe.sh",
                   'source "$EVS_OPS_HOME/bin/ops-common.sh"\nops_lock "$@"\njava -version\n')
    result = subprocess.run([env["OPS_BASH"], str(probe), *([] if from_config else ["--noconfig"])],
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "selected-jdk"


@pytest.mark.parametrize("name,args,parent_layout", [
    ("audit.sh", ["all"], False),
    ("list.sh", ["--quiet"], False),
    ("list.sh", ["--quiet"], True),
    ("reindex.sh", ["--terminology", "ncit"], False),
    ("reindex.sh", ["--terminology", "ncit"], True),
    ("report.sh", ["--list"], False),
    ("report.sh", ["--list"], True),
    ("ncim-part.sh", ["missing-rrf-directory"], False),
    ("ncim-part.sh", ["missing-rrf-directory"], True),
])
def test_scripts_read_spaced_config_and_honor_noconfig(tmp_path, name, args, parent_layout):
    env, jdk = environment(tmp_path)
    # Fail closed if the workflow reaches Java; this test never indexes anything.
    script(jdk / "bin/java", "exit 88\n")
    app_home = tmp_path / "configuration home with spaces"
    config = app_home / ("evsrestapi/config/setenv.sh" if parent_layout else "config/setenv.sh")
    config.parent.mkdir(parents=True)
    marker = tmp_path / "configuration-read"
    config.write_text('printf loaded > "$OPS_TEST_MARKER"\n', encoding="utf-8", newline="\n")
    env.update(APP_HOME=str(app_home), APP_NAME="evsrestapi" if parent_layout else "",
               OPS_TEST_MARKER=str(marker))
    for no_config in (False, True):
        marker.unlink(missing_ok=True)
        result = subprocess.run([env["OPS_BASH"], str(REPO / "bin" / name),
                                 *(["--noconfig"] if no_config else []), *args],
                                cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
        assert marker.exists() == (not no_config), (result.stdout, result.stderr)
        assert not re.search(r"line \d+: .*: (No such file|[Ii]s a directory)", result.stderr), result.stderr


def installation(tmp_path, names):
    root = tmp_path / "operations with spaces"
    for name in {"ops-common.sh", "process_supervisor.py", "process_exec.sh", *names}:
        target = root / "bin" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "bin" / name, target)
    return root


def record_arguments(path, exit_code):
    program = (
        "import json,os,sys; from pathlib import Path; "
        "Path(os.environ['OPS_TEST_ARGS']).write_text(json.dumps({"
        "'args':sys.argv[1:],'cwd':os.getcwd()}),encoding='utf-8')"
    )
    script(path, '"$OPS_PYTHON" -c ' + shlex.quote(program) + ' "$@"\nexit ' + str(exit_code) + '\n')


@pytest.mark.parametrize("parent_layout", [False, True])
def test_config_selects_lock_directory_before_supervisor(tmp_path, parent_layout):
    env, _ = environment(tmp_path)
    root = installation(tmp_path, [])
    app = tmp_path / "configuration home"
    config = app / ("evsrestapi/config/setenv.sh" if parent_layout else "config/setenv.sh")
    config.parent.mkdir(parents=True)
    state = tmp_path / "shared state"
    reads = tmp_path / "config-reads"
    config.write_text("export OPS_STATE_DIR=" + shlex.quote(state.as_posix()) +
                      '\nprintf x >> "$OPS_TEST_READS"\n', encoding="utf-8")
    env.pop("OPS_STATE_DIR")
    env.update(EVS_OPS_HOME=root.as_posix(), APP_HOME=app.as_posix(),
               APP_NAME="evsrestapi", OPS_TEST_READS=str(reads))
    probe = script(tmp_path / "probe.sh", 'source "$EVS_OPS_HOME/bin/ops-common.sh"\n'
                   'ops_lock "$@"\nops_load_config 1 || exit 1\nops_load_config 1 || exit 1\n'
                   'printf "%s\n" "$OPS_STATE_DIR"\n')
    result = subprocess.run([env["OPS_BASH"], str(probe)], env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == state.as_posix()
    assert (state / "mutation.lock").exists()
    assert not (root / "var").exists()
    # One read in each shell: the initial caller and the supervised worker.
    assert reads.read_text(encoding="utf-8") == "xx"


@pytest.mark.parametrize("parent_layout", [False, True])
def test_admin_launcher_uses_same_config_resolver(tmp_path, parent_layout):
    env, jdk = environment(tmp_path)
    root = installation(tmp_path, ["evsrestapi-operations"])
    jar = root / "lib/evsrestapi-operations.jar"
    jar.parent.mkdir()
    jar.write_bytes(b"synthetic")
    script(jdk / "bin/java", 'printf "%s|%s|%s\n" "$OPS_STATE_DIR" "$ADMIN_KEY" "$ADMIN_BIND"\n')
    app = tmp_path / "configuration home"
    config = app / ("evsrestapi/config/setenv.sh" if parent_layout else "config/setenv.sh")
    config.parent.mkdir(parents=True)
    state = tmp_path / "shared state"
    config.write_text("export OPS_STATE_DIR=" + shlex.quote(state.as_posix()) +
                      "\nexport ADMIN_KEY=" + ADMIN_KEY + "\n", encoding="utf-8")
    env.pop("OPS_STATE_DIR")
    env.pop("ADMIN_KEY", None)
    # An empty bind address must fall back to loopback, not every interface.
    env.update(EVS_OPS_HOME=root.as_posix(), APP_HOME=app.as_posix(), APP_NAME="evsrestapi",
               ADMIN_BIND="")
    result = subprocess.run([env["OPS_BASH"], str(root / "bin/evsrestapi-operations"), "foreground"],
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == state.as_posix() + "|" + ADMIN_KEY + "|127.0.0.1"
    assert (state / "logs").is_dir()


def test_admin_launcher_rejects_short_key(tmp_path):
    env, jdk = environment(tmp_path)
    root = installation(tmp_path, ["evsrestapi-operations"])
    jar = root / "lib/evsrestapi-operations.jar"
    jar.parent.mkdir()
    jar.write_bytes(b"synthetic")
    script(jdk / "bin/java", "exit 88\n")
    env.update(EVS_OPS_HOME=root.as_posix(), APP_HOME=(tmp_path / "no config").as_posix(),
               ADMIN_KEY="too-short")
    result = subprocess.run([env["OPS_BASH"], str(root / "bin/evsrestapi-operations"), "foreground"],
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert "at least 32 characters" in result.stderr


@pytest.mark.parametrize("no_config", [False, True])
def test_scripts_never_keep_admin_key(tmp_path, no_config):
    env, _ = environment(tmp_path)
    app = tmp_path / "configuration home"
    config = app / "config/setenv.sh"
    config.parent.mkdir(parents=True)
    config.write_text("export ADMIN_KEY=from-setenv\n", encoding="utf-8", newline="\n")
    env.update(APP_HOME=str(app), ADMIN_KEY="from-caller")
    probe = script(tmp_path / "probe.sh", 'source "$EVS_OPS_HOME/bin/ops-common.sh"\nops_lock "$@"\n'
                   'printf "%s\n" "${ADMIN_KEY-unset}"\n')
    result = subprocess.run([env["OPS_BASH"], str(probe), *(["--noconfig"] if no_config else [])],
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "unset"


def test_patch_version_cannot_leave_patches_directory(tmp_path):
    env, _ = environment(tmp_path)
    root = installation(tmp_path, ["run_command.sh"])
    script(root / "bin/outside/run.sh", "echo escaped\n")
    env["EVS_OPS_HOME"] = root.as_posix()
    result = subprocess.run([env["OPS_BASH"], str(root / "bin/run_command.sh"), "--noconfig",
                             "patch", "../outside"],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert "escaped" not in result.stdout
    assert "Invalid patch version" in result.stdout


def test_metadata_arguments_cannot_add_curl_options_or_url_segments(tmp_path):
    env, _ = environment(tmp_path)
    root = installation(tmp_path, ["metadata.sh"])
    calls = tmp_path / "curl-calls.jsonl"
    program = ("import json,os,sys; open(os.environ['OPS_TEST_ARGS'],'a',encoding='utf-8')"
               ".write(json.dumps(sys.argv[1:])+'\\n')")
    script(Path(env["OPS_TEST_TOOLS"]) / "curl", '"$OPS_PYTHON" -c ' + shlex.quote(program) + ' "$@"\n')
    env.update(EVS_OPS_HOME=root.as_posix(), OPS_TEST_ARGS=str(calls))

    def metadata(*args):
        return subprocess.run([env["OPS_BASH"], str(root / "bin/metadata.sh"), "--noconfig", *args],
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)

    result = metadata("ncit/../../other", "2106e", "https://example.org/ncit.json")
    assert result.returncode == 1 and "invalid terminology or version" in result.stdout
    assert not calls.exists()
    uri = "https://example.org/a.json -o " + (tmp_path / "written").as_posix() + " https://example.org/b"
    metadata("ncit", "2106e", uri)
    download = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()][-1]
    assert download[-1] == uri and len(download) == 4
    assert not (tmp_path / "written").exists()


@pytest.mark.parametrize("failure", ["missing-jar", "bad-jvm", "none"])
def test_devreset_preflight_happens_before_data_checks_or_backend_calls(tmp_path, failure):
    env, jdk = environment(tmp_path)
    root = installation(tmp_path, ["devreset.sh", "reindex.sh"])
    jar = tmp_path / "loader.jar"
    if failure != "missing-jar":
        jar.write_bytes(b"synthetic")
    calls = tmp_path / "java-arguments.json"
    record_arguments(jdk / "bin/java", 1 if failure == "bad-jvm" else 0)
    backend_call = tmp_path / "backend-called"
    script(Path(env["OPS_TEST_TOOLS"]) / "curl", 'touch "$OPS_TEST_BACKEND_CALL"\nexit 88\n')
    env.update(EVS_OPS_HOME=root.as_posix(), APP_HOME=(tmp_path / "no config").as_posix(),
               EVS_LOADER_JAR=jar.as_posix(), OPS_TEST_ARGS=str(calls), OPS_TEST_BACKEND_CALL=str(backend_call))
    result = subprocess.run([env["OPS_BASH"], str(root / "bin/devreset.sh"), str(tmp_path / "missing inputs")],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert not backend_call.exists()
    if failure == "missing-jar":
        assert "loader JAR not found" in result.stderr
        assert not calls.exists()
    else:
        assert json.loads(calls.read_text(encoding="utf-8"))["args"] == ["-jar", jar.as_posix(), "--help"]
        if failure == "bad-jvm":
            assert "loader preflight failed" in result.stderr
        else:
            assert "unexpectedly missing NCIM" in result.stdout
