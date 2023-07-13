#!/bin/bash
TERMINOLOGY="umlssemnet"
TERMINOLOGY_URL="${2:-http://www.nlm.nih.gov/research/umls/${TERMINOLOGY}.owl}"
VERSION="${3:-2023AA}"
dir=$(pwd | perl -pe 's#/cygdrive/c#C:#;')
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
EVS_OPS_HOME=$DIR/../..
WORK_DIRECTORY=$EVS_OPS_HOME/work
INPUT_DIRECTORY=$WORK_DIRECTORY/${TERMINOLOGY}_input
OUTPUT_DIRECTORY=$WORK_DIRECTORY/${TERMINOLOGY}_output
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
setup() {
  python3 -m venv "$VENV_DIRECTORY"
  source "$VENV_BIN_DIRECTORY"/activate
  "$VENV_BIN_DIRECTORY"/pip install poetry
  pushd "$EVS_OPS_HOME" || exit
  "$VENV_BIN_DIRECTORY"/poetry install
  popd "$EVS_OPS_HOME" || exit

  mkdir "$INPUT_DIRECTORY"
  mkdir "$OUTPUT_DIRECTORY"
}
extract_umls_files() {
  echo "extracting UMLS files to $INPUT_DIRECTORY"
  if [ -f "$1" ]; then
    unzip "$1" -d $INPUT_DIRECTORY
  else
    echo "$1 does not exist. Exiting transformation"
    cleanup 1
  fi
}

generate_standard_format_files() {
  echo "generating UMLS Semantic Network standard format files at $OUTPUT_DIRECTORY"
  "$VENV_BIN_DIRECTORY"/poetry run python3 "$EVS_OPS_HOME"/src/terminology_converter/converter/umls_sem_net.py -d "$INPUT_DIRECTORY/SRDEF" -r "$INPUT_DIRECTORY/SRSTRE1" -o "$OUTPUT_DIRECTORY"
}

generate_owl_file() {
  echo "generating UMLS Semantic Network owl file at $OUTPUT_DIRECTORY"
  local terminology_upper=$(echo "$TERMINOLOGY" | tr '[:lower:]' '[:upper:]')
  local versioned_owl_file="$dir/${terminology_upper}_$date.owl"
  "$VENV_BIN_DIRECTORY"/poetry run python3 "$EVS_OPS_HOME"/src/terminology_converter/converter/owl_file_converter.py -u "${TERMINOLOGY_URL}" -v "${VERSION}" -i "${OUTPUT_DIRECTORY}" -o "${OUTPUT_DIRECTORY}" -t "${TERMINOLOGY}"
  mv "$OUTPUT_DIRECTORY/$TERMINOLOGY.owl" "$versioned_owl_file"
  echo "$versioned_owl_file"
}

setup
extract_umls_files "$1"
generate_standard_format_files
versioned_owl_file=$(generate_owl_file)
cleanup
echo "$versioned_owl_file"
