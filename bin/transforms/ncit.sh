#!/bin/bash
set -e

# This is the inference stage migrated from legacy/MasterCTRP.sh. Publication
# and host-specific post-processing are intentionally left to later workflows.
TERMINOLOGY="ncit"
PID=$2
INPUT_FILE=$1
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
EVS_OPS_HOME=$DIR/../..
WORK_DIRECTORY=$EVS_OPS_HOME/bin/work_$PID
INPUT_DIRECTORY=$WORK_DIRECTORY/input
OUTPUT_DIRECTORY=$WORK_DIRECTORY/output
INFERENCE_JAR=$EVS_OPS_HOME/legacy/GenerateOWLAPIInferred/GenerateOWLAPIInferred-2.0-jar-with-dependencies.jar
JAVA_COMMAND=${JAVA_COMMAND:-java}

pre_condition_check() {
  if [[ ! -s $INPUT_FILE ]]; then
    echo "No NCIt input file ($INPUT_FILE) found or file is empty. Exiting"
    exit 1
  fi
  if [[ ! -d $INPUT_DIRECTORY ]]; then
    echo "No input directory ($INPUT_DIRECTORY) found. Exiting"
    exit 1
  fi
  if [[ ! -d $OUTPUT_DIRECTORY ]]; then
    echo "No output directory ($OUTPUT_DIRECTORY) found. Exiting"
    exit 1
  fi
  if [[ ! -f $INFERENCE_JAR ]]; then
    echo "NCIt inference JAR ($INFERENCE_JAR) not found. Exiting"
    exit 1
  fi
  if [[ $(basename "$INPUT_FILE") != *"Thesaurus"* ]]; then
    echo "NCIt asserted input filename must contain Thesaurus: $INPUT_FILE"
    exit 1
  fi
  if ! command -v "$JAVA_COMMAND" >/dev/null 2>&1; then
    echo "Java command ($JAVA_COMMAND) not found. Exiting"
    exit 1
  fi
}

generate_inferred_owl() {
  local input_uri="file://$INPUT_FILE"
  local generated_file=${INPUT_FILE/Thesaurus/ThesaurusInf}
  local asserted_basename
  local output_basename
  local inferred_file
  local java_options

  asserted_basename=$(basename "$INPUT_FILE")
  asserted_basename=${asserted_basename#f$PID.}
  output_basename=${asserted_basename/Thesaurus/ThesaurusInf}
  inferred_file=$OUTPUT_DIRECTORY/$output_basename
  read -r -a java_options <<<"${NCIT_INFERENCE_JAVA_OPTS:--Xmx20000m}"

  echo "Generating inferred NCIt OWL from $INPUT_FILE"
  "$JAVA_COMMAND" "${java_options[@]}" -jar "$INFERENCE_JAR" "$input_uri" 2>&1
  if [[ ! -s $generated_file ]]; then
    echo "NCIt inference did not create the expected file: $generated_file"
    return 1
  fi
  mv "$generated_file" "$inferred_file"
  echo "$inferred_file"
}

pre_condition_check
INPUT_FILE="$(cd "$(dirname "$INPUT_FILE")" >/dev/null 2>&1 && pwd)/$(basename "$INPUT_FILE")"
generate_inferred_owl
