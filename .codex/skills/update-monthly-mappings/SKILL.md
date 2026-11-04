---
name: update-monthly-mappings
description: >-
  Ingest new monthly EVS mapping drops in evsrestapi-operations: normalize a raw
  drop file into the canonical data/mappings file, update mapsetMetadata.txt and
  the mapset HTML with the new terminology versions, then commit and propagate
  the change to the develop, stage, and main tier branches. Use when a new
  mapping file (e.g. Aug2026NCItHGNCmap.txt) has been placed in
  data/mappings/ and the monthly mapping update needs to be published.
---

# Update Monthly Mappings

This skill publishes new monthly EVS mapping drops. Most steps are handled by the
bundled script `scripts/update_monthly_mappings.py` (stdlib-only Python, run from
the repo root). The script does the deterministic work and prints JSON; **you**
handle the confirmation/override prompts described below.

Run everything from the `evsrestapi-operations` repo root. Invoke the script as:

```
python3 <skill-dir>/scripts/update_monthly_mappings.py <subcommand> [flags]
```

## 0. Pre-flight gates — stop if any fail

1. **Branch + freshness.** Run `... preflight`. It must report `ok: true` (on
   `develop`, at HEAD, not behind `origin/develop`). If not, **stop** and tell
   the user why (wrong branch, or behind — they must pull/rebase first).
2. **Fresh files present.** Run `... detect`. If `drops` is empty, there is
   nothing to do — report that and stop.
3. **Already done.** For any drop with `already_done: true`, the canonical target
   file already exists — that map's update is complete. Flag it and skip it. If
   *all* drops are already done, stop.

`detect` also reports `ignored` files (non-canonical files with no matching
mapset, e.g. legacy PDQ data) — mention them only if relevant; take no action.

## 1. Per detected drop — confirm, then apply

For each drop in `detect` output that is **not** already done:

1. **[ASK] Confirm the match.** Show the user: raw file → matched `mapset`
   (source/target terminology), the parsed `new_version` (e.g. `August2026`),
   and the `previous_file` it replaces. Ask them to confirm before proceeding.
2. **[ASK] Confirm/override the source version.** Present
   `source_default_version` (from the EVS API, preferring the `monthly`-tagged
   entry). If the lookup failed (`source_default_error`), you must ask the user
   for the value. Let them accept the default or type a different version.
3. **[ASK] Confirm/override the target version.** Same, using
   `target_default_version`.
4. **[AUTO] Apply.** Run:
   ```
   ... apply --mapset <name> --raw <raw_file> --new-version <version> \
             --source-version <chosen> --target-version <chosen>
   ```
   This builds the new canonical file (previous header + raw rows, `\r`
   stripped), deletes the previous version, updates the metadata row (version +
   both terminology versions), and updates the Source/Target version tokens in
   the mapset HTML file.

## 1b. Sync version-only mapsets (SWISSPROT)

`detect` reports `version_sync` — mapsets whose `version` field tracks the
monthly version but have no local data file (e.g. `NCIT_TO_SWISSPROT`).

**[ASK — default yes]** Ask the user whether to also bump these mapsets to the
same `new_version` being published this run (e.g. `August2026`). Default is
**yes**. For each one they approve, run:

```
... sync-version --mapset <name> --new-version <version>
```

If multiple drops were processed and share the same `new_version`, use that. If
they somehow differ, ask the user which version SWISSPROT should track.

## 2. Confirmation gate before committing

**[ASK]** Show a summary of all changes and `git status -s` / `git diff` for the
metadata + HTML edits. Do **not** commit until the user approves. Note that the
raw drop file(s) will be excluded from the commit and kept as a re-run safety net.

## 3. Commit and propagate

1. **[AUTO] Commit + push develop.** Run `... commit`. It stages the canonical
   file(s), metadata, HTML, and deletions (excluding raw drops), computes the
   message month (`Monthly mapping update for <YYYYMM>` — current month, or the
   previous month if within the first couple days of a new month), commits, and
   pushes `develop`. Direct push to `develop` is intended for this routine
   change; ignore the branch-protection PR advisory. Record the returned `sha`.
2. **[AUTO] Propagate to tiers.** Run `... propagate --sha <sha>`. It
   cherry-picks the commit onto `stage` and `main`, pushes each, and returns to
   `develop`. Each branch serves a different system tier, so the change must land
   on all three. If a cherry-pick conflicts, it is aborted and reported — stop
   and surface the conflict.

## 4. End-of-process cleanup

**[ASK]** For each raw drop file processed, ask the user whether to delete it
(it was kept during the run so the process could be re-run). On yes, run
`... cleanup --raw <raw_file>`.

## Notes for maintainers

- The API version lookup uses the **lowercased `sourceTerminology` /
  `targetTerminology` field value** as the `terminology=` query param (e.g.
  `ncit`, `hgnc`) — not a hand-typed code. Among `latest=true` results it prefers
  the entry whose `tags.monthly == "true"`, else the first row.
- The mapset HTML filename comes from the metadata `welcomeText` field, read
  verbatim (it may use `nci` rather than `ncit`).
- Combined commit: when several drops are processed in one run, they share a
  single `Monthly mapping update for <YYYYMM>` commit.
