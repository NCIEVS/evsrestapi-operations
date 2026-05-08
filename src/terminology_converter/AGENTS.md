# Scope

This package contains Python code for converting source terminology files into simple intermediate files and then OWL.

# Package Architecture

- `models/` defines Pydantic models for rows consumed by the OWL converter.
- `converter/` contains source-specific converters, shared simple-format utilities, and the OWL writer.

# Simple Format Contract

The package-level intermediate format is a set of pipe-delimited files:

- `concepts.txt`: concept code, semantic type, preferred name, and optional synonyms.
- `attributes.txt`: concept code, attribute type, value.
- `parChd.txt`: parent code, child code.
- `relationships.txt`: relationship rows used for OWL restrictions when present.

These files are the boundary between source-specific converters and the OWL writer. Keep changes compatible across both sides of that boundary.

# Models And Shared Contracts

`models/terminology.py` defines the fields and ordering expected when loading simple-format rows. If a model changes, update the simple-format producers, `OwlConverter`, and tests together.

# Subdirectory Contexts

- `converter/AGENTS.md`: converter implementation patterns, CLI behavior, and OWL writer details.

# Core Files

- `models/terminology.py`
