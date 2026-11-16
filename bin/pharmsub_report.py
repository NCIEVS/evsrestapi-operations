#!/usr/bin/env python3
"""Generate and verify the monthly PharmSub workbook from Jena SELECT results."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import tempfile
from datetime import datetime, timezone
from itertools import chain, zip_longest
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPBasicAuthHandler,
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPRedirectHandler,
    Request,
    build_opener,
)

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell


COLUMNS = (
    "Concept_Name", "Concept_ID", "PT", "SY", "SY_Source",
    "CAS_Registry", "FDA_UNII_Code", "DEFINITION",
)
SHEET_NAME = "queryResults"
ROOT_CODE = "C1909"
MAX_DATA_ROWS = 1_048_575  # Reserve one Excel row for the headers.
QUERY_TEMPLATE = Path(__file__).resolve().parents[1] / "config/reports/pharmsub.rq"
INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


class ReportError(Exception):
    """An input, retrieval, or workbook validation error."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReportError("Query endpoint redirected; configure its final query URL.")


def render_query(version: str) -> str:
    if not re.fullmatch(r"[0-9]{2}\.(?:0[1-9]|1[0-2])[a-z]", version):
        raise ReportError("Version must have the form YY.MMa, for example 26.09d.")
    return QUERY_TEMPLATE.read_text(encoding="utf-8").replace("{{VERSION}}", version)


def validate_release_date(release_date: str) -> None:
    if not re.fullmatch(r"[0-9]{8}", release_date):
        raise ReportError("Release date must be YYYYMMDD, for example 20260928.")
    try:
        datetime.strptime(release_date, "%Y%m%d")
    except ValueError as exc:
        raise ReportError("Release date is not a valid calendar date.") from exc


def configured_endpoint() -> Optional[str]:
    """Use exported operations configuration without executing a shell file."""
    if os.environ.get("PHARMSUB_ENDPOINT"):
        return os.environ["PHARMSUB_ENDPOINT"]
    base = os.environ.get("GRAPH_DB_URL")
    if not base and os.environ.get("GRAPH_DB_HOST"):
        base = "{}://{}:{}".format(
            os.environ.get("GRAPH_DB_SCHEME", "http"),
            os.environ["GRAPH_DB_HOST"],
            os.environ.get("GRAPH_DB_PORT", "3030"),
        )
    if base:
        database = os.environ.get("GRAPH_DB_DB") or os.environ.get("GRAPH_DB", "NCIT2")
        return f"{base.rstrip('/')}/{database}/query"
    return None


def fetch_results(endpoint: str, query: str, destination: Path, timeout: float) -> None:
    try:
        parts = urlsplit(endpoint)
        valid = (
            parts.scheme in ("http", "https") and parts.hostname and parts.port != 0
            and not parts.username and not parts.password and not parts.query
            and not parts.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise ReportError("Endpoint must be an HTTP(S) URL without credentials, query, or fragment.")
    username = os.environ.get("GRAPH_DB_USERNAME")
    password = os.environ.get("GRAPH_DB_PASSWORD")
    if bool(username) != bool(password):
        raise ReportError("Set both GRAPH_DB_USERNAME and GRAPH_DB_PASSWORD, or neither.")
    handlers = [NoRedirects()]
    if username:
        credentials = HTTPPasswordMgrWithDefaultRealm()
        credentials.add_password(None, endpoint, username, password)
        handlers += [HTTPBasicAuthHandler(credentials), HTTPDigestAuthHandler(credentials)]
    request = Request(endpoint, data=query.encode("utf-8"), headers={
        "Content-Type": "application/sparql-query; charset=utf-8",
        "Accept": "application/sparql-results+json",
    }, method="POST")
    try:
        with build_opener(*handlers).open(request, timeout=timeout) as response:
            with destination.open("wb") as output:
                shutil.copyfileobj(response, output)
    except HTTPError as exc:
        raise ReportError(f"Jena returned HTTP {exc.code}; no report was published.") from exc
    except (URLError, TimeoutError) as exc:
        reason = exc.reason if isinstance(exc, URLError) else exc
        server = f"{parts.hostname}:{parts.port or (443 if parts.scheme == 'https' else 80)}"
        if isinstance(reason, socket.gaierror):
            message = (
                f"DNS lookup failed while connecting to Jena at {server}. "
                "Check the endpoint hostname and NIH/NCI network or VPN access."
            )
        elif isinstance(reason, TimeoutError):
            message = (
                f"Request to Jena at {server} timed out (HTTP timeout: {timeout:g} seconds). "
                "Check network access and server availability. Increase --timeout "
                "if the server is reachable but the query needs more time."
            )
        elif isinstance(reason, ConnectionRefusedError):
            message = (
                f"Jena refused the connection at {server}. "
                "Check the endpoint port and that the Jena service is running."
            )
        else:
            # The raw exception can contain proxy URLs or other credential-bearing text.
            message = (
                f"Could not retrieve Jena results from {server}. "
                "Check network/VPN access and any required proxy configuration."
            )
        raise ReportError(message) from exc


def read_rows(path: Path) -> list[tuple[Optional[str], ...]]:
    try:
        result = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise ReportError("Input is not valid UTF-8 SPARQL JSON results.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("head"), dict):
        raise ReportError("Expected a SPARQL SELECT response with head.vars and results.bindings.")
    if result["head"].get("vars") != list(COLUMNS):
        raise ReportError("SPARQL result columns do not match the eight PharmSub columns in order.")
    bindings = result.get("results", {})
    bindings = bindings.get("bindings") if isinstance(bindings, dict) else None
    if not isinstance(bindings, list) or not bindings:
        raise ReportError("No result rows; check that the requested NCIT graph has finished loading.")
    if len(bindings) > MAX_DATA_ROWS:
        raise ReportError("Results exceed the Excel worksheet row limit.")
    rows = []
    for index, binding in enumerate(bindings, start=2):
        if not isinstance(binding, dict) or set(binding) - set(COLUMNS):
            raise ReportError(f"Unexpected SPARQL binding at worksheet row {index}.")
        values = []
        for column in COLUMNS:
            term = binding.get(column)
            if column not in binding and column in COLUMNS[5:]:
                values.append(None)
                continue
            if (
                not isinstance(term, dict)
                or term.get("type") not in ("literal", "typed-literal")
                or not isinstance(term.get("value"), str)
            ):
                raise ReportError(f"Expected a literal for {column} at worksheet row {index}.")
            value = term["value"]
            if column in COLUMNS[:5] and not value.strip():
                raise ReportError(f"Missing required {column} at worksheet row {index}.")
            if INVALID_XML.search(value):
                raise ReportError(f"Invalid XML character in {column} at worksheet row {index}.")
            if len(value.encode("utf-16-le")) // 2 > 32_767:
                raise ReportError(f"Excel cell text limit exceeded in {column} at worksheet row {index}.")
            values.append(value if value else None)
        rows.append(tuple(values))
    if not any(row[1] == ROOT_CODE for row in rows):
        raise ReportError("Results omit the C1909 root; check the graph and query completeness.")
    return rows


def write_workbook(path: Path, rows: list[tuple[Optional[str], ...]]) -> None:
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet(SHEET_NAME)
    for row in chain((COLUMNS,), rows):
        cells = []
        for value in row:
            cell = WriteOnlyCell(sheet, value=value)
            # Assignment alone would interpret '=...' as a formula and '#N/A' as an error.
            cell.data_type = "s"
            cell.number_format = "@"
            cells.append(cell)
        sheet.append(cells)
    workbook.save(path)


def verify_workbook(path: Path, rows: list[tuple[Optional[str], ...]]) -> None:
    workbook = load_workbook(path, read_only=True, data_only=False)
    try:
        if workbook.sheetnames != [SHEET_NAME]:
            raise ReportError("Workbook must contain only the queryResults worksheet.")
        sheet = workbook[SHEET_NAME]
        sheet.reset_dimensions()
        actual = sheet.iter_rows()
        for index, (expected, cells) in enumerate(
            zip_longest(chain((COLUMNS,), rows), actual), start=1
        ):
            if expected is None or cells is None:
                raise ReportError("Saved workbook row count differs from the query results.")
            values = tuple(cell.value for cell in cells)
            padded = values[:len(COLUMNS)] + (None,) * max(0, len(COLUMNS) - len(values))
            if padded != expected or any(value is not None for value in values[len(COLUMNS):]):
                raise ReportError(f"Saved workbook differs from query results at row {index}.")
            if any(cell.value is not None and (cell.data_type != "s" or cell.number_format != "@") for cell in cells):
                raise ReportError(f"Saved workbook contains a non-text cell at row {index}.")
    finally:
        workbook.close()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_previous(path: Path, report: dict) -> dict:
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
        counts = {key: previous[key] for key in ("data_rows", "concept_count")}
        if any(type(value) is not int or value < 1 for value in counts.values()):
            raise ValueError("Invalid previous counts")
    except (ValueError, KeyError, TypeError) as exc:
        raise ReportError("Previous report must contain positive data_rows and concept_count integers.") from exc
    return {
        "report": str(path.resolve()),
        "previous_version": previous.get("version"),
        "data_rows_delta": report["data_rows"] - counts["data_rows"],
        "data_rows_change_percent": round(100 * (report["data_rows"] / counts["data_rows"] - 1), 2),
        "concept_count_delta": report["concept_count"] - counts["concept_count"],
    }


def generate_report(
    version: str, release_date: str, output_dir: Path, *,
    endpoint: Optional[str] = None, results_json: Optional[Path] = None,
    timeout: float = 600, previous_report: Optional[Path] = None,
) -> Path:
    query = render_query(version)
    validate_release_date(release_date)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ReportError("Timeout must be a positive, finite number of seconds.")
    if (endpoint is None) == (results_json is None):
        raise ReportError("Provide either a query endpoint or a saved results JSON file.")
    stem = f"NCIT_PharmSub_{version}_{release_date}"
    final_dir = output_dir / stem
    if final_dir.exists():
        raise ReportError(f"Output already exists: {final_dir}. Use another output directory for a rerun.")
    output_dir.mkdir(parents=True, exist_ok=True)
    # Publish the complete bundle together only after the saved workbook has passed validation.
    with tempfile.TemporaryDirectory(prefix=f".{stem}.", dir=output_dir) as directory:
        staging = Path(directory)
        raw_path = staging / f"{stem}.results.json"
        query_path = staging / f"{stem}.rq"
        workbook_path = staging / f"{stem}.xlsx"
        query_path.write_text(query, encoding="utf-8")
        if results_json is not None:
            print("Reading saved SPARQL results...", file=sys.stderr)
            shutil.copyfile(results_json, raw_path)
            source = {"kind": "saved_results", "path": str(results_json.resolve())}
        else:
            print(f"Querying Jena for NCIT {version}...", file=sys.stderr)
            fetch_results(endpoint, query, raw_path, timeout)
            source = {"kind": "jena", "endpoint": endpoint}
        rows = read_rows(raw_path)
        print(f"Writing {len(rows):,} data rows as text...", file=sys.stderr)
        write_workbook(workbook_path, rows)
        print("Verifying every saved value and cell type...", file=sys.stderr)
        verify_workbook(workbook_path, rows)
        report = {
            "schema_version": 1,
            "status": "validated",
            "version": version,
            "release_date": release_date,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "graph": f"http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus_{version}.owl",
            "source": source,
            "sheet": SHEET_NAME,
            "columns": list(COLUMNS),
            "data_rows": len(rows),
            "concept_count": len({row[1] for row in rows}),
            "duplicate_display_rows": len(rows) - len(set(rows)),
            "optional_blank_counts": {
                column: sum(row[index] is None for row in rows)
                for index, column in enumerate(COLUMNS) if index >= 5
            },
            "all_values_and_string_types_match": True,
            "sha256": {path.name: sha256(path) for path in (workbook_path, raw_path, query_path)},
        }
        if previous_report is not None:
            report["comparison"] = compare_previous(previous_report, report)
        (staging / f"{stem}.report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if final_dir.exists():
            raise ReportError(f"Output already exists: {final_dir}.")
        staging.rename(final_dir)
    return final_dir / workbook_path.name


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="NCIT version, e.g. 26.09d")
    parser.add_argument("--release-date", required=True, help="Release date in YYYYMMDD form")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--endpoint", help="Jena SELECT URL; otherwise use exported graph configuration")
    source.add_argument("--results-json", type=Path, help="Replay saved PharmSub SPARQL JSON results offline")
    parser.add_argument("--timeout", type=float, default=600, help="HTTP timeout in seconds (default: 600)")
    parser.add_argument("--previous-report", type=Path, help="Previous generated JSON report for count comparison")
    args = parser.parse_args(argv)
    endpoint = None if args.results_json is not None else args.endpoint or configured_endpoint()
    try:
        path = generate_report(
            args.version, args.release_date, args.output_dir, endpoint=endpoint,
            results_json=args.results_json, timeout=args.timeout, previous_report=args.previous_report,
        )
    except (ReportError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Validated workbook: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
