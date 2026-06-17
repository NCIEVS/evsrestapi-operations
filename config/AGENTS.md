# Scope

This directory contains runtime configuration templates, terminology metadata, transform configuration, and ignored-source lists consumed by operations scripts and downstream EVS indexing/loading workflows.

# Configuration Families

- Environment templates define graph database and Elasticsearch variables.
- Metadata files describe terminology and mapset behavior for loaders and consumers.
- Transform configuration supports terminology-specific conversion assets.
- Ignored-source files filter ontology source URLs from graph listing and related workflows.

# Environment Templates

`setenv-stardog.sh_orig` and `setenv-jena.sh_orig` document the expected variables for local or server runs. Local `setenv.sh` files are intentionally ignored and must not be committed.

# Subdirectory Contexts

- `metadata/AGENTS.md`: terminology JSON, HTML welcome text, mapset metadata, and ignored source metadata.
- `transforms/hgnc/AGENTS.md`: HGNC transform property files.

# Core Files

- `setenv-stardog.sh_orig`: Stardog environment template.
- `setenv-jena.sh_orig`: Jena/Fuseki environment template.
- `ignore-source.txt`: top-level ignored source list.
