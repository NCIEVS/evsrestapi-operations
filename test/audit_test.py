from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "bin/audit.sh"


def run_audit(tmp_path, curl_exit=0, args=("--recent", "all"), response='{"hits":{"hits":[]}}'):
    # The script builds its OpenSearch query with jq, so these tests use the real one.
    if shutil.which("jq") is None:
        pytest.skip("audit.sh requires jq")
    tools = tmp_path / "audit tools"
    tools.mkdir()
    response_file = tmp_path / "response.json"
    response_file.write_text(response, encoding="utf-8")
    scripts = {
        "curl": '#!/bin/bash\nprintf "%s\\n" "$@" > "$AUDIT_TEST_ARGS"\ncat "$AUDIT_TEST_RESPONSE"\nexit "$AUDIT_TEST_EXIT"\n',
        "date": '#!/bin/bash\necho "GNU date must not be required for --recent" >&2\nexit 99\n',
    }
    for name, contents in scripts.items():
        tool = tools / name
        tool.write_text(contents, encoding="utf-8", newline="\n")
        tool.chmod(0o755)
    arguments = tmp_path / "curl-arguments.txt"
    env = dict(os.environ, AUDIT_TEST_TOOLS=str(tools),
               OPS_PYTHON=sys.executable, AUDIT_TEST_ARGS=str(arguments), AUDIT_TEST_EXIT=str(curl_exit),
               AUDIT_TEST_RESPONSE=str(response_file),
               ES_SCHEME="http", ES_HOST="127.0.0.1", ES_PORT="1")
    result = subprocess.run([os.environ.get("OPS_BASH", "bash"), "-c",
                            'export PATH="$(cd -- "$AUDIT_TEST_TOOLS" && pwd):$PATH"; source "$@"',
                            "audit-test", str(SCRIPT), "--noconfig", *args],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    return result, arguments


def request_body(arguments):
    lines = arguments.read_text().splitlines()
    return json.loads(lines[lines.index("-d") + 1])


def test_recent_audit_uses_a_portable_utc_range(tmp_path):
    result, arguments = run_audit(tmp_path)
    assert result.returncode == 0, result.stderr
    query = json.dumps(request_body(arguments)["query"])
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


def test_stats_report_is_available_and_newest_first(tmp_path):
    hit = {"_source": {"terminology": "ncit", "version": "26.10d", "date": "2026-11-01T00:00:00Z",
                       "stats": {"conceptCount": 5, "codeCount": 4,
                                 "hierarchy": {"maxParents": {"code": "C1", "count": 3}}}}}
    result, arguments = run_audit(tmp_path, args=("stats", "ncit"),
                                  response=json.dumps({"hits": {"hits": [hit]}}))
    assert result.returncode == 0, result.stdout + result.stderr
    body = request_body(arguments)
    # Newest first, so the 1,000-record limit never drops the latest loads.
    assert body["sort"][0] == {"startDate": {"order": "desc", "missing": "_last"}}
    assert {"term": {"terminology": "ncit"}} in body["query"]["bool"]["filter"]
    header, row = [line.split("\t") for line in result.stdout.splitlines()[:2]]
    assert len(row) == len(header) == 24
    assert row[:4] == ["ncit", "26.10d", "5", "4"]
    assert row[header.index("Max Parents")] == "C1:3"
