# Project Overview

This repository contains EVSRESTAPI operations assets: shell entry points, Python terminology converters, configuration metadata, mapping data, and legacy tooling used to prepare, validate, load, remove, and describe EVS terminology content.

# Global Architecture

- `bin/` contains operational scripts for local/server workflows, graph database loading, metadata updates, removal, listing, initialization, QA, sampling, and transform orchestration.
- `src/` contains Python source code, including the `terminology_converter` package for converting selected terminology source files into a simple pipe-delimited format and then OWL.
- `config/` contains environment templates, terminology metadata, mapset metadata, ignored-source lists, and transform configuration assets.
- `data/` contains checked-in mapping data used by EVS mapset workflows.
- `test/` contains pytest coverage and fixtures for active converter behavior.
- `legacy/` and `lib/` contain archived scripts, JARs, and vendored artifacts that are still packaged or retained for operational compatibility.

# Build And Test Commands

- Install Python dependencies with `poetry install`.
- Run tests with `poetry run pytest`.
- Build the operations zip with `make clean build`.
- Run the primary loader through `bin/stardog_load.sh`; use `--help` on scripts before changing or invoking destructive paths.

# Global Coding Standards

- Prefer the existing shell and Python patterns already used in the touched directory.
- Keep operational scripts portable across the supported local/server layouts; preserve the existing `--noconfig` behavior where present.
- Treat committed metadata, mapping files, JARs, and generated OWL outputs as operational artifacts. Do not reformat or regenerate broad data files as part of unrelated code changes.
- Keep generated local files out of commits, including `bin/work_*`, `__pycache__`, `.pytest_cache`, local `config/setenv.sh`, logs, and build output.
- For Python converter changes, preserve the simple-format file contract consumed by `OwlConverter` unless the caller and tests are updated together.

# Context Map

- `bin/AGENTS.md`: active operational shell/Python entry points.
- `bin/transforms/AGENTS.md`: per-terminology transform wrappers called during load.
- `bin/patches/AGENTS.md`: versioned operational patch packages.
- `config/AGENTS.md`: environment templates and configuration layout.
- `config/metadata/AGENTS.md`: terminology and mapset metadata files.
- `config/transforms/hgnc/AGENTS.md`: HGNC transform property files.
- `data/mappings/AGENTS.md`: checked-in mapping data files.
- `src/AGENTS.md`: Python source tree boundaries.
- `src/terminology_converter/AGENTS.md`: terminology converter package contracts.
- `src/terminology_converter/converter/AGENTS.md`: converter implementations and OWL writer behavior.
- `test/AGENTS.md`: pytest and fixture guidance.
- `legacy/AGENTS.md`: archived shell/JAR workflows.
- `lib/AGENTS.md`: vendored library artifacts.
