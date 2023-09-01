#!/bin/bash
TERMINOLOGY="medrt"
TERMINOLOGY_URL="${3:-http://ncicb.nci.nih.gov/MEDRT.owl}"
dir=$(pwd | perl -pe 's#/cygdrive/c#C:#;')
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
EVS_OPS_HOME=$DIR/../..
WORK_DIRECTORY=$EVS_OPS_HOME/bin/work
INPUT_DIRECTORY=$WORK_DIRECTORY/input
OUTPUT_DIRECTORY=$WORK_DIRECTORY/output
VENV_DIRECTORY=$WORK_DIRECTORY/venv
VENV_BIN_DIRECTORY=$VENV_DIRECTORY/bin
# We sort on version to determine "latest" programmatically in a consistent way
date=$(/bin/date +%Y%m)

cleanup() {
  echo "${TERMINOLOGY}.sh:Cleaning up. code:$1"
  local code=$1
  /bin/rm -rf "$WORK_DIRECTORY"
  if [ "$code" != "" ]; then
    exit $code
  fi
}
pre_condition_check(){
if [ ! -d $INPUT_DIRECTORY ]; then
  echo "No input directory ($INPUT_DIRECTORY) found. Exiting"
  cleanup 1
fi

if [ ! -d $OUTPUT_DIRECTORY ]; then
  echo "No output directory ($OUTPUT_DIRECTORY) found. Exiting"
  cleanup 1
fi
}
setup() {
  python3 -m venv "$VENV_DIRECTORY"
  source "$VENV_BIN_DIRECTORY"/activate
  "$VENV_BIN_DIRECTORY"/pip install poetry
  # Setting the URL lib to a specific version to avoid upgrading OpenSSL version
  "$VENV_BIN_DIRECTORY"/pip install "urllib3 <=1.26.15"
  pushd "$EVS_OPS_HOME" || exit
  "$VENV_BIN_DIRECTORY"/poetry install
  popd "$EVS_OPS_HOME" || exit
}

generate_standard_format_files() {
  echo "generating MED-RT standard format files at $OUTPUT_DIRECTORY"
  "$VENV_BIN_DIRECTORY"/poetry run python3 "$EVS_OPS_HOME"/src/terminology_converter/converter/med_rt.py -d "$1" -o "$OUTPUT_DIRECTORY"
}

generate_owl_file() {
  echo "generating MED-RT owl file at $OUTPUT_DIRECTORY"
  local terminology_upper=$(echo "$TERMINOLOGY" | tr '[:lower:]' '[:upper:]')
  local version=$(grep '<version>' "$1" | perl -pe 's/.*<version>//; s/<\/version>//; s/^\s+|\s+$//g;')
  local versioned_owl_file="$dir/${terminology_upper}_$version.owl"
  "$VENV_BIN_DIRECTORY"/poetry run python3 "$EVS_OPS_HOME"/src/terminology_converter/converter/owl_file_converter.py -u "${TERMINOLOGY_URL}" -v "${version}" -i "${OUTPUT_DIRECTORY}" -o "${OUTPUT_DIRECTORY}" -t "${TERMINOLOGY}"
  mv "$OUTPUT_DIRECTORY/$TERMINOLOGY.owl" "$versioned_owl_file"
  echo "$versioned_owl_file"
}

pre_condition_check
setup
generate_standard_format_files "$@"
versioned_owl_file=$(generate_owl_file "$@")
echo "$versioned_owl_file"
