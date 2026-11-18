# Upload and promote a PharmSub workbook

Use this procedure when the operator asks to upload or publish a report.
A request to generate a report or edit these instructions does not itself
request publication. Give instructions when asked for guidance; carry out
publication steps only within the operator's actual request and available access.

## 1. Identify the approved file

Use the selected release's exact `.xlsx` path. For a generated bundle, inspect
its `.report.json`: require `validated`, matching version/date, and matching
workbook SHA-256. Recover the audit bundle or ask for validation context if only
a copied workbook is provided. Establish completed release content QA and the
operator's publication intent from existing context; ask only for missing facts.

Check the recorded source. Dev and replay outputs are not automatically approved
production releases. If approval of that particular source/file is unclear,
resolve it before publication. Preserve the real source metadata even when an
exception has been explicitly approved. Upload **only the workbook**; keep raw
results, queries, reports, and private release records out of the public folder.

If an existing destination file has the same name, compare it when possible.
Identical bytes need no replacement. A different existing file requires clear
replacement intent; do not overwrite it merely because this is a new local run.
Keep any required backup outside the mirrored public tree.

## 2. Upload to the internal FTP server

The operator confirmed this FTP profile and remote folder on 2026-11-17:

| FTP client setting | Value |
| --- | --- |
| Protocol | FTP - File Transfer Protocol |
| Host | `ncias-p3388-v.nci.nih.gov` |
| Port | Leave blank, as in the existing profile |
| Encryption | Use explicit FTP over TLS if available |
| Logon type | Normal |
| User | `cacore` |
| Password | Operator's existing credential; never include it in the skill or chat |
| Remote site | `/ftp/ftpcacore/pub/cacore/EVS/NCI_Thesaurus/Branches` |

Use the approved saved profile in the FTP client (for example, FileZilla).
This profile is FTP with the explicit TLS option shown, not an SFTP/SSH login.
Do not guess an SSH account, obtain the password from the screenshot, or bypass
certificate/security warnings. Let the operator resolve authentication directly
in the client if secure credential access is unavailable to Codex.

1. Connect from the required NIH/NCI network or VPN.
2. Paste the exact **Remote site** path above and verify the displayed folder.
   Do not create a lookalike folder elsewhere if navigation fails.
3. Select the approved local workbook on the local side. Transfer it in binary
   mode, keeping the complete original filename, version, and release date.
4. Use the established staging/rename procedure when available. The sync also
   runs on a schedule: avoid exposing an incomplete upload during a concurrent
   sync, and keep staging files/backups outside the mirrored public tree.
5. Wait for a completed transfer with no failed queue entry. Verify the remote
   filename and byte size. For byte verification, use an approved remote checksum
   facility or download the uploaded file into a separate local verification
   directory and compare SHA-256 with the validated original.

If FTP access, permissions, or the upload fails, stop here and report the actual
state. Do not trigger public synchronization after a partial or failed upload.
The GitHub action does not transfer the workbook from the operator's computer.

## 3. Verify the upload feeds the sync source

The current production action reads:

```text
ncils-av-62s9yh:/share/content/evs/ftp1
```

The workbook must therefore be available in this source view:

```text
/share/content/evs/ftp1/NCI_Thesaurus/Branches/WORKBOOK_FILENAME.xlsx
```

The FTP host/path and this workflow host/path are different views. Their names
alone do not prove the share mapping. Confirm the approved mapping with existing
operations records/administrator context, or verify that the same complete file
is visible in the workflow source with matching bytes/checksum using authorized
access. Operators do not need the workflow service account's SSH key; do not
extract runner credentials or invent a mount, symlink, or second upload location.

If the mapping is unconfirmed and the source cannot be checked, report
**uploaded internally; promotion not started**, and identify the required
operations confirmation. Do not present an unverified route as a working one.

## 4. Run the production GitHub action

Use the workflow in **CBIIT/evs-utils**, not the report generator's repository:

[EVS NFS to AWS S3 Sync in Prod](https://github.com/CBIIT/evs-utils/actions/workflows/evs-ftp-s3sync-prod.yaml)

The [workflow source](https://github.com/CBIIT/evs-utils/blob/main/.github/workflows/evs-ftp-s3sync-prod.yaml)
was inspected on 2026-11-17 (file blob `dc3de7bb035419056fce321c3f8ce11278b59260`).
Re-read its current source/inputs before dispatching. At that review:

- Workflow file: `evs-ftp-s3sync-prod.yaml`; production ref: `main`.
- Manual `workflow_dispatch` is supported, with no release/file input fields.
- It mirrors the entire `ftp1` tree to
  `s3://cbiit-evs-drupaldocker-prod/evs/ftp1`, using `aws s3 sync --delete`.
- It also has scheduled weekday runs.
- Sync warnings (exit code 2) are treated as success, so green status alone does
  not prove the requested workbook was copied.

The log message `Source validation passed` only establishes that the
`NCI_Thesaurus` directory contains more than eight files within depth three.
It does not verify this workbook's presence or the completeness of `ftp1`;
retain the specific uploaded-file/source check above.

Explain the whole-tree sync/delete scope before running it. Proceed when the
operator's request authorizes this production promotion; do not repeat an
already-satisfied authorization question. An upload-only request does not imply
permission to dispatch the action. If the source mount is missing, incomplete,
or unexpectedly empty, stop rather than running a destructive mirror.
Do not change the workflow, bucket, credentials, or permissions for this report.

### Browser steps

1. Open the workflow link and sign in with an account authorized to run it.
2. Select **Run workflow** and choose **main** in the branch selector.
3. After the upload/source checks above, select **Run workflow** once.
4. Open that new manual run. Record its run URL/ID, actor/time, and ref; distinguish
   it from scheduled or other operators' runs. If the button is missing or access
   is denied, have an administrator resolve access rather than bypassing it.
5. Wait for completed/success, then inspect the source-validation and sync logs
   for skipped files, warnings, or transfer errors affecting this workbook.

### Optional GitHub CLI

Prefer a connected GitHub tool if it supports the required action. The CLI is
optional; operators can use the browser above. With an already-authorized `gh`
session, the equivalent dispatch is:

```sh
gh workflow run evs-ftp-s3sync-prod.yaml --repo CBIIT/evs-utils --ref main
```

Capture the returned run URL when available. Otherwise identify the newly created
manual run by workflow, actor/time, and ref before following it; do not blindly
choose the latest run. Do not dispatch again just because a run URL is delayed.
For a selected run ID, poll in bounded intervals and keep the operator informed:

```sh
gh run view "$PHARMSUB_RUN_ID" --repo CBIIT/evs-utils --json status,conclusion,url
```

Require `status=completed` and `conclusion=success`; a pending command's zero exit
status is insufficient. If failed, cancelled, or stuck, preserve the run URL and
explain the failure. Correct its cause before considering another dispatch.
[GitHub CLI command reference](https://cli.github.com/manual/gh_workflow_run)

## 5. Verify the public workbook

The public download pattern is:

```text
https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/Branches/WORKBOOK_FILENAME.xlsx
```

For example, the existing October filename is
`NCIT_PharmSub_26.10d_20261112.xlsx`. Use the operator's selected filename, not
that example as a default. The public site is served over HTTPS; this URL is
where to verify publication, regardless of the internal FTP protocol.

Download that exact URL to a separate verification location and compare its
SHA-256 with the approved local workbook. Codex can perform this check. Optional
Mac/Linux commands, after setting the selected filename/paths, are:

```sh
curl --fail --location --silent --show-error --connect-timeout 10 --max-time 120 --output "$PHARMSUB_PUBLIC_COPY" "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/Branches/$PHARMSUB_FILENAME"
shasum -a 256 "$PHARMSUB_LOCAL_XLSX" "$PHARMSUB_PUBLIC_COPY"
```

The verification copy must differ from the original path so a failed download
cannot overwrite the validated workbook. On Windows, `Get-FileHash -Algorithm
SHA256` provides the same check. Downloading an HTML error/login page, finding a
directory entry, matching a timestamp, or receiving HTTP 200 is not sufficient.
Do not substitute an S3 ETag for the workbook's SHA-256.

If a green action is followed by a missing or different public file, check the
source view, sync warnings, exact key/filename, and CDN caching. Use bounded
read-only retries for propagation; report verification pending if it still does
not match. Do not repeatedly run the whole sync, delete the public file, change
the release date, or invalidate caches without an identified need and scope.

## Completion record

Report the uploaded filename/internal destination, workflow run URL/ID and
terminal result, public workbook URL, and whether the downloaded SHA-256 matches
the approved local file. Keep release version/date, actual data-source environment,
and content-QA context with that evidence. Preserve the generator's original
source and checksum records. Distinguish **uploaded internally**, **sync started**,
**sync succeeded**, and **public download verified**; claim publication complete
only after the last check.
