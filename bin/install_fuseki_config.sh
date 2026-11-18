#!/usr/bin/env bash
# Install the packaged Fuseki datasets into the selected Jena version.
set -euo pipefail

DIR=$(cd "$(dirname "$0")" && pwd -P)
SOURCE_DIR=${FUSEKI_CONFIG_SOURCE:-"$DIR/../config/fuseki"}
BASE=${FUSEKI_BASE:-/local/content/fuseki/current/run}
CHECK_ONLY=0

usage() {
  echo "Usage: $0 [--check] [--base FUSEKI_BASE] [--source CONFIG_DIR]" >&2
}

while (($#)); do
  case "$1" in
    --check) CHECK_ONLY=1; shift ;;
    --base|--source)
      (($# >= 2)) || { usage; exit 2; }
      if [[ $1 == --base ]]; then BASE=$2; else SOURCE_DIR=$2; fi
      shift 2 ;;
    *) usage; exit 2 ;;
  esac
done

fail() { echo "Fuseki configuration: $*" >&2; exit 1; }
[[ -d $BASE && -d $BASE/databases ]] || fail "missing run directory or databases: $BASE"
[[ -d $SOURCE_DIR ]] || fail "missing packaged configuration: $SOURCE_DIR"
BASE=$(cd "$BASE" && pwd -P)
SOURCE_DIR=$(cd "$SOURCE_DIR" && pwd -P)
CONFIG_DIR=$BASE/configuration
[[ $CHECK_ONLY == 1 || -d $CONFIG_DIR ]] || mkdir -p "$CONFIG_DIR"
[[ -d $CONFIG_DIR ]] || fail "missing configuration directory: $CONFIG_DIR"

# The repository owns the complete active dataset list. Unknown assemblers must
# be reviewed before Jena can start, since they may re-enable SERVICE.
for path in "$CONFIG_DIR"/*.ttl; do
  [[ -e $path ]] || continue
  case "$(basename "$path")" in
    NCIT2.ttl|CTRP.ttl) ;;
    *) fail "unmanaged active dataset assembler: $path" ;;
  esac
done

for dataset in NCIT2 CTRP; do
  source_file=$SOURCE_DIR/$dataset.ttl
  target_file=$CONFIG_DIR/$dataset.ttl
  [[ -f $source_file ]] || fail "missing packaged $dataset.ttl"
  grep -Eq 'ja:cxtName[[:space:]]+"arq:httpServiceAllowed"[[:space:]]*;[[:space:]]*ja:cxtValue[[:space:]]+false' "$source_file" \
    || fail "packaged $dataset.ttl lacks the dataset SERVICE denial"
  grep -Fq "fuseki:name                   \"$dataset\"" "$source_file" \
    || fail "packaged $dataset.ttl has the wrong dataset name"
  [[ -d $BASE/databases/$dataset ]] || fail "missing $dataset database; refusing to create or move it"
  if [[ $CHECK_ONLY == 1 ]]; then
    [[ -f $target_file ]] && cmp -s "$source_file" "$target_file" \
      || fail "installed $dataset.ttl differs from packaged version"
  elif [[ ! -f $target_file ]] || ! cmp -s "$source_file" "$target_file"; then
    temp_file=$(mktemp "$CONFIG_DIR/.$dataset.ttl.XXXXXX")
    cp "$source_file" "$temp_file"
    chmod 644 "$temp_file"
    mv -f "$temp_file" "$target_file"
  fi
done

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

manifest=$CONFIG_DIR/evsrestapi-operations-fuseki.txt
expected=$(mktemp)
trap 'rm -f "$expected"' EXIT
{
  echo "fuseki_home=$(cd "${FUSEKI_HOME:-"$BASE/.."}" && pwd -P)"
  echo "operations_version=$(sed -n '1s/^VERSION=//p' "$DIR/../Makefile")"
  for dataset in NCIT2 CTRP; do
    echo "$dataset.ttl sha256=$(hash_file "$SOURCE_DIR/$dataset.ttl")"
  done
} > "$expected"

if [[ $CHECK_ONLY == 1 ]]; then
  [[ -f $manifest ]] && cmp -s "$expected" "$manifest" \
    || fail "deployed configuration version record differs from packaged version"
  echo "Fuseki configuration verified: $BASE"
elif [[ ! -f $manifest ]] || ! cmp -s "$expected" "$manifest"; then
  temp_file=$(mktemp "$CONFIG_DIR/.evsrestapi-operations-fuseki.XXXXXX")
  cp "$expected" "$temp_file"
  chmod 644 "$temp_file"
  mv -f "$temp_file" "$manifest"
  echo "Fuseki configuration installed: $BASE"
else
  echo "Fuseki configuration already current: $BASE"
fi
