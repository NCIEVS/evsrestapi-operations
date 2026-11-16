# Upgrade and run operations

If you're used to the evsrestapi scripts, start with
[Switching from evsrestapi indexing](switching-from-evsrestapi.md). This page has the details.

## Upgrade notes

- Build operations from a matching evsrestapi checkout. The build compiles
  `evsrestapi-core` from that checkout; no Maven repository is needed. Rebuilding the
  server does not rebuild the loader, so rebuild operations after changing core.
- `OPS_STATE_DIR` holds the lock, API job history, and logs. Use one for every script
  and API process on the host, and keep it across upgrades.
- Existing indexes keep working; this change alone does not require a reindex.
- Call scripts from operations directly; the old evsrestapi script paths and
  `make devreset` target have been removed.

## Install and configure

Build as described in the [README](../README.md#building-scripts) and unzip the result
into the operations installation, so that `bin/`, `lib/`, `config/`, and `data/` are
directly under `EVS_OPS_HOME`. Gradle and the source checkouts are not needed at
runtime. `build-info.json` records the evsrestapi and operations commits the ZIP was
built from; deploy a server and operations built from the same pair. The operations
CI workflow uses the full commit SHA supplied by the manual `evsrestapi_ref` input
or the `EVSRESTAPI_CORE_REF` repository variable. When neither is set, it uses the
matching branch name in evsrestapi. It resolves that branch once and pins all three
platform jobs to the resulting SHA, recorded in the job summary. A matching branch
must exist and contain `evsrestapi-core`; CI does not fall back to an unrelated
default branch. Set an explicit SHA for release builds or operations-only branches.

The scripts and the API read the existing
`${APP_HOME:-/local/content/evsrestapi}/config/setenv.sh` (or
`$APP_HOME/$APP_NAME/config/setenv.sh`), so cron jobs need no wrapper. Add these
settings to it:

```bash
export JAVA_HOME=/path/to/jdk-25
export EVS_OPS_HOME=/local/content/evsrestapi-operations
export OPS_STATE_DIR=/local/content/evsrestapi/config/operations-state
export JAVA_OPTS='-Xmx4096M'

# Required only when running the private API:
export ADMIN_KEY='replace-with-a-private-random-value'
```

The `config/setenv-*.sh_orig` templates include these settings. Put `OPS_STATE_DIR`
on a local disk the service account can write to, outside anything a deployment
replaces. `JAVA_OPTS` sets the loader JVM options; `ADMIN_JAVA_OPTS` sets the API JVM
options (default `-Xmx512m`).

To use the scripts or the curl examples below from a shell, load the file first:

```bash
source "${APP_HOME:-/local/content/evsrestapi}/config/setenv.sh"
cd "$EVS_OPS_HOME"
```

`OPS_PYTHON` and `OPS_BASH` replace `python3` and `bash` if needed. The shell bootstrap
keeps the invoking Bash executable, so native Windows Python does not resolve bare
`bash` to the WSL launcher. In Git Bash on Windows, use native Python and
forward-slash paths. To select Git Bash explicitly:

```bash
export OPS_BASH='C:/Program Files/Git/bin/bash.exe'
"$OPS_BASH" "$EVS_OPS_HOME/bin/devreset.sh" "$INDEX_DATA_ROOT"
```

Use that explicit executable for the outer command as well if `bash` on PATH starts
WSL. `wsl: Failed to translate ...` followed by a missing `process_exec.sh` is a
sign of mixed Windows/WSL execution; a Windows `D:/...` path belongs to Git Bash
and native Python, while WSL uses `/mnt/d/...` and Linux runtimes.

The transforms create a Python
virtual environment for each run, so Python needs venv, pip, and access to the package
index.

`CONFIG_BASE_URI` works as before. It can be an HTTP(S) URL or a
`file:///absolute/path/to/config/metadata` URL.

Loader settings:

- With `--noconfig`, the loader uses its local profile: development metadata,
  250-concept batches, and a query URL built from `GRAPH_DB`. It ignores
  `GRAPH_DB_MONTHLY_QUERY_URL`.
- Without `--noconfig`, it uses main-branch metadata and 1,000-concept batches. Leave
  `GRAPH_DB_MONTHLY_QUERY_URL` unset for operations: it fixes the query URL, so
  scripts that switch `GRAPH_DB` would keep querying the same database.
- The existing batch-size and metadata environment variables still override these.
- `GRAPH_DB_BATCH_TIMEOUT` (seconds, default 900) is how long the loader waits for one
  batch of concepts before it fails the load.

## Run scripts directly

The scripts take the same arguments as before. Neither the API nor the REST server
needs to be running, but the graph database and OpenSearch do. From the operations
installation:

```bash
bin/reindex.sh --terminology ncit
bin/list.sh --es --quiet
```

On scripts that have it, `--noconfig` uses your shell environment instead of
setenv.sh. Relative paths resolve from your working directory. API jobs run from
`EVS_OPS_HOME`, so use absolute paths in API calls; files a script writes to its working
directory, such as `report.txt`, also end up there. Transforms print the generated
file's path as their last line of output.

`reindex.sh --terminology NAME` loads only that terminology, but still removes stale
indexes and updates the latest flags for all terminologies. It skips indexes that
already exist; it does not force a rebuild.

For a full reset, build the loader with `(cd web && ./gradlew loaderJar)`, then run
`bin/devreset.sh /absolute/path/to/UnitTestData` from operations. The script checks
that the loader JAR and Java work before it changes the graph database or OpenSearch.
`reindex.sh`, `ncim.sh`, `ncim-part.sh`, and `report.sh` make the same check first.

## Start the private API

The API is optional and runs as a Linux service. The scripts also work on macOS and in
Git Bash on Windows. API settings are in `application.properties`; loader settings are
in `loader.properties`.

```bash
bin/evsrestapi-operations foreground
# Or: bin/evsrestapi-operations start|stop|restart|status
```

The API does not start without a non-blank `ADMIN_KEY`. It listens on
`127.0.0.1:8083` by default (`ADMIN_BIND` and `ADMIN_PORT` change this). It starts and
serves job history without the graph database or OpenSearch. With `start`, its log is
`$OPS_STATE_DIR/logs/admin.log`.

For systemd, edit the user and paths in `bin/evsrestapi-operations.service`, then:

```bash
sudo cp bin/evsrestapi-operations.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now evsrestapi-operations
```

Keep the port private, and leave access logging off: the key is sent in the query
string. To reach the API from another machine, use an SSH tunnel:

```bash
ssh -N -L 8083:127.0.0.1:8083 operations-host
```

## API calls

Every request needs the `apiKey` query parameter. `exec` runs a registered script with
a list of arguments, which are passed as-is and never interpreted by a shell.
`GET /admin/commands` lists each command's name, script, usage, and `mutation` flag
(`true` means it takes the lock). The [command reference](workflow-contracts.md) maps
commands to scripts.

| Endpoint | Purpose |
|---|---|
| `GET /admin/commands` | Available commands and arguments |
| `POST /admin/exec` | Run `{"command":"name","args":["argument",...]}` |
| `GET /admin/processes?page=0&size=20` | API job history; size 1–100 |
| `GET /admin/processes/{id}` | State, timestamps, exit code, and available output |
| `GET /admin/processes/{id}/log` | Output chunk, or plain text with `full=true` |

List commands, run a short command, then submit indexing and poll it:

```bash
api='http://127.0.0.1:8083/admin'
api_key=$(printf '%s' "$ADMIN_KEY" | jq -sRr @uri)
curl -fsS "$api/commands?apiKey=$api_key"

# Short commands return their output in the response.
curl -fsS "$api/exec?apiKey=$api_key" -H 'Content-Type: application/json' \
  -d '{"command":"list","args":["--es","--quiet"]}' | jq -r .output

# Long commands: submit in the background, then poll.
job_id=$(curl -fsS "$api/exec?apiKey=$api_key&background=true" \
  -H 'Content-Type: application/json' \
  -d '{"command":"reindex","args":["--terminology","ncit"]}' | jq -er .id)

curl -fsS "$api/processes/$job_id?apiKey=$api_key"
curl -fsS "$api/processes/$job_id/log?apiKey=$api_key&full=true" > process.log
```

By default `exec` waits up to `OPS_WAIT_SECONDS` (default 300). A job that finishes
in that time returns 200 with up to 1 MiB of output; check `state` and `exitCode`
for command failure. A job still running returns 202 and keeps running; poll its
process URL. Add `&background=true` to return 202 immediately.
`outputTruncated=true` means the rest is available from the log endpoint.

To read a log in pieces, pass `offset` and `limit` (up to 1 MiB). The response has
`output`, `nextOffset`, and `complete`; pass `nextOffset` as the next `offset`. Errors
are 400 for bad arguments, 401 for a missing or wrong key, 404 for an unknown job, and
409 when another data-changing job is running or a job's process survived a restart.

## Jobs, locking, and recovery

Only one data-changing command runs at a time on a host, whether it was started from
a script or the API. A second one exits with code 75 from the command line and gets
409 from the API. Read-only commands (`list`, `audit`, `report`, `qa`, the sampling
commands, and `load-testing`) do not take the lock. Every caller must use the same
`OPS_STATE_DIR`. Do not run indexing from an older evsrestapi release on the same
host; it does not use this lock.

Job history covers API calls only. States are `STARTING`, `RUNNING`, `SUCCEEDED`,
`FAILED`, and `INTERRUPTED`. A job's stdout and stderr are written to its log as they
arrive. Finished jobs are kept for `OPS_RETENTION_DAYS` (default 30).

Stopping the service stops the jobs it started (on Linux, the whole process group).
After a restart, unfinished jobs show as `INTERRUPTED`, and a job process that is
still alive blocks new data-changing jobs. Check the log and the backends before
retrying. Nothing is rolled back and nothing is retried automatically.

To upgrade or roll back, stop new submissions, let running jobs finish or stop them,
keep `OPS_STATE_DIR`, and switch the server, operations, and scheduled jobs together.
Keep the previous artifacts. If a job was interrupted partway, check and repair its
data separately.
