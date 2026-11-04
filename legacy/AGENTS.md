# Scope

This directory contains archived operational scripts, JARs, config files, and helper binaries retained for historical or compatibility reasons.

# Legacy Status

Do not modernize or reorganize this directory as part of active loader or converter work unless the task specifically targets legacy behavior. Prefer changing active code in `bin/`, `src/`, or `config/` when possible.

# Legacy Script And JAR Patterns

Legacy shell scripts often assume fixed server layouts, old Java/JAR tooling, and external binaries. Preserve those assumptions unless the requested change includes a migration plan.

# Config Coupling

Subdirectories such as `OWLDiff`, `OWLScrubber`, and `OWLSummary` include local config files paired with their JARs. Keep config changes scoped to the tool that consumes them.

# Entry Points And Core Artifacts

- `Master*.sh`, `BaselineFTP.sh`, `TestFTP.sh`, and `extractBranches_md5*.sh`: historical operational scripts.
- `GenerateOWLAPIInferred/`: inferred OWL generation JARs and runner.
- `OWLDiff/`: OWL diff JAR and config.
- `OWLScrubber/`: OWL scrubber JAR, properties, config, and helper scripts.
- `OWLSummary/`: OWL summary JAR and runner.
- `legacy/bin/`: retained helper binaries.
