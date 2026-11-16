---
name: pharmsub-report
description: Generate, replay, validate, or locate monthly NCIT PharmSub Excel reports using evsrestapi-operations. Use when an operator asks to create or rerun a PharmSub report, including setup and Jena connection troubleshooting. Publication and terminology loading are separate workflows.
---

# PharmSub Report

Help an operator obtain a validated local PharmSub workbook. Run the existing
`bin/pharmsub_report.py`; it owns the SPARQL query, Excel conversion, validation,
and audit bundle. Read the checkout's `docs/pharmsub_report.md` for additional
configuration or troubleshooting. Poetry and Microsoft Excel are not required.

## Find the checkout and release

- Find a checkout containing `bin/pharmsub_report.py` and
  `config/reports/pharmsub.rq`. Prefer the user's selected project. For an
  installed symlink, resolve the skill's path and check its containing repository.
  If neither identifies a checkout, ask for its location. Do not assume a
  particular username, Mac folder, branch, or clean working tree.
- Use the NCIT version and release date provided by the user or established
  release context. Version has the form `26.10d`; the required release date is a
  valid `YYYYMMDD`, such as `20261112`. These are examples, not current defaults.
  Never substitute today's date or infer a release date from a month name.
- If either value is missing or ambiguous, ask one concise question for the
  missing details. Offer to read a release announcement or approved report
  filename if that is easier for the operator. If the version is unknown, a
  read-only graph inventory can help present available versions; a loaded graph
  does not establish release QA.
- For production publication, establish completed loading and monthly content QA
  from release records or user context before generating the publication workbook.
  Ask about missing QA status along with any missing release details. Explicit
  dev tests and offline replays may validate the generator; label those results
  as tests, since conversion validation does not establish publication readiness.
- For a request only to find an existing report, inspect output folders and their
  `.report.json` files and return the actual paths and source environment.
  Do not regenerate a workbook merely to locate it.

## Select the source explicitly

Normal monthly runs use **production**:

```text
http://ncidb-p335-c.nci.nih.gov:3030/NCIT2/query
```

Development is available when the user requests testing there:

```text
http://ncias-d2175-c.nci.nih.gov:3030/NCIT2/query
```

Pass the selected service URL explicitly with `--endpoint`, respecting any
user-supplied endpoint. A browser URL containing `/#/dataset/NCIT2/query` is
navigation: use the same server's `/NCIT2/query` service URL. Do not silently
fall back from production to development or change a saved report's source.
Use `output/` for normal runs and `output/dev/` for dev tests unless the user
chooses another location. Both are relative to the checkout root.

For offline replay, use `--results-json` with the supplied raw response and
omit `--endpoint`. Keep its original provenance; SPARQL JSON alone cannot prove
which graph/version was queried. Put replay output under `output/replay/` by
default and label it as replayed data.

## Prepare and check access

Reuse the checkout's working Python environment. If needed, create one with
Python 3.9 or later and install just the runtime packages:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'openpyxl==3.1.5' 'lxml==5.4.0'
```

On Windows use `py -3 -m venv .venv` and `.venv\Scripts\python.exe`.
Activation, Poetry, pytest, and the unrelated converter package are unnecessary
for report generation. Include lxml to preserve carriage returns in Excel text.
Reuse installed dependencies rather than reinstalling them on every run.

For a live run, perform a short read-only endpoint check before the full query.
A graph inventory query is `SELECT ?graph WHERE { GRAPH ?graph {} } ORDER BY ?graph`;
look for `http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus_VERSION.owl` with the
selected version substituted. Use a short timeout for this check, not a large
report query. For authenticated probes, the generator's `fetch_results` helper
reuses its configured authentication and redirect handling.

Use exported `GRAPH_DB_USERNAME` and `GRAPH_DB_PASSWORD` together if required.
Never print credentials or put them in a URL. Do not source unfamiliar shell
configuration or weaken TLS checks to make a connection work.

If access fails, explain whether it is DNS, connection timeout/refusal, or an
HTTP/authentication failure. Check VPN access and the current endpoint with the
operator when needed. Retry after a concrete correction; do not loop on an
unchanged failure. A browser shell opening does not prove a query succeeds.
A connectivity failure is not fixed by increasing the query timeout. Report the
blocker and needed correction, without claiming a report was generated.

## Generate and verify

Run from the checkout root with the selected version, date, source, and output
directory. Use `.venv/bin/python bin/pharmsub_report.py --help` if options need
checking. This is a production example; replace its release values as needed:

```sh
.venv/bin/python bin/pharmsub_report.py --version 26.10d --release-date 20261112 --endpoint http://ncidb-p335-c.nci.nih.gov:3030/NCIT2/query --output-dir ./output
```

Use `--previous-report` when a previous generated report is supplied or can be
reliably identified. Surface any difference in source environment when comparing
releases. Never require historical row counts to remain fixed.

A full run can take several minutes; the November 2026 dev examples took about
six minutes each. Keep the operator informed and wait for the process to finish.
For an explicit rerun, use a fresh output directory under `output/`; preserve
existing bundles and keep the requested version/date unchanged. Do not delete
an existing output to bypass the script's overwrite protection.

Successful generation produces one directory named
`NCIT_PharmSub_VERSION_RELEASEDATE/`, containing `.xlsx`, `.results.json`, `.rq`,
and `.report.json` files with that same stem. Require successful process exit
and inspect the report: `status` must be `validated`,
`all_values_and_string_types_match` must be true, and the version, date, source,
and counts must agree with the requested run. Verify recorded checksums if
files are moved. A running process or an existing filename is not success.

Preserve every raw string and row, including repeated Concept_ID values,
synonym/source combinations, Unicode, numeric-looking identifiers, and blanks.
The generator reopens the saved workbook and checks every value and populated
cell's text type. Do not rebuild the workbook using Excel imports or a different
spreadsheet authoring path. When comparing a reference, treat empty optional
strings as blanks and ignore ordering among tied sort keys. Investigate other
differences against raw JSON; do not reproduce reference date/number conversion
or character encoding errors. Do not require a reference workbook to generate.

## Hand over the result

Return the actual **absolute XLSX path**, a clickable link when supported,
version/date, production/dev/replay source, row and concept counts, and relevant
count changes. Include a copyable absolute path, not an abbreviated folder name.
State any unresolved content-QA status and distinguish local generation from
public publication. Retain the raw JSON, rendered query, and validation report
with the workbook.

This skill ends at local generation. Upload and public synchronization remain
separate: the transfer method and publication path mapping in the run guide
need confirmation before automation. Do not upload, trigger synchronization,
modify Jena, or commit/push repository changes as a side effect of creating a
report. Handle any separately requested publication work with its own context.
