"""Exercise an extracted distribution with synthetic commands and no backend access.

Run explicitly after packaging: python test/distribution_smoke.py build/evsrestapi-operations-2.6.0.zip
"""

import argparse
import io
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile


def wait_for(check, description, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {description}")


def alive(pid):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True)
    return result.returncode == 0 and not result.stdout.strip().startswith("Z")


def run_smoke(archive, temporary):
    installation = temporary / "operations installation"
    installation.mkdir()
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        assert any(name.startswith("data/mappings/") for name in names)
        assert "config/setenv.sh" not in names
        assert not any(name.startswith(("var/", "build/")) or "/work_" in name for name in names)
        for name in ("bin/evsrestapi-operations", "bin/ops-common.sh", "bin/process_supervisor.py", "bin/process_exec.sh"):
            entry = zipped.getinfo(name)
            assert entry.create_system == 3 and (entry.external_attr >> 16) & 0o111
        for name, own_config, forbidden_config, forbidden_classes in (
            ("evsrestapi-operations.jar", "application.properties", "loader.properties",
             ("gov/nih/nci/evs/api/", "gov/nih/nci/evs/operations/loader/")),
            ("evsrestapi-loader.jar", "loader.properties", "application.properties",
             ("gov/nih/nci/evs/operations/admin/",)),
        ):
            with zipfile.ZipFile(io.BytesIO(zipped.read("lib/" + name))) as executable:
                entries = executable.namelist()
                assert "BOOT-INF/classes/" + own_config in entries, name
                assert "BOOT-INF/classes/" + forbidden_config not in entries, name
                assert not any(entry.startswith("BOOT-INF/classes/" + prefix)
                               for entry in entries for prefix in forbidden_classes), name
                if name == "evsrestapi-operations.jar":
                    assert not any(entry.startswith(("BOOT-INF/classes/cuis-", "BOOT-INF/classes/cumulative_history_"))
                                   for entry in entries), name
        if os.name == "nt":
            zipped.extractall(installation)
        else:
            subprocess.run(["unzip", "-q", str(archive), "-d", str(installation)], check=True)

    # Replace commands only inside the temporary extracted installation.
    # init.sh stands in for any data-changing command; list.sh for a read-only one.
    (installation / "bin/list.sh").write_text(
        '#!/bin/bash\nprintf "stdout:%s\\n" "$1"\necho stderr >&2\n'
        '[[ "$1" != fail ]] || exit 7\n', encoding="utf-8", newline="\n")
    (installation / "bin/init.sh").write_text(
        '#!/bin/bash\nsource "$(dirname "$0")/ops-common.sh"\nops_lock "$@"\n'
        'echo mutation-started\n'
        '"$OPS_PYTHON" -c \'import os, pathlib, sys, time; '
        'pathlib.Path(os.environ["OPS_STATE_DIR"], "smoke-worker.pid").write_text(str(os.getpid())); '
        'time.sleep(float(sys.argv[1]))\' "${1:-3}"\n'
        'echo mutation-finished\n', encoding="utf-8", newline="\n")
    for name in ("list.sh", "init.sh"):
        (installation / "bin" / name).chmod(0o755)

    java = str(Path(os.environ["JAVA_HOME"]) / "bin" / ("java.exe" if os.name == "nt" else "java")) if os.environ.get("JAVA_HOME") else shutil.which("java")
    bash = os.environ.get("OPS_BASH", shutil.which("bash"))
    assert java and bash, "Java 25 and Bash are required"
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    key = "distribution-smoke-private-key"
    env = dict(os.environ, ADMIN_KEY=key, ADMIN_PORT=str(port), ADMIN_BIND="127.0.0.1",
               EVS_OPS_HOME=str(installation), APP_HOME=str(temporary / "empty configuration"),
               OPS_STATE_DIR=str(temporary / "process state"), OPS_PYTHON=sys.executable,
               OPS_BASH=bash, OPS_WAIT_SECONDS="1", PYTHONUTF8="1",
               ES_HOST="127.0.0.1", ES_PORT="1", GRAPH_DB_HOST="127.0.0.1", GRAPH_DB_PORT="1")
    env.pop("EVS_OPS_LOCK_TOKEN", None)
    base = f"http://127.0.0.1:{port}"
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    log = (temporary / "service.log").open("w", encoding="utf-8")
    process = None
    supervisors = set()
    lifecycle_started = False
    lifecycle = [bash, str(installation / "bin/evsrestapi-operations")]

    def call(path, body=None, authenticated=True, admin_prefix="/admin", **query):
        parameters = dict(query)
        if authenticated:
            parameters["apiKey"] = key
        request = urllib.request.Request(base + admin_prefix + path + "?" + urllib.parse.urlencode(parameters),
                                         data=None if body is None else json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
        try:
            response = http.open(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            output = response.read().decode("utf-8")
            return response.status, json.loads(output) if "application/json" in response.headers.get("Content-Type", "") else output

    def ready():
        try:
            return call("/commands")[0] == 200
        except (urllib.error.URLError, ConnectionError):
            return False

    def start():
        nonlocal process
        process = subprocess.Popen([java, "-Xmx256m", "-jar", str(installation / "lib/evsrestapi-operations.jar")],
                                   cwd=temporary, env=env, stdout=log, stderr=subprocess.STDOUT)
        wait_for(ready, "backend-independent API startup")

    def stop():
        nonlocal process
        if process is not None:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=30)
            process = None

    def succeeded(job):
        return call("/processes/" + job["id"])[1]["state"] == "SUCCEEDED"

    def worker_pid():
        marker = Path(env["OPS_STATE_DIR"]) / "smoke-worker.pid"
        wait_for(marker.exists, "synthetic worker startup")
        return int(marker.read_text())

    try:
        start()
        assert call("/commands", authenticated=False)[0] == 401
        assert call("/processes", authenticated=False)[0] == 401
        assert call("/exec", {"command": "list", "args": []}, authenticated=False)[0] == 401
        assert call("/exec", {"command": "unknown", "args": []})[0] == 400
        status, job = call("/exec", {"command": "list", "args": ["literal $(no-shell) space"]}, background="false")
        assert status == 200 and job["state"] == "SUCCEEDED", job
        assert "stdout:literal $(no-shell) space" in job["output"] and "stderr" in job["output"]
        identifier = job["id"]
        for suffix in ("", "/log"):
            assert call("/processes/" + identifier + suffix, authenticated=False)[0] == 401
        for prefix in ("/%61dmin", "/a%64min", "/ad%6din"):
            for path in ("/commands", "/processes", "/processes/" + identifier,
                         "/processes/" + identifier + "/log"):
                assert call(path, authenticated=False, admin_prefix=prefix)[0] == 401
                assert call(path, authenticated=False, admin_prefix=prefix, apiKey="wrong")[0] == 401
                assert call(path, admin_prefix=prefix)[0] == 200
            request = {"command": "unknown", "args": []}
            assert call("/exec", request, authenticated=False, admin_prefix=prefix)[0] == 401
            assert call("/exec", request, authenticated=False, admin_prefix=prefix, apiKey="wrong")[0] == 401
            assert call("/exec", request, admin_prefix=prefix)[0] == 400
        assert "stdout:literal" in call("/processes/" + identifier + "/log", full="true")[1]
        chunk = call("/processes/" + identifier + "/log", offset=0, limit=16)[1]
        assert chunk["nextOffset"] == 16
        failed = call("/exec", {"command": "list", "args": ["fail"]}, background="false")[1]
        assert failed["state"] == "FAILED" and failed["exitCode"] == 7, failed

        status, job = call("/exec", {"command": "init", "args": ["3"]}, background="false")
        assert status == 202, job
        assert call("/exec", {"command": "init", "args": []})[0] == 409
        direct = subprocess.run([bash, str(installation / "bin/init.sh")], env=env, cwd=temporary,
                                capture_output=True, text=True, timeout=15)
        assert direct.returncode == 75, (direct.returncode, direct.stdout, direct.stderr)
        wait_for(lambda: succeeded(job), "asynchronous mutation completion")
        stop()
        start()
        assert call("/processes/" + identifier)[1]["state"] == "SUCCEEDED"

        if os.name != "nt":
            # Orderly JVM shutdown must stop the worker tree and retain interrupted history.
            (Path(env["OPS_STATE_DIR"]) / "smoke-worker.pid").unlink()
            job = call("/exec", {"command": "init", "args": ["60"]}, background="true")[1]
            worker = worker_pid()
            stop()
            wait_for(lambda: not alive(worker), "worker termination after service shutdown")
            start()
            assert call("/processes/" + job["id"])[1]["state"] == "INTERRUPTED"

            # Abrupt JVM death leaves its supervisor alive: recovery must block another mutation.
            (Path(env["OPS_STATE_DIR"]) / "smoke-worker.pid").unlink()
            job = call("/exec", {"command": "init", "args": ["60"]}, background="true")[1]
            worker_pid()
            job = call("/processes/" + job["id"])[1]
            supervisors.add(job["pid"])
            process.kill()
            process.wait(timeout=10)
            process = None
            start()
            assert call("/processes/" + job["id"])[1]["state"] == "INTERRUPTED"
            assert call("/exec", {"command": "init", "args": []})[0] == 409
            os.kill(job["pid"], signal.SIGTERM)
            wait_for(lambda: not alive(job["pid"]), "orphan supervisor termination")
            supervisors.remove(job["pid"])
            status, resumed = call("/exec", {"command": "init", "args": ["0"]}, background="false")
            assert status == 200 and resumed["state"] == "SUCCEEDED", resumed
            stop()

            lifecycle_started = True
            for action in ("start", "status", "restart"):
                subprocess.run(lifecycle + [action], env=env, cwd=temporary, check=True, timeout=60)
                wait_for(ready, "service launcher " + action)
            subprocess.run(lifecycle + ["stop"], env=env, check=True, timeout=60)
            lifecycle_started = False
            assert subprocess.run(lifecycle + ["status"], env=env, capture_output=True).returncode == 3

        loader = subprocess.run([java, "-jar", str(installation / "lib/evsrestapi-loader.jar"), "--help"],
                                env=env, cwd=temporary, capture_output=True, text=True, timeout=30)
        assert loader.returncode == 0 and "forceDeleteIndex" in loader.stdout, loader.stderr
        for script in (installation / "bin").rglob("*.sh"):
            if "patches" not in script.parts:
                subprocess.run([bash, "-n", str(script)], check=True, capture_output=True)
        print("PASS: packaged API/loader, authentication, argument preservation, output, failure, polling, CLI/API lock, history and shell syntax")
        if os.name != "nt":
            print("PASS: Unix shutdown, surviving-worker recovery, launcher start/stop/restart/status and ZIP executable permissions")
    finally:
        stop()
        for pid in supervisors:
            if alive(pid):
                os.kill(pid, signal.SIGTERM)
        if lifecycle_started:
            subprocess.run(lifecycle + ["stop"], env=env, timeout=60)
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="evs operations smoke ") as directory:
        run_smoke(arguments.archive.resolve(), Path(directory))
