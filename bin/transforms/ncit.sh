#!/bin/bash
set -e

# Keep the known Java 17 locations available for local and server runs. An
# installation can select another executable explicitly with JAVA_COMMAND.
export PATH="/opt/homebrew/opt/openjdk@17/bin:/usr/local/corretto-jdk17/bin:$PATH"

TERMINOLOGY="ncit"
INPUT_FILE=$1
PID=$2
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
EVS_OPS_HOME=$DIR/../..
WORK_DIRECTORY=${NCIT_WORK_DIRECTORY:-$EVS_OPS_HOME/bin/work_$PID}
INPUT_DIRECTORY=$WORK_DIRECTORY/input
OUTPUT_DIRECTORY=$WORK_DIRECTORY/output

# MasterCTRP.sh expected these tools under this installation. Each location is
# configurable so the transform can also be exercised outside that server.
PROCESSING_HOME=${NCIT_PROCESSING_HOME:-/local/content/vocab_processing_OWL2}
INFERENCE_JAR=${NCIT_INFERENCE_JAR:-$EVS_OPS_HOME/legacy/GenerateOWLAPIInferred/GenerateOWLAPIInferred-2.0-jar-with-dependencies.jar}
LVG_DIRECTORY=${NCIT_LVG_DIRECTORY:-$PROCESSING_HOME/lvg2015}
LVG_COMMAND=${NCIT_LVG_COMMAND:-$LVG_DIRECTORY/bin/lvg}
SCRUBBER_DIRECTORY=${NCIT_SCRUBBER_DIRECTORY:-$PROCESSING_HOME/OWLScrubber}
SCRUBBER_JAR=${NCIT_SCRUBBER_JAR:-$SCRUBBER_DIRECTORY/owlscrubber-2.1.0-jar-with-dependencies.jar}
SCRUBBER_PROPERTIES=${NCIT_SCRUBBER_PROPERTIES:-$SCRUBBER_DIRECTORY/owlscrubber.properties}
DISJOINT_DIRECTORY=${NCIT_DISJOINT_DIRECTORY:-$PROCESSING_HOME/disjoint}
DISJOINT_CLASSPATH=${NCIT_DISJOINT_CLASSPATH:-.}
DISJOINT_CLASS=${NCIT_DISJOINT_CLASS:-OWLDisjointWithProcessor}
JAVA_COMMAND=${JAVA_COMMAND:-java}

FINAL_OWL=$OUTPUT_DIRECTORY/ThesaurusInferred_forTS.owl
CREATE_ARCHIVES=${NCIT_CREATE_ARCHIVES:-true}
PUBLISH_FTP=${NCIT_PUBLISH_FTP:-false}
FTP_HOST=${NCIT_FTP_HOST:-ncicbftp2.nci.nih.gov}
FTP_DIRECTORY=${NCIT_FTP_DIRECTORY:-cacore/EVS/upload}

log() {
  echo "$TERMINOLOGY.sh: $*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

require_file() {
  [[ -f $1 ]] || fail "$2 ($1) not found"
}

require_executable() {
  [[ -x $1 ]] || fail "$2 ($1) not found or not executable"
}

pre_condition_check() {
  [[ $# -eq 2 ]] || fail "Usage: $0 <asserted-owl-file> <stardog-load-pid>"
  [[ -s $INPUT_FILE ]] || fail "NCIt input file ($INPUT_FILE) not found or empty"
  [[ -d $INPUT_DIRECTORY ]] || fail "Input directory ($INPUT_DIRECTORY) not found"
  [[ -d $OUTPUT_DIRECTORY ]] || fail "Output directory ($OUTPUT_DIRECTORY) not found"
  [[ $(basename "$INPUT_FILE") == *"Thesaurus"* ]] ||
    fail "NCIt asserted input filename must contain Thesaurus: $INPUT_FILE"

  command -v "$JAVA_COMMAND" >/dev/null 2>&1 || fail "Java command ($JAVA_COMMAND) not found"
  require_file "$INFERENCE_JAR" "NCIt inference JAR"
  require_file "$SCRUBBER_JAR" "OWL scrubber JAR"
  require_file "$SCRUBBER_PROPERTIES" "OWL scrubber properties"
  command -v perl >/dev/null 2>&1 || fail "perl command not found"
  [[ -d $DISJOINT_DIRECTORY ]] || fail "Disjoint processor directory ($DISJOINT_DIRECTORY) not found"

  if [[ $CREATE_ARCHIVES == true ]]; then
    command -v zip >/dev/null 2>&1 || fail "zip command not found"
  fi
  if [[ $PUBLISH_FTP == true ]]; then
    [[ $CREATE_ARCHIVES == true ]] ||
      fail "NCIT_CREATE_ARCHIVES must be true when NCIT_PUBLISH_FTP=true"
    command -v ftp >/dev/null 2>&1 || fail "ftp command not found"
    [[ -n $NCIT_FTP_USER && -n $NCIT_FTP_PASSWORD ]] ||
      fail "NCIT_FTP_USER and NCIT_FTP_PASSWORD are required when NCIT_PUBLISH_FTP=true"
  fi
}

generate_inferred_owl() {
  local generated_file=${INPUT_FILE/Thesaurus/ThesaurusInf}
  local java_options
  read -r -a java_options <<<"${NCIT_INFERENCE_JAVA_OPTS:--Xmx20000m}"

  log "Generating inferred OWL from $INPUT_FILE"
  "$JAVA_COMMAND" "${java_options[@]}" -jar "$INFERENCE_JAR" "file://$INPUT_FILE" 2>&1
  [[ -s $generated_file ]] || fail "Inference did not create the expected file: $generated_file"
  INFERRED_OWL=$generated_file
}

run_lvg() {
  # LVG's command parser treats hyphens in -i/-o path values as new options.
  # Preserve MasterCTRP's runLVG.sh behavior by using fixed, hyphen-free names.
  local lvg_input=$OUTPUT_DIRECTORY/lvg_input.owl
  LVG_OWL=$OUTPUT_DIRECTORY/lvg_output.owl
  log "Running LVG"
  cp "$INFERRED_OWL" "$lvg_input"
  (
    cd "$LVG_DIRECTORY"
    "$LVG_COMMAND" -f:q0 '-s:\t' -F:2 -i:"$lvg_input" -o:"$LVG_OWL"
  ) 2>&1
  [[ -s $LVG_OWL ]] || fail "LVG did not create the expected file: $LVG_OWL"

  # LVG transliterates the Unicode less-than-or-equal sign to a raw "<=",
  # which is not legal XML character data. Keep the transliteration XML-safe.
  perl -pi -e 's/ <= / \&lt;= /g' "$LVG_OWL"
}

scrub_inferred_owl() {
  local java_options
  SCRUBBED_OWL=$OUTPUT_DIRECTORY/$(basename "$INFERRED_OWL")-forProduction.owl
  read -r -a java_options <<<"${NCIT_SCRUBBER_JAVA_OPTS:---add-opens=java.base/java.lang=ALL-UNNAMED -Xmx15000M}"

  log "Scrubbing inferred OWL for production"
  (
    cd "$SCRUBBER_DIRECTORY"
    "$JAVA_COMMAND" "${java_options[@]}" -jar "$SCRUBBER_JAR" \
      -C "$SCRUBBER_PROPERTIES" -E -N "file://$INFERRED_OWL" -O "file://$SCRUBBED_OWL"
  ) 2>&1
  [[ -s $SCRUBBED_OWL ]] || fail "OWL scrubber did not create the expected file: $SCRUBBED_OWL"
}

make_by_code_owl() {
  log "Converting production OWL to by-code form"
  perl -pi -e '
    s#<P386 rdf:datatype="http://www.w3.org/2001/XMLSchema\#string"></P386>##g;
    s#<P385 rdf:datatype="http://www.w3.org/2001/XMLSchema\#string"></P385>##g;
    s#<P378 rdf:datatype="http://www.w3.org/2001/XMLSchema\#string"></P378>##g;
    s#<P378 rdf:datatype="http://www.w3.org/2001/XMLSchema\#string">NCI</P378>#<P378>NCI</P378>#g;
    s#<term-group#<P383#g;
    s#</term-group#</P383#g;
    s#<term-source#<P384#g;
    s#</term-source#</P384#g;
  ' "$SCRUBBED_OWL"
  [[ -s $SCRUBBED_OWL ]] || fail "By-code conversion left an empty OWL file: $SCRUBBED_OWL"
  cp "$SCRUBBED_OWL" "$FINAL_OWL"
}

apply_disjoint_axioms() {
  local legacy_disjoint_owl=${FINAL_OWL%.owl}_disjoint.owl
  local current_disjoint_owl=$FINAL_OWL-disjoint.owl
  local disjoint_owl
  local java_options
  read -r -a java_options <<<"${NCIT_DISJOINT_JAVA_OPTS:--Xms512m -Xmx8g}"

  log "Applying disjoint axioms"
  (
    cd "$DISJOINT_DIRECTORY"
    "$JAVA_COMMAND" "${java_options[@]}" -cp "$DISJOINT_CLASSPATH" "$DISJOINT_CLASS" "$FINAL_OWL"
  ) 2>&1
  if [[ -s $legacy_disjoint_owl ]]; then
    disjoint_owl=$legacy_disjoint_owl
  elif [[ -s $current_disjoint_owl ]]; then
    disjoint_owl=$current_disjoint_owl
  else
    fail "Disjoint processing did not create $legacy_disjoint_owl or $current_disjoint_owl"
  fi
  mv "$disjoint_owl" "$FINAL_OWL"
}

create_publication_artifacts() {
  local ftp_zip=$OUTPUT_DIRECTORY/ThesaurusInferred_forTS.zip

  [[ $CREATE_ARCHIVES == true ]] || return 0

  log "Creating FTP publication archive"
  (
    cd "$OUTPUT_DIRECTORY"
    zip "$(basename "$ftp_zip")" "$(basename "$FINAL_OWL")"
  )
}

publish_ftp_artifacts() {
  [[ $PUBLISH_FTP == true ]] || return 0

  log "Publishing NCIt archive to $FTP_HOST/$FTP_DIRECTORY"
  (
    cd "$OUTPUT_DIRECTORY"
    ftp -n "$FTP_HOST" <<EOF
quote USER $NCIT_FTP_USER
quote PASS $NCIT_FTP_PASSWORD
cd $FTP_DIRECTORY
binary
put ThesaurusInferred_forTS.zip
quit
EOF
  )
}

pre_condition_check "$@"
INPUT_FILE="$(cd "$(dirname "$INPUT_FILE")" >/dev/null 2>&1 && pwd)/$(basename "$INPUT_FILE")"
log "Processing asserted OWL: $INPUT_FILE"
generate_inferred_owl
# run_lvg
scrub_inferred_owl
make_by_code_owl
apply_disjoint_axioms
create_publication_artifacts
#publish_ftp_artifacts

# stardog_load.sh consumes the last output line as the transformed OWL path.
echo "$FINAL_OWL"
