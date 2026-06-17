# Scope

This directory contains Python source code. The active package is `terminology_converter`; standalone analysis scripts at this level are not package modules unless explicitly wired into tests or operations scripts.

# Python Source Boundaries

Keep import paths consistent with the existing Poetry package layout. Package code should live under `src/terminology_converter/`; operational Python helpers that are only called by shell scripts should stay in `bin/`.

# One-Off Analysis Scripts

`analyze_medrt_xpath.py` is a local MED-RT analysis utility with hard-coded input paths. Treat it as exploratory support code unless the task explicitly asks to productize it.

# Subdirectory Contexts

- `terminology_converter/AGENTS.md`: package-level converter contracts and model boundaries.
