# Command reference

Each API command runs one script in `bin/`. API callers pass the script's arguments as
a JSON array, in the same order as on the command line. Run a script with `--help`, or
with no arguments, to see its full usage. API jobs run from `EVS_OPS_HOME`, so
relative paths in API arguments resolve from there.

| API command | Script | Arguments |
|---|---|---|
| load | stardog_load.sh | `[--noconfig] [--force] [--weekly] <file-or-url>` |
| bulk-load | bulk_load.sh | `[--noconfig] [--force]` |
| reindex | reindex.sh | `[--noconfig] [--history file] [--terminology name]` |
| ncim | ncim.sh | `[--download]` |
| ncim-part | ncim-part.sh | `[--noconfig] [--download] [--keep] [--terminology name] [RRF-directory]` |
| devreset | devreset.sh | `[--test-reconcile] <UnitTestData-directory>` |
| load-local | load.sh | `<UnitTestData-directory>` |
| report | report.sh | `[--noconfig] [--list] [<database> <terminology> <version>]` |
| list | list.sh | `[--noconfig] [--quiet] [--graphdb] [--es]` |
| remove | remove.sh | `[--noconfig] <terminology> <version> --graphdb\|--es`, or `--mapset <code>` |
| metadata | metadata.sh | `[--noconfig] <terminology> <version> <config>` |
| init | init.sh | `[--noconfig] [--quiet]` |
| audit | audit.sh | `[--noconfig] [--csv\|--tsv] [--recent] <load\|stats\|error\|warning\|all> [terminology]` |
| command | run_command.sh | `[--noconfig] <print_env\|list\|remove\|patch\|metadata\|init\|audit\|drop_ctrp_db\|list_compaction_tasks> ...` |
| qa | stardog_qa.sh | `<terminology> <OWL-file> <weekly-flag> <input-directory>` |
| owl-sampling | owl_sampling.sh (runs owl_sampling.py) | `<OWL-file> <terminology-JSON> [--output file] [--terminology name] [--report file]` |
| rrf-sampling | rrf_sampling.sh (runs rrf_sampling.py) | `<RRF-directory> <config-directory> <terminology>` |
| java-rrf-sampling | java_rrf_sampling.sh | `<inputPath> <list-file> <terminologies> [codesab\|cui]` |
| load-testing | load_testing.sh (runs load_testing.py) | `[--url url] [--time ms] [--calls count]` |
| cdisc-form-update | cdisc_form_update.sh | `<codes-file>` |
| transform-hgnc, transform-canmed, transform-medrt | transforms/hgnc.sh, canmed.sh, medrt.sh | `<input-file> <process-id> [ontology-URL]` |
| transform-umlssemnet | transforms/umlssemnet.sh | `<input-file> <process-id> [version] [ontology-URL]` |

`list`, `audit`, `report`, `qa`, `owl-sampling`, `rrf-sampling`, `java-rrf-sampling`, and
`load-testing` only read data or write local files. All other commands take the lock
described in [Jobs, locking, and recovery](operations-api.md#jobs-locking-and-recovery).

`load` runs the matching transform in `bin/transforms` when a terminology needs one.
Transforms work in `bin/work_$PID` and print the generated OWL file's path as their
last line. `command patch <version> ...` runs the versioned patches.

`audit.sh` used to exist in both repositories; the evsrestapi copy now forwards here.
These are not available through the API: the Stardog `CTRP_Weekly.sh` and
`NCIEVS_Monthly.sh` templates, scripts under `legacy/`, packaging, and starting or
stopping the API service.
