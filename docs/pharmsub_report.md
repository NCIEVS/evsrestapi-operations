# Monthly PharmSub Excel report

The generator runs the query in `config/reports/pharmsub.rq` against Jena,
substituting the requested version in the named graph URI. It preserves the
supplied query's C1909 hierarchy traversal, synonym/source pairing, optional
fields, `DISTINCT`, and `ORDER BY ?Concept_Name ?SY`. It includes C1909 itself.
Multiple synonyms, sources, CAS values, or definitions can produce multiple
rows for a concept. The script preserves all returned rows and their order.

## Generate a report

Normal monthly reports use the production NCIT2 dataset on
`ncidb-p335-c.nci.nih.gov:3030`.
The browser page is
`http://ncidb-p335-c.nci.nih.gov:3030/#/dataset/NCIT2/query`.
Pass the service URL `http://ncidb-p335-c.nci.nih.gov:3030/NCIT2/query`
to `--endpoint`; the browser URL's `/#/dataset/...` fragment is not a query
service endpoint.

For development testing, pass
`--endpoint http://ncias-d2175-c.nci.nih.gov:3030/NCIT2/query` and
`--output-dir ./output/dev`. Select the environment explicitly; the script
uses the supplied endpoint or exported configuration.

Python 3.9 or later is required. Poetry is optional: generation and the
PharmSub tests can use Python's built-in `venv` and pip.

From the operations repository root, run this setup once:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install 'openpyxl==3.1.5' 'lxml==5.4.0'
```

The dependency versions match the repository's lock file. Include `lxml`
so multiline text, including carriage returns, is preserved by the Excel
writer. The project-local `.venv` is ignored by Git and does not need shell
activation. Subsequent reports use the existing `.venv/bin/python` directly;
there is no need to reinstall the dependencies for each run.
If you already use Poetry, run `poetry install` and replace `.venv/bin/python`
with `poetry run python` in the commands below.

```bash
.venv/bin/python bin/pharmsub_report.py \
  --version 26.09d \
  --release-date 20260928 \
  --endpoint http://ncidb-p335-c.nci.nih.gov:3030/NCIT2/query \
  --output-dir ./output
```

When copying commands into a terminal, use the plain URL from the code block.
Do not include Markdown link syntax or blank lines between continued lines.
A backslash must be the last character on its line. The generation command
can also be pasted as one line:

```bash
.venv/bin/python bin/pharmsub_report.py --version 26.09d --release-date 20260928 --endpoint http://ncidb-p335-c.nci.nih.gov:3030/NCIT2/query --output-dir ./output
```

Replace the example version and date with the intended release. The date
must be an explicit, valid `YYYYMMDD` date. The graph must have finished
loading and passed the monthly content QA process before generation.

The script uses exported `GRAPH_DB_USERNAME` and `GRAPH_DB_PASSWORD` for
HTTP Basic or Digest authentication when configured. Set both or neither.
Credentials are not accepted in the endpoint URL and are not recorded in
the output files. HTTP redirects are rejected so a login page or different
endpoint cannot silently replace the configured query service.

To omit `--endpoint`, export `PHARMSUB_ENDPOINT`, or use the existing graph
environment variables. `GRAPH_DB_URL` supplies the server base URL;
`GRAPH_DB_DB` (or `GRAPH_DB`) selects the database, defaulting to `NCIT2`.
Alternatively, use `GRAPH_DB_HOST`, `GRAPH_DB_SCHEME` (default `http`), and
`GRAPH_DB_PORT` (default `3030`). Explicit `--endpoint` takes precedence.
The Python script consumes exported variables and does not source a shell
configuration file. Source your Jena `config/setenv.sh` in your shell first
if needed, as for operations scripts using `--noconfig`.

`--timeout` sets the HTTP timeout in seconds, defaulting to 600. A failed
request stops the run. Nothing is uploaded, and the graph is never modified.

## Connection troubleshooting

The script distinguishes DNS lookup failures, timeouts, refused connections,
and HTTP errors. A DNS lookup failure means the connection cannot find a
server address; increasing the query timeout will not resolve it.

Try opening the Jena query page on the same computer:

```text
http://ncidb-p335-c.nci.nih.gov:3030/#/dataset/NCIT2/query
```

If it also fails, connect to the NIH/NCI network or VPN required for that
server and verify that the hostname in the procedure is still current.
If the browser opens it but Python cannot connect, compare the hostname
and port and check whether the browser uses a proxy or tunnel that Python
does not use. Run the script where the internal server is reachable, or
configure the required proxy for that environment.

Once the server is reachable, rerun the generation command. A reachable
server that takes longer to answer the query may need a larger `--timeout`.

## Output and validation

A successful example run creates this directory:

```text
output/NCIT_PharmSub_26.09d_20260928/
  NCIT_PharmSub_26.09d_20260928.xlsx
  NCIT_PharmSub_26.09d_20260928.results.json
  NCIT_PharmSub_26.09d_20260928.rq
  NCIT_PharmSub_26.09d_20260928.report.json
```

The workbook has one worksheet, `queryResults`, with these columns:

```text
Concept_Name, Concept_ID, PT, SY, SY_Source, CAS_Registry, FDA_UNII_Code, DEFINITION
```

Every populated cell is explicitly stored as a string with Excel text
formatting, including numeric-looking identifiers, date-like synonyms, and
values beginning with `=`. Missing or empty optional values remain blank.
The workbook uses the sample's plain sheet structure, with no extra tabs,
tables, or formulas.

The script rejects empty results, missing required literals, missing C1909,
unexpected columns, invalid XML characters, and Excel row or cell length
limits. It reopens the saved workbook and checks every value, row count,
and populated cell's string type and text format against the response.
The final directory appears only after validation succeeds. A failed run
cleans up its staging directory and exits nonzero. Existing output is never
overwritten; choose another `--output-dir` for a rerun.

The JSON report records the source, version, date, counts, optional blanks,
and SHA-256 checksums for the workbook, raw response, and rendered query.
Distinct RDF terms can have identical displayed text, so duplicate display
rows are counted and retained rather than collapsed.

Add `--previous-report /path/to/previous.report.json` to record row and
concept count changes from a previous generated report. Counts are not
hardcoded across releases. Review changes as part of monthly content QA;
matching counts alone do not establish correct content or completed loading.

## Replay saved results

For offline conversion or reproducing a previous run:

```bash
.venv/bin/python bin/pharmsub_report.py \
  --version 26.09d \
  --release-date 20260928 \
  --results-json /path/to/NCIT_PharmSub_26.09d_20260928.results.json \
  --output-dir ./output-replay
```

Use the version and date belonging to the saved response, and retain its
original `.rq` and `.report.json` as provenance. SPARQL result JSON does not
contain the queried graph, so an offline replay cannot independently verify
the version or that the source graph finished loading. Replay mode records
the input path and does not contact Jena or use graph credentials.

The September 2026 sample has 112,578 data rows and 26,988 distinct concepts.
It contains numeric and date-formatted identifier and synonym cells. Use it
as a layout and count reference; use the raw query response to establish
exact string values rather than reproducing Excel's conversions. If the
26.09d graph remains available, regenerate it and investigate differences
against that response. Only compare ordering across different runs within
the query's specified sort keys; ties are not ordered by the query.

Validation on 2026-11-16 used the development server `ncias-d2175-c`
because production was unavailable. The September example used the `26.09d`
graph and release date `20260928`. Generation, download, and verification
took approximately six minutes and produced 112,578 rows and 26,988 concepts.
The saved workbook matched every raw result value and text type. Reference
comparison ignored ordering among tied sort keys: 111,609 rows matched
exactly, 902 differed because the reference contained number/date cells,
and 67 differed because the reference had character encoding errors (for
example, `na√Øve` instead of the raw `naïve`). Every concept's row count
matched, and no unexplained row differences remained. The generator
preserves the raw query strings rather than reproducing those conversions.

The October example (`26.10d` / `20261112`) was also generated and verified
on dev: 112,798 rows and 27,013 concepts, with all rows matching the October
reference after treating empty optional strings as blank. The saved reports
retain their actual development endpoint as provenance. Runtime depends on
server load and download speed.

## Publication handoff

Upload only the validated `.xlsx` to the designated publication folder.
Keep the raw results, query, and report with the release records. Generation
does not upload files, invoke GitHub Actions, or change the monthly loader.

The supplied procedure identifies `ncias-p3388-v` and
`/ftp/ftpcacore/pub/cacore/EVS/NCI_Thesaurus/Branches` as the upload target.
Before automating the transfer, confirm the supported transfer protocol and
how that target maps to the sync workflow's source,
`ncils-av-62s9yh:/share/content/evs/ftp1`. The
[production sync workflow](https://github.com/CBIIT/evs-utils/actions/workflows/evs-ftp-s3sync-prod.yaml)
must run after the upload for public publication. Verify that the exact
workbook is publicly available after synchronization.

## Tests

After the setup above, install the test runner and run the PharmSub tests:

```bash
.venv/bin/python -m pip install 'pytest==7.4.4'
.venv/bin/python -m pytest test/pharmsub_report_test.py
```

The test runner is only needed for development, not monthly report generation.

The tests use small synthetic SPARQL responses and a local HTTP server for
query and authentication checks. They do not depend on an NCI connection.
