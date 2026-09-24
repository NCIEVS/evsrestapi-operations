# Scope

This directory contains pytest coverage for active terminology converters and OWL generation.

# Test Strategy

Tests exercise converter output at two levels: simple-format file creation and generated OWL structure. Keep assertions focused on stable counts, representative attributes, hierarchy relationships, and OWL metadata.

# Fixture Policy

Fixtures under `test/fixtures/` are intentionally representative source inputs. Do not reformat or shrink large fixtures unless the expected converter behavior and assertions are updated together.

# Expected Output Assertions

Use `tmp_path` for converter output. Tests should verify the standard files exist, then inspect pipe-delimited rows and OWL XML output.

# Entry Points

- `hgnc_test.py`
- `canmed_test.py`
- `umls_sem_net_test.py`
