# Scope

This directory contains active operational entry points for EVSRESTAPI operations. Most scripts are shell wrappers around graph database, Elasticsearch, metadata, QA, and transform workflows. The Python files here are standalone operational utilities, not part of the `terminology_converter` package.

# Operational Flow

`stardog_load.sh` is the main load orchestrator. It accepts local files or URLs, stages input under `bin/work_$PID`, applies a transform when needed, derives terminology/version/graph information from OWL content, runs QA, loads graph data, removes old versions, and performs optimization/compaction when configured.

`run_command.sh` dispatches command-style operations such as `print_env`, `list`, `remove`, `patch`, `metadata`, `drop_ctrp_db`, `init`, and `list_compaction_tasks`.

# Script Patterns

- Scripts derive `DIR` from their own path and call sibling scripts by absolute path.
- Scripts commonly support `--noconfig` to use environment variables directly instead of sourcing the server config file.
- Server-configured runs default through `APP_HOME=/local/content/evsrestapi` and source `${APP_HOME}/config/setenv.sh`.
- Preserve explicit validation and failure exits before making remote graph database or Elasticsearch changes.
- Keep credential logging masked when adding diagnostics.

# Configuration And Environment

The active graph database type is controlled by `GRAPH_DB_TYPE`, with Stardog and Jena/Fuseki branches in several scripts. Elasticsearch access is assembled from `ES_SCHEME`, `ES_HOST`, and `ES_PORT`.

Do not commit local environment files or secrets. Use the templates in `config/` for documented shape only.

# Entry Points And Core Logic

- `stardog_load.sh`: primary load, transform, QA, graph load, cleanup, and retention workflow.
- `run_command.sh`: command dispatcher used directly and by the loader.
- `list.sh`: graph database and Elasticsearch inventory.
- `remove.sh`: terminology, graph, Elasticsearch, and mapset removal.
- `metadata.sh`: metadata document update workflow.
- `init.sh`: configuration index and default database initialization.
- `stardog_qa.sh`: pre-load content checks.
- `bulk_load.sh`: scripted batch load list.
- `get_databases.py` and `get_graphs.py`: JSON parsing helpers for shell pipelines.
- `owl_sampling.py`, `rrf_sampling.py`, and `load_testing.py`: standalone analysis/load-test utilities.

# Subdirectory Contexts

- `transforms/AGENTS.md`: per-terminology transform wrappers and their working-directory contract.
- `patches/AGENTS.md`: versioned patch workflow and patch safety guidance.
