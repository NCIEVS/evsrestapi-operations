# Scope

This directory contains per-terminology transform wrappers invoked by `bin/stardog_load.sh` when incoming data is not already a loadable OWL file.

# Transform Pipeline

Each transform wrapper stages work under `bin/work_$PID`, creates a local virtual environment, installs Poetry, installs this repository, runs a terminology-specific Python converter, and then runs `owl_file_converter.py` to produce OWL.

The final line printed by a transform is expected to be the generated OWL file path. `stardog_load.sh` parses that final line, moves or renames the file, and continues the graph load workflow.

# Per-Terminology Wrappers

- `hgnc.sh`: converts an HGNC TSV download into simple format and then HGNC OWL.
- `canmed.sh`: expects paired HCPCS and NDC CSV inputs and generates CanMED OWL.
- `medrt.sh`: finds the MED-RT XML input, converts it, and uses the XML version value for the OWL filename.
- `umlssemnet.sh`: expects `SRDEF`, `SRSTRE1`, and `SRSTR` files and generates UMLS Semantic Network OWL.

# Working Directory Pattern

Transforms use:

- `WORK_DIRECTORY=$EVS_OPS_HOME/bin/work_$PID`
- `INPUT_DIRECTORY=$WORK_DIRECTORY/input`
- `OUTPUT_DIRECTORY=$WORK_DIRECTORY/output`
- `VENV_DIRECTORY=$WORK_DIRECTORY/venv`

Preserve this layout because the parent loader owns staging and cleanup.

# Entry Points

The shell wrappers in this directory call Python modules under `src/terminology_converter/converter/`. Keep wrapper argument handling aligned with those modules' CLI options.
