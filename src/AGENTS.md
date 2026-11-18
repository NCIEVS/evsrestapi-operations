# Scope

This directory contains the active `terminology_converter` Python package.

# Python Source Boundaries

Keep import paths consistent with the existing Poetry package layout. Package code should live under `src/terminology_converter/`; operational Python helpers that are only called by shell scripts should stay in `bin/`.

# Subdirectory Contexts

- `terminology_converter/AGENTS.md`: package-level converter contracts and model boundaries.
