# This script will take the file with the new codes in a .txt file as input
set -e -o pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/ops-common.sh"
ops_lock "$@"

[[ "$#" -eq 1 && -r "$1" ]] || { echo "Usage: $0 <codes-file>" >&2; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq is required" >&2; exit 1; }
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FILE="$1"
CONFIG_FILE="$EVS_OPS_HOME/config/metadata/cdisc-form.json"
mkdir -p "$DIR/temp"
WORK_DIRECTORY="$(mktemp -d "$DIR/temp/cdisc.XXXXXX")"
trap 'rm -rf -- "$WORK_DIRECTORY"' EXIT
CODELISTS="$WORK_DIRECTORY/codelists"
SUBSETS="$WORK_DIRECTORY/subsets"
CDISC_FORM_COPY="$WORK_DIRECTORY/cdisc-form.json"

# Reformat the new codes such that all semi-colons are replaced with /n; remove whitespace around hyphens
sed "s/; /\n/g;s/&/&/;s/\s*-\s*/-/g" "$FILE" > "$CODELISTS.txt"

# Get just unique values (Should be just the subsets)
cut -d- -f 1 "$CODELISTS.txt" | uniq > "$SUBSETS.txt"

# Set the codelist and subset txts to be JSON format
jq --raw-input . "$CODELISTS.txt" | jq --slurp . > "$CODELISTS.json"
jq --raw-input . "$SUBSETS.txt" | jq --slurp . > "$SUBSETS.json"

# Remove text files
rm "$CODELISTS.txt" "$SUBSETS.txt"

# Copy over current cdisc-form.json from ./../config/metadata; have a copy with the current PID
cp "$CONFIG_FILE" "$CDISC_FORM_COPY"
cp "$CONFIG_FILE" "$DIR/temp/original-cdisc-form-$$.json"

# Replace subset and codelist section in the copy
jq '(.sections[].fields[] | select(.name == "subset")).options = input | (.sections[].fields[] | select(.name == "codelist")).options = input' "$CDISC_FORM_COPY" "$SUBSETS.json" "$CODELISTS.json" > "$WORK_DIRECTORY/updated.json"

# Copy new form into original file
cp "$WORK_DIRECTORY/updated.json" "$CONFIG_FILE"

echo "Completed reformatting of codelist and subsets based on $FILE."
