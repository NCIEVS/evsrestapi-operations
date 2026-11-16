# Switching from evsrestapi indexing

Indexing moved from evsrestapi to evsrestapi-operations. The scripts keep their names and
arguments; evsrestapi is now only the server. Existing indexes keep working, so no
reindex is needed for the switch.

## Set up a host (once)

1. Build in evsrestapi-operations. This needs Java 25 and the evsrestapi checkout next
   to it:

   ```bash
   make build    # writes build/evsrestapi-operations-<version>.zip
   ```

2. Install it:

   ```bash
   unzip build/evsrestapi-operations-<version>.zip -d /local/content/evsrestapi-operations
   ```

3. Add these to `/local/content/evsrestapi/config/setenv.sh`, the same file as before:

   ```bash
   export JAVA_HOME=/path/to/jdk-25
   export EVS_OPS_HOME=/local/content/evsrestapi-operations
   export OPS_STATE_DIR=/local/content/evsrestapi/config/operations-state
   ```

   The server launcher uses the same `JAVA_HOME`.

4. Make sure `python3` is installed.

## Running scripts

| Before | Now |
|---|---|
| `/local/content/evsrestapi/evsrestapi/bin/reindex.sh` | `$EVS_OPS_HOME/bin/reindex.sh`, same arguments. Same for `ncim.sh`, `ncim-part.sh`, `report.sh`, `audit.sh`, `load.sh`, and `devreset.sh`. |
| `lib/evsrestapi.jar` | `$EVS_OPS_HOME/lib/evsrestapi-loader.jar`. Scripts find it, so they can run from any directory. |
| Java 17 from `/usr/local/corretto-jdk17` | Java 25 from `JAVA_HOME` in setenv.sh. |

The old paths still work for one release. They print `Deprecated: use <new path>` on
stderr, then run the new script with the same arguments and exit code.

## Local development

Keep the two checkouts side by side:

```text
workspace/evsrestapi
workspace/evsrestapi-operations
```

Full reset, as before. This builds the loader in `../evsrestapi-operations` and runs
in the background:

```bash
cd evsrestapi
make devreset
tail -f log
```

Single scripts: build the loader once, then run from evsrestapi-operations:

```bash
cd evsrestapi-operations/web && ./gradlew loaderJar && cd ..
bin/reindex.sh --noconfig --terminology ncit
```

- `./gradlew rrfSample -P...` now runs in `evsrestapi-operations/web`, with the same
  properties. Give `-PinputPath` as an absolute path.
- After changing `evsrestapi-core`, rebuild the loader with `./gradlew loaderJar`;
  building the server doesn't update it.

## What's different

- Only one data-changing script runs at a time on a host. A second one exits with code
  75. `list.sh`, `audit.sh`, `report.sh`, `stardog_qa.sh`, and the sampling scripts
  aren't affected.
- `reindex.sh`, `ncim.sh`, `ncim-part.sh`, `report.sh`, and `devreset.sh` check the
  loader JAR and Java before they load anything.
- `devreset.sh` and `load.sh` still use only your shell environment, not setenv.sh.

## Errors you might see

| Message | Fix |
|---|---|
| `loader preflight failed; the loader needs Java 25` | Set `JAVA_HOME` in setenv.sh to a Java 25 JDK. |
| `loader JAR not found` | Run `make build` in evsrestapi-operations, or `./gradlew loaderJar` in its `web/`. |
| `evsrestapi-operations not found` | Set `EVS_OPS_HOME` in setenv.sh, or clone evsrestapi-operations next to evsrestapi. |
| `another data-changing operation is running` (exit 75) | Another script holds the lock. Wait for it to finish. |
| `previous worker still exists` | A process from an interrupted run is still alive. Stop it, then retry. |
| `.../setenv.sh does not exist; use --noconfig ...` | Create setenv.sh, or pass `--noconfig` with the settings exported in your shell. |

## Optional: run scripts over HTTP

evsrestapi-operations can also run as a private service that runs these scripts through
an API. Add `export ADMIN_KEY=<value>` to setenv.sh, using a long random hex value (for
example, from `openssl rand -hex 32`). Then:

```bash
$EVS_OPS_HOME/bin/evsrestapi-operations start
curl -s "http://127.0.0.1:8083/admin/exec?apiKey=$ADMIN_KEY" \
  -H 'Content-Type: application/json' -d '{"command":"list","args":["--es","--quiet"]}'
```

See [operations-api.md](operations-api.md) for background jobs, logs, and the systemd
unit.
