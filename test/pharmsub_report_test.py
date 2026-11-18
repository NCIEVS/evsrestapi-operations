import base64
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import socket
import threading
from urllib.error import URLError

from openpyxl import load_workbook
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "bin/pharmsub_report.py"
spec = importlib.util.spec_from_file_location("pharmsub_report", SCRIPT)
pharmsub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pharmsub)


def literal(value):
    return {"type": "literal", "value": value}


@pytest.fixture(autouse=True)
def clear_graph_environment(monkeypatch):
    for name in (
        "PHARMSUB_ENDPOINT", "GRAPH_DB_URL", "GRAPH_DB_DB", "GRAPH_DB",
        "GRAPH_DB_SCHEME", "GRAPH_DB_HOST", "GRAPH_DB_PORT",
        "GRAPH_DB_USERNAME", "GRAPH_DB_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def payload():
    root = dict(zip(pharmsub.COLUMNS[:5], map(literal, (
        "Pharmacologic Substance", "C1909", "Pharmacologic Substance", "Agent", "NCI",
    ))))
    child = dict(zip(pharmsub.COLUMNS, map(literal, (
        "Test Substance", "C123", "Test Substance", "11-4", "NCI",
        "001-23-4", "0447KM2XTD", "  Greek β, café & <text>\nline 2\tend\r\n  ",
    ))))
    # Multiple sources and CAS values must remain separate rows for the same concept.
    other_source = deepcopy(child)
    other_source["SY_Source"] = literal("FDA")
    other_cas = deepcopy(child)
    other_cas["CAS_Registry"] = literal("002-34-5")
    return {
        "head": {"vars": list(pharmsub.COLUMNS)},
        "results": {"bindings": [root, child, other_source, other_cas]},
    }


@pytest.fixture
def saved_results(tmp_path, payload):
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def generate(tmp_path, saved_results, **kwargs):
    return pharmsub.generate_report(
        "26.09d", "20260928", tmp_path / "output", results_json=saved_results, **kwargs
    )


def test_offline_generation_preserves_values_and_audit_files(tmp_path, saved_results):
    previous = tmp_path / "previous.report.json"
    previous.write_text(json.dumps({"version": "26.08d", "data_rows": 5, "concept_count": 3}))
    workbook_path = generate(tmp_path, saved_results, previous_report=previous)
    assert workbook_path.name == "NCIT_PharmSub_26.09d_20260928.xlsx"
    workbook = load_workbook(workbook_path, read_only=True)
    try:
        assert workbook.sheetnames == ["queryResults"]
        rows = list(workbook.active.iter_rows(max_col=8))
        assert tuple(cell.value for cell in rows[0]) == pharmsub.COLUMNS
        assert [cell.value for cell in rows[1]][5:] == [None, None, None]
        assert rows[2][3].value == "11-4"
        assert rows[2][5].value == "001-23-4"
        assert rows[2][6].value == "0447KM2XTD"
        assert rows[2][7].value == "  Greek β, café & <text>\nline 2\tend\r\n  "
        assert len(rows) == 5
        assert all(cell.data_type == "s" and cell.number_format == "@" for row in rows for cell in row if cell.value is not None)
    finally:
        workbook.close()
    files = sorted(workbook_path.parent.iterdir())
    assert len(files) == 4
    report = json.loads(workbook_path.with_suffix(".report.json").read_text())
    assert report["status"] == "validated"
    assert report["data_rows"] == 4
    assert report["concept_count"] == 2
    assert report["optional_blank_counts"] == {name: 1 for name in pharmsub.COLUMNS[5:]}
    assert report["source"]["kind"] == "saved_results"
    assert report["comparison"]["data_rows_delta"] == -1
    assert report["comparison"]["data_rows_change_percent"] == -20
    assert report["comparison"]["concept_count_delta"] == -1
    assert all(pharmsub.sha256(workbook_path.parent / name) == digest for name, digest in report["sha256"].items())
    assert workbook_path.with_suffix(".results.json").read_bytes() == saved_results.read_bytes()
    assert "Thesaurus_26.09d.owl>" in workbook_path.with_suffix(".rq").read_text()


@pytest.mark.parametrize("text", [
    "=1+1", "+001", "-001", "@SUM(A1)", "#N/A", "#REF!", "000123", "1E10", "2026-09-28",
])
def test_excel_like_strings_are_never_converted(tmp_path, payload, text):
    payload["results"]["bindings"][1]["SY"] = literal(text)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload))
    workbook_path = generate(tmp_path, path)
    workbook = load_workbook(workbook_path, read_only=True, data_only=False)
    try:
        cell = workbook.active["D3"]
        assert cell.value == text
        assert cell.data_type == "s"
    finally:
        workbook.close()


@pytest.mark.parametrize("mutation, message", [
    (lambda p: p["head"].update(vars=["Concept_ID"]), "columns"),
    (lambda p: p["results"].update(bindings=[]), "No result rows"),
    (lambda p: p["results"]["bindings"].pop(0), "C1909"),
    (lambda p: p["results"]["bindings"][1].pop("SY_Source"), "Expected a literal"),
    (lambda p: p["results"]["bindings"][1].update(SY=literal(" ")), "Missing required"),
    (lambda p: p["results"]["bindings"][1].update(CAS_Registry=None), "Expected a literal"),
    (lambda p: p["results"]["bindings"][1].update(SY={"type": "uri", "value": "https://example.org"}), "Expected a literal"),
    (lambda p: p["results"]["bindings"][1].update(SY=literal(123)), "Expected a literal"),
    (lambda p: p["results"]["bindings"][1].update(SY=literal("bad\x00text")), "Invalid XML"),
    (lambda p: p["results"]["bindings"][1].update(SY=literal("x" * 32_768)), "text limit"),
    (lambda p: p["results"]["bindings"][1].update(SY=literal("😀" * 16_384)), "text limit"),
])
def test_invalid_results_publish_no_output(tmp_path, payload, mutation, message):
    mutation(payload)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(pharmsub.ReportError, match=message):
        generate(tmp_path, path)
    assert list((tmp_path / "output").iterdir()) == []


def test_malformed_json_and_excel_capacity_fail(tmp_path, saved_results, monkeypatch):
    path = tmp_path / "html.json"
    path.write_text("<html>Login</html>")
    with pytest.raises(pharmsub.ReportError, match="not valid"):
        generate(tmp_path, path)
    monkeypatch.setattr(pharmsub, "MAX_DATA_ROWS", 3)
    with pytest.raises(pharmsub.ReportError, match="row limit"):
        generate(tmp_path, saved_results)


def test_distinct_rdf_terms_with_same_display_value_are_preserved(tmp_path, payload):
    other = deepcopy(payload["results"]["bindings"][1])
    other["SY"]["xml:lang"] = "en"
    payload["results"]["bindings"].append(other)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload))
    workbook_path = generate(tmp_path, path)
    report = json.loads(workbook_path.with_suffix(".report.json").read_text())
    assert report["data_rows"] == 5
    assert report["duplicate_display_rows"] == 1


@pytest.mark.parametrize("version,date", [
    ("26.13d", "20260928"), ("../26.09d", "20260928"),
    ("26.09d", "20260230"), ("26.09d", "2026-09-28"),
])
def test_invalid_release_inputs_fail_before_output(tmp_path, saved_results, version, date):
    with pytest.raises(pharmsub.ReportError):
        pharmsub.generate_report(version, date, tmp_path / "output", results_json=saved_results)
    assert not (tmp_path / "output").exists()


def test_does_not_overwrite_existing_output(tmp_path, saved_results):
    workbook_path = generate(tmp_path, saved_results)
    original = {p.name: p.read_bytes() for p in workbook_path.parent.iterdir()}
    with pytest.raises(pharmsub.ReportError, match="already exists"):
        generate(tmp_path, saved_results)
    assert original == {p.name: p.read_bytes() for p in workbook_path.parent.iterdir()}


def test_validation_failure_removes_staging_files(tmp_path, saved_results, monkeypatch):
    def fail(*args):
        raise pharmsub.ReportError("verification failed")
    monkeypatch.setattr(pharmsub, "verify_workbook", fail)
    with pytest.raises(pharmsub.ReportError, match="verification failed"):
        generate(tmp_path, saved_results)
    assert list((tmp_path / "output").iterdir()) == []


@pytest.mark.parametrize("change", ["value", "type", "missing_row", "extra_column"])
def test_verification_detects_saved_file_changes(tmp_path, saved_results, change):
    payload = json.loads(saved_results.read_text())
    payload["results"]["bindings"][1]["SY"] = literal("#N/A")
    saved_results.write_text(json.dumps(payload))
    workbook_path = generate(tmp_path, saved_results)
    workbook = load_workbook(workbook_path)
    if change == "value":
        workbook.active["D3"] = "changed"
    elif change == "type":
        workbook.active["D3"].data_type = "e"
    elif change == "missing_row":
        workbook.active.delete_rows(5)
    else:
        workbook.active["J3"] = "unexpected"
    workbook.save(workbook_path)
    workbook.close()
    message = "non-text" if change == "type" else "differs"
    with pytest.raises(pharmsub.ReportError, match=message):
        pharmsub.verify_workbook(workbook_path, pharmsub.read_rows(saved_results))


@pytest.fixture
def query_server(payload):
    requests = []
    state = {"status": 200, "auth": False}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append((self.path, self.headers, body.decode("utf-8")))
            if state["auth"] and not self.headers.get("Authorization"):
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="Jena"')
                self.end_headers()
                return
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/sparql-results+json")
            if state["status"] == 302:
                self.send_header("Location", "/login")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/NCIT2/query", requests, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_live_http_query_and_authentication(tmp_path, query_server, monkeypatch, capsys):
    endpoint, requests, state = query_server
    state["auth"] = True
    monkeypatch.setenv("GRAPH_DB_USERNAME", "test-user")
    monkeypatch.setenv("GRAPH_DB_PASSWORD", "test-password")
    monkeypatch.setenv("GRAPH_DB_URL", endpoint.removesuffix("/NCIT2/query"))
    monkeypatch.setenv("GRAPH_DB_DB", "NCIT2")
    assert pharmsub.main([
        "--version", "26.09d", "--release-date", "20260928", "--output-dir", str(tmp_path / "output"),
    ]) == 0
    path, headers, query = requests[-1]
    assert len(requests) == 2
    assert path == "/NCIT2/query"
    assert headers["Accept"] == "application/sparql-results+json"
    assert headers["Content-Type"].startswith("application/sparql-query")
    expected_auth = base64.b64encode(b"test-user:test-password").decode("ascii")
    assert headers["Authorization"] == f"Basic {expected_auth}"
    assert "Thesaurus_26.09d.owl>" in query
    assert "owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first" in query
    assert "ORDER BY ?Concept_Name ?SY" in query
    output = capsys.readouterr()
    assert "test-password" not in output.out + output.err
    for report_path in (tmp_path / "output").glob("*/*.report.json"):
        assert "test-password" not in report_path.read_text()


@pytest.mark.parametrize("status,message", [(500, "HTTP 500"), (302, "redirected")])
def test_http_failure_publishes_nothing(tmp_path, query_server, status, message):
    endpoint, requests, state = query_server
    state["status"] = status
    with pytest.raises(pharmsub.ReportError, match=message):
        pharmsub.generate_report("26.09d", "20260928", tmp_path / "output", endpoint=endpoint)
    assert len(requests) == 1
    assert list((tmp_path / "output").iterdir()) == []


def test_offline_cli_and_error_exit(tmp_path, saved_results, monkeypatch, capsys):
    monkeypatch.setenv("PHARMSUB_ENDPOINT", "https://unused.example/query")
    args = ["--version", "26.09d", "--release-date", "20260928",
            "--results-json", str(saved_results), "--output-dir", str(tmp_path / "output")]
    assert pharmsub.main(args) == 0
    assert pharmsub.main(args) == 1
    assert "already exists" in capsys.readouterr().err


@pytest.mark.parametrize("endpoint", ["file:///tmp/results", "https://user:secret@example.org/query", "https://example.org/query?password=secret"])
def test_invalid_endpoint_does_not_expose_credentials(tmp_path, endpoint, capsys):
    assert pharmsub.main([
        "--version", "26.09d", "--release-date", "20260928", "--endpoint", endpoint,
        "--output-dir", str(tmp_path / "output"),
    ]) == 1
    assert "secret" not in capsys.readouterr().err


@pytest.mark.parametrize("error,message", [
    (URLError(socket.gaierror(socket.EAI_NONAME, "Name not known")), "DNS lookup failed"),
    (URLError(TimeoutError("timed out")), "timed out"),
    (TimeoutError("timed out while reading"), "timed out"),
    (URLError(ConnectionRefusedError("refused")), "refused the connection"),
    (URLError("proxy failure with secret in its URL"), "proxy configuration"),
])
def test_network_errors_explain_cause_without_exposing_credentials(
    tmp_path, monkeypatch, capsys, error, message
):
    class FailingOpener:
        def open(self, *args, **kwargs):
            raise error

    monkeypatch.setattr(pharmsub, "build_opener", lambda *handlers: FailingOpener())
    assert pharmsub.main([
        "--version", "26.09d", "--release-date", "20260928",
        "--endpoint", "http://example.test:3030/NCIT2/query",
        "--output-dir", str(tmp_path / "output"),
    ]) == 1
    stderr = capsys.readouterr().err
    assert message in stderr
    assert "example.test:3030" in stderr
    assert "secret" not in stderr
    assert list((tmp_path / "output").iterdir()) == []
