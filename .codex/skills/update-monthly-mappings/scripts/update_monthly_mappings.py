#!/usr/bin/env python3
"""Deterministic helpers for the "update monthly mappings" skill.

This script performs the programmatic ([AUTO]) parts of the monthly mapping
update for the evsrestapi-operations repo.  The human decision points ([ASK])
are handled by the agent driving the skill, which passes confirmed values in as
flags.  Every subcommand is idempotent-friendly and prints JSON (or a short
summary) so the agent can relay results.

Subcommands:
  preflight   Verify we are on `develop`, up to date, and not behind origin.
  detect      Find fresh raw drop files, match them to mapsets, compute the
              target filenames/versions, and fetch default terminology versions.
  apply       For one confirmed drop: build the new canonical file, delete the
              old one, and update mapsetMetadata.txt + the mapset HTML file.
  commit      Stage the changes (excluding raw drops), commit, and push develop.
  propagate   Cherry-pick a commit onto the other tier branches and push.
  cleanup     Delete a raw drop file (end-of-process cleanup).

Uses only the Python standard library so any agent can run it directly.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.request

API_BASE = "https://api-evsrest.nci.nih.gov/api/v1/metadata/terminologies"

# Branch that the process starts on and commits to first.
PRIMARY_BRANCH = "develop"
# Tier branches the commit is cherry-picked onto (each serves a system tier).
TIER_BRANCHES = ["stage", "main"]

MAPPINGS_DIR = os.path.join("data", "mappings")
METADATA_FILE = os.path.join("config", "metadata", "mapsetMetadata.txt")
METADATA_DIR = os.path.join("config", "metadata")

# Canonical mapping filename, e.g. NCIt_to_HGNC_Mapping_August2026.txt
CANONICAL_RE = re.compile(r"^.+_Mapping_[A-Z][a-z]+\d{4}\.txt$")

# Files in data/mappings that are never raw drops (not scanned as candidates).
SKIP_FILES = {"AGENTS.md", ".DS_Store"}

# Mapsets whose `version` field tracks the monthly version (no local data file)
# and should be synced to match the drops being published this run.
VERSION_SYNC_MAPSETS = ["NCIT_TO_SWISSPROT"]

_MONTH_ABBR = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "sept": "September", "oct": "October",
    "nov": "November", "dec": "December",
}
_FULL_MONTHS = {m.lower(): m for m in set(_MONTH_ABBR.values())}
# Longest names first so "september" matches before "sep".
_MONTH_ALTERNATION = "|".join(
    sorted(set(list(_MONTH_ABBR) + list(_FULL_MONTHS)), key=len, reverse=True)
)
_MONTH_RE = re.compile(r"(" + _MONTH_ALTERNATION + r")[^a-z0-9]*((?:19|20)\d{2})", re.I)


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def run(args, cwd, check=True, capture=True):
    """Run a subprocess, returning its stdout (stripped)."""
    res = subprocess.run(
        args, cwd=cwd, check=check,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        text=True,
    )
    return (res.stdout or "").strip(), res.returncode


def repo_root(start):
    out, _ = run(["git", "rev-parse", "--show-toplevel"], cwd=start)
    return out


def read_metadata_rows(root):
    """Return (path, lines, rows) where rows maps name -> list-of-fields.

    Only rows with both a sourceTerminology and targetTerminology (i.e. local
    data-file mapsets) are returned.
    """
    path = os.path.join(root, METADATA_FILE)
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    rows = {}
    for line in lines:
        if not line or line.startswith("#"):
            continue
        fields = line.split(",")
        if len(fields) < 9:
            continue
        name, src_term, tgt_term = fields[0], fields[5], fields[7]
        if src_term and tgt_term:
            rows[name] = fields
    return path, lines, rows


def parse_month_year(basename):
    """Extract ('August', '2026', 'August2026') from a raw drop filename."""
    m = _MONTH_RE.search(basename.lower())
    if not m:
        return None
    token, year = m.group(1).lower(), m.group(2)
    month = _FULL_MONTHS.get(token) or _MONTH_ABBR.get(token)
    if not month:
        return None
    return month, year, month + year


def match_mapset(basename, rows):
    """Match a raw drop filename to a mapset by source+target terminology tokens."""
    norm = re.sub(r"[^a-z0-9]", "", basename.lower())
    hits = []
    for name, fields in rows.items():
        src, tgt = fields[5].lower(), fields[7].lower()
        if src in norm and tgt in norm:
            hits.append((name, fields))
    # Prefer the most specific match (longest combined token length).
    hits.sort(key=lambda nf: len(nf[1][5]) + len(nf[1][7]), reverse=True)
    return hits[0] if hits else None


def api_default_version(term_code):
    """Fetch the default version for a terminology, preferring the monthly tag."""
    url = f"{API_BASE}?latest=true&terminology={term_code.lower()}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
    except Exception as exc:  # network/JSON errors -> caller must ask the user
        return None, f"lookup failed: {exc}"
    if not isinstance(data, list) or not data:
        return None, "no entries returned"
    monthly = [d for d in data
               if str(d.get("tags", {}).get("monthly", "")).lower() == "true"]
    chosen = (monthly[0] if monthly else data[0])
    return chosen.get("version"), None


def commit_month(today=None):
    """YYYYMM for the commit message.

    Current month, unless we are in the first couple of days of a new month, in
    which case the month that just ended is used.
    """
    today = today or datetime.date.today()
    if today.day <= 2:
        prev_last = today.replace(day=1) - datetime.timedelta(days=1)
        return prev_last.strftime("%Y%m")
    return today.strftime("%Y%m")


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def cmd_preflight(root, _args):
    run(["git", "fetch", "origin", "--quiet"], cwd=root, check=False)
    branch, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    counts, rc = run(
        ["git", "rev-list", "--left-right", "--count",
         f"HEAD...origin/{PRIMARY_BRANCH}"], cwd=root, check=False)
    ahead = behind = None
    if rc == 0 and counts:
        parts = counts.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])
    ok = branch == PRIMARY_BRANCH and behind == 0
    if branch != PRIMARY_BRANCH:
        msg = f"HALT: on '{branch}', not '{PRIMARY_BRANCH}'."
    elif behind:
        msg = f"HALT: behind origin/{PRIMARY_BRANCH} by {behind} commit(s); pull/rebase first."
    elif ahead:
        msg = f"OK (warn): on {PRIMARY_BRANCH}, up to date, but {ahead} unpushed local commit(s)."
    else:
        msg = f"OK: on {PRIMARY_BRANCH}, at HEAD, up to date."
    print(json.dumps({"ok": ok, "branch": branch, "ahead": ahead,
                      "behind": behind, "message": msg}, indent=2))
    return 0 if ok else 1


def cmd_detect(root, args):
    _, lines, rows = read_metadata_rows(root)
    mdir = os.path.join(root, MAPPINGS_DIR)
    drops, ignored = [], []
    for fname in sorted(os.listdir(mdir)):
        if fname in SKIP_FILES or fname.startswith("."):
            continue
        if CANONICAL_RE.match(fname):
            continue  # already-canonical current file
        match = match_mapset(fname, rows)
        my = parse_month_year(fname)
        if not match or not my:
            ignored.append({"file": fname,
                            "reason": "no mapset match" if not match else "no month/year in name"})
            continue
        name, fields = match
        month, year, version = my
        new_file = f"{name}_{version}.txt"
        prev_file = f"{name}_{fields[2]}.txt"
        already_done = os.path.exists(os.path.join(mdir, new_file))
        src_term, tgt_term = fields[5], fields[7]
        src_default, src_err = api_default_version(src_term)
        tgt_default, tgt_err = api_default_version(tgt_term)
        drops.append({
            "raw_file": fname,
            "mapset": name,
            "html_file": fields[3],
            "source_terminology": src_term,
            "target_terminology": tgt_term,
            "current_version": fields[2],
            "current_source_version": fields[6],
            "current_target_version": fields[8],
            "new_version": version,
            "previous_file": prev_file,
            "new_file": new_file,
            "already_done": already_done,
            "source_default_version": src_default,
            "source_default_error": src_err,
            "target_default_version": tgt_default,
            "target_default_error": tgt_err,
        })
    # Report version-sync mapsets (e.g. SWISSPROT) so the agent can offer to
    # bump their version field to match the drops being published this run.
    version_sync = []
    for line in lines:
        fields = line.split(",")
        if fields and fields[0] in VERSION_SYNC_MAPSETS and len(fields) >= 3:
            version_sync.append({"mapset": fields[0], "current_version": fields[2]})

    print(json.dumps({"drops": drops, "ignored": ignored,
                      "version_sync": version_sync}, indent=2))
    return 0


def cmd_sync_version(root, args):
    """Update only the `version` field of a named mapset row (e.g. SWISSPROT)."""
    path = os.path.join(root, METADATA_FILE)
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    updated = False
    old_version = None
    out = []
    for line in lines:
        fields = line.split(",")
        if fields and fields[0] == args.mapset and len(fields) >= 3:
            old_version = fields[2]
            fields[2] = args.new_version
            line = ",".join(fields)
            updated = True
        out.append(line)
    if updated:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
    print(json.dumps({"updated": updated, "mapset": args.mapset,
                      "old_version": old_version, "new_version": args.new_version}))
    return 0 if updated else 1


def cmd_apply(root, args):
    path, lines, rows = read_metadata_rows(root)
    if args.mapset not in rows:
        print(f"ERROR: mapset '{args.mapset}' not found in metadata", file=sys.stderr)
        return 1
    fields = rows[args.mapset]
    old_version = fields[2]
    old_src_ver, old_tgt_ver = fields[6], fields[8]
    html_name = fields[3]

    mdir = os.path.join(root, MAPPINGS_DIR)
    raw_path = args.raw if os.path.isabs(args.raw) else os.path.join(mdir, args.raw)
    prev_path = os.path.join(mdir, f"{args.mapset}_{old_version}.txt")
    new_path = os.path.join(mdir, f"{args.mapset}_{args.new_version}.txt")

    # 1. Build the new canonical file: previous header + raw rows, CRs stripped.
    if not os.path.exists(prev_path):
        print(f"ERROR: previous file missing: {prev_path}", file=sys.stderr)
        return 1
    with open(prev_path, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\r\n") + "\n"
    with open(raw_path, "rb") as fh:
        raw_text = fh.read().decode("utf-8", "replace").replace("\r", "")
    with open(new_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(header + raw_text)

    # 2. Delete the old canonical version (once the new one exists).
    if os.path.abspath(prev_path) != os.path.abspath(new_path) and os.path.exists(prev_path):
        os.remove(prev_path)

    # 3. Update the metadata row (version, source version, target version).
    new_fields = list(fields)
    new_fields[2] = args.new_version
    new_fields[6] = args.source_version
    new_fields[8] = args.target_version
    old_line, new_line = ",".join(fields), ",".join(new_fields)
    new_lines = [new_line if ln == old_line else ln for ln in lines]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(new_lines) + "\n")

    # 4. Update the mapset HTML: version token on the Source/Target lines.
    html_changes = []
    if html_name:
        html_path = os.path.join(root, METADATA_DIR, html_name)
        if os.path.exists(html_path):
            with open(html_path, encoding="utf-8") as fh:
                html_lines = fh.read().splitlines()
            out = []
            for ln in html_lines:
                if "Source:" in ln and old_src_ver:
                    ln = ln.replace(old_src_ver, args.source_version)
                if "Target:" in ln and old_tgt_ver:
                    ln = ln.replace(old_tgt_ver, args.target_version)
                out.append(ln)
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(out) + "\n")
            html_changes = [html_name]

    print(json.dumps({
        "mapset": args.mapset,
        "new_file": os.path.relpath(new_path, root),
        "deleted_file": os.path.relpath(prev_path, root),
        "metadata_updated": True,
        "html_updated": html_changes,
        "source_version": args.source_version,
        "target_version": args.target_version,
    }, indent=2))
    return 0


def cmd_commit(root, args):
    run(["git", "add", "-A", "--", METADATA_DIR, MAPPINGS_DIR], cwd=root)
    # Unstage any raw drops (non-canonical files under data/mappings).
    staged, _ = run(["git", "diff", "--cached", "--name-only"], cwd=root)
    for rel in staged.splitlines():
        if rel.startswith(MAPPINGS_DIR + os.sep) or rel.startswith(MAPPINGS_DIR + "/"):
            base = os.path.basename(rel)
            if not CANONICAL_RE.match(base):
                run(["git", "restore", "--staged", "--", rel], cwd=root, check=False)
    month = args.month or commit_month()
    message = args.message or f"Monthly mapping update for {month}"
    staged, _ = run(["git", "diff", "--cached", "--name-only"], cwd=root)
    if not staged:
        print(json.dumps({"committed": False, "reason": "nothing staged"}))
        return 1
    run(["git", "commit", "-m", message], cwd=root)
    sha, _ = run(["git", "rev-parse", "HEAD"], cwd=root)
    if not args.no_push:
        run(["git", "push", "origin", PRIMARY_BRANCH], cwd=root, check=False)
    print(json.dumps({"committed": True, "sha": sha, "message": message,
                      "pushed": not args.no_push, "files": staged.splitlines()}, indent=2))
    return 0


def cmd_propagate(root, args):
    branches = args.branches or TIER_BRANCHES
    results = []
    for b in branches:
        run(["git", "checkout", b], cwd=root)
        out, rc = run(["git", "cherry-pick", args.sha], cwd=root, check=False)
        if rc != 0:
            run(["git", "cherry-pick", "--abort"], cwd=root, check=False)
            results.append({"branch": b, "ok": False, "error": out})
            continue
        if not args.no_push:
            run(["git", "push", "origin", b], cwd=root, check=False)
        newsha, _ = run(["git", "rev-parse", "HEAD"], cwd=root)
        results.append({"branch": b, "ok": True, "sha": newsha, "pushed": not args.no_push})
    run(["git", "checkout", PRIMARY_BRANCH], cwd=root)
    print(json.dumps({"results": results, "returned_to": PRIMARY_BRANCH}, indent=2))
    return 0 if all(r["ok"] for r in results) else 1


def cmd_cleanup(root, args):
    mdir = os.path.join(root, MAPPINGS_DIR)
    target = args.raw if os.path.isabs(args.raw) else os.path.join(mdir, args.raw)
    existed = os.path.exists(target)
    if existed:
        os.remove(target)
    print(json.dumps({"deleted": existed, "file": os.path.relpath(target, root)}))
    return 0


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=None, help="repo root (default: git toplevel of cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("preflight")
    sub.add_parser("detect")

    a = sub.add_parser("apply")
    a.add_argument("--mapset", required=True)
    a.add_argument("--raw", required=True, help="raw drop filename or path")
    a.add_argument("--new-version", required=True, help="e.g. August2026")
    a.add_argument("--source-version", required=True)
    a.add_argument("--target-version", required=True)

    c = sub.add_parser("commit")
    c.add_argument("--month", help="YYYYMM override")
    c.add_argument("--message", help="commit message override")
    c.add_argument("--no-push", action="store_true")

    pr = sub.add_parser("propagate")
    pr.add_argument("--sha", required=True)
    pr.add_argument("--branches", nargs="*", help="default: stage main")
    pr.add_argument("--no-push", action="store_true")

    cl = sub.add_parser("cleanup")
    cl.add_argument("--raw", required=True)

    sv = sub.add_parser("sync-version")
    sv.add_argument("--mapset", required=True)
    sv.add_argument("--new-version", required=True)

    args = p.parse_args()
    root = args.repo or repo_root(os.getcwd())
    handler = {
        "preflight": cmd_preflight, "detect": cmd_detect, "apply": cmd_apply,
        "commit": cmd_commit, "propagate": cmd_propagate, "cleanup": cmd_cleanup,
        "sync-version": cmd_sync_version,
    }[args.cmd]
    sys.exit(handler(root, args))


if __name__ == "__main__":
    main()
