from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
import subprocess
import sys


SCRIPT = Path(__file__).resolve().parents[1] / "bin/audit.sh"


def run_audit(tmp_path, curl_exit=0):
    tools = tmp_path / "audit tools"
    tools.mkdir()
    scripts = {
        "curl": '#!/bin/bash\nprintf "%s\\n" "$@" > "$AUDIT_TEST_ARGS"\necho "{}"\nexit "$AUDIT_TEST_EXIT"\n',
        "jq": '#!/bin/bash\n[[ "$1" != --help ]] || exit 0\ncat > /dev/null\n',
        "date": '#!/bin/bash\necho "GNU date must not be required for --recent" >&2\nexit 99\n',
    }
    for name, contents in scripts.items():
        tool = tools / name
        tool.write_text(contents, encoding="utf-8", newline="\n")
        tool.chmod(0o755)
    arguments = tmp_path / "curl-arguments.txt"
    env = dict(os.environ, AUDIT_TEST_TOOLS=str(tools),
               OPS_PYTHON=sys.executable, AUDIT_TEST_ARGS=str(arguments), AUDIT_TEST_EXIT=str(curl_exit),
               ES_SCHEME="http", ES_HOST="127.0.0.1", ES_PORT="1")
    result = subprocess.run([os.environ.get("OPS_BASH", "bash"), "-c",
                            'export PATH="$(cd -- "$AUDIT_TEST_TOOLS" && pwd):$PATH"; source "$@"',
                            "audit-test", str(SCRIPT), "--noconfig", "--recent", "all"],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    return result, arguments


def test_recent_audit_uses_a_portable_utc_range(tmp_path):
    result, arguments = run_audit(tmp_path)
    assert result.returncode == 0, result.stderr
    query = next(line for line in arguments.read_text().splitlines() if line.startswith("q="))
    dates = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", query)
    assert len(dates) == 4
    start, end = [datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) for value in dates[:2]]
    assert end - start == timedelta(hours=24)
    assert abs((datetime.now(timezone.utc) - end).total_seconds()) < 10


def test_audit_propagates_query_failure(tmp_path):
    result, _ = run_audit(tmp_path, curl_exit=7)
    assert result.returncode == 1
    assert "Elasticsearch query failed" in result.stderr
    assert "No records found" not in result.stdout
