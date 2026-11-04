# Scope

This directory contains versioned operational patch packages invoked through the command dispatcher. Patches are for one-off or release-specific operational updates, not for normal reusable loader logic.

# Versioned Patch Pattern

Each patch version lives under a version-named directory such as `2.2.0/`. The dispatcher runs that directory's `run.sh` through `bin/run_command.sh patch <version>`.

# Patch Safety Rules

- Keep patches self-contained inside their versioned directory.
- Resolve paths relative to the patch script or the repository `bin/` directory.
- Validate required files before mutating anything.
- Make patch scripts repeatable when possible; if a patch cannot be idempotent, document the reason in the script.
- Do not hide failures from unzip, chmod, child scripts, or remote operations.

# Entry Points

- `2.2.0/run.sh`: unpacks FHIR transform assets and runs the included update script.
