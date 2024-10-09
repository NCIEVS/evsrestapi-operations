#!/bin/bash -f
#
# This script takes a parameter locating a data file.
# If the data file is a remote file, it downloads that file
# to a local file.  The data is then loaded into graph DB
# and this script takes responsibility for determining the
# "graph" and "version" needed for performing that load.
#
force=0
config=1
help=0
weekly=0

while [[ "$#" -gt 0 ]]; do
  case $1 in
  --help) help=1 ;;
  # use environment variable config (dev env)
  --noconfig)
    config=0
    ncflag="--noconfig"
    ;;
  # ignore errors AND replace the specified terminology/verison/graph
  --force) force=1 ;;
  # weekly not monthly
  --weekly) weekly=1 ;;
  *) arr=("${arr[@]}" "$1") ;;
  esac
  shift
done

if [ ${#arr[@]} -ne 1 ] || [ $help -eq 1 ]; then
  echo "Usage: $0 [--noconfig] [--force] [--weekly] [--help] <data>"
  echo "  e.g. $0 /local/content/downloads/Thesaurus.owl --weekly --force"
  echo "  e.g. $0 ../../data/ncit_22.07c/ThesaurusInferred_forTS.owl"
  echo "  e.g. $0 https://evs.nci.nih.gov/ftp1/upload/ThesaurusInferred_forTS.zip"
  echo "  e.g. $0 http://current.geneontology.org/ontology/go.owl"
  echo "  e.g. $0 /local/content/downloads/HGNC_202209.owl"
  echo "  e.g. $0 /local/content/downloads/chebi_213.owl"
  exit 1
fi

data=${arr[0]}

optimize_stardog_dbs() {
  optimize_stardog_db "NCIT2"
  optimize_stardog_db "CTRP"
}

optimize_stardog_db() {
  optimize_db=$1
  if [[ $l_graph_db_type == "stardog" ]]; then
    echo "  optimize_stardog_db ($optimize_db) ...$(/bin/date)"
    $l_graph_db_home/bin/stardog-admin db optimize -n $optimize_db -u $l_graph_db_username -p $l_graph_db_password | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
      echo "    ERROR: Problem optimizing stardog ($optimize_db)"
      cleanup 1
    fi
  elif [[ $l_graph_db_type == "jena" ]]; then
    echo "    no optimize for jena"
  fi
}

setup_configuration() {
  if [[ $config -eq 1 ]]; then
    APP_HOME="${APP_HOME:-/local/content/evsrestapi}"
    CONFIG_DIR=${APP_HOME}/config
    CONFIG_ENV_FILE=${CONFIG_DIR}/setenv.sh
    if [[ -e $CONFIG_ENV_FILE ]]; then
      echo "    config = $CONFIG_ENV_FILE"
      . $CONFIG_ENV_FILE
    else
      echo "    ERROR: $CONFIG_ENV_FILE does not exist, consider using --noconfig"
      exit 1
    fi
  fi
}

setup() {
  mkdir -p "$INPUT_DIRECTORY"
  mkdir -p "$OUTPUT_DIRECTORY"
}

validate_setup() {
  if [[ $l_graph_db_type == "stardog" ]]; then
    if [[ -n "$GRAPH_DB_HOME" ]]; then
      l_graph_db_home="$GRAPH_DB_HOME"
    elif [[ -n "$STARDOG_HOME" ]]; then
      l_graph_db_home="$STARDOG_HOME"
    else
      echo "Error: Both GRAPH_DB_HOME and STARDOG_HOME are not set."
      exit 1
    fi
    if [[ -n "$GRAPH_DB_USERNAME" ]]; then
      l_graph_db_username="$GRAPH_DB_USERNAME"
    elif [[ -n "$STARDOG_USERNAME" ]]; then
      l_graph_db_username="$STARDOG_USERNAME"
    else
      echo "Error: Both GRAPH_DB_USERNAME and STARDOG_USERNAME are not set."
      exit 1
    fi
        if [[ -n "$GRAPH_DB_PASSWORD" ]]; then
      l_graph_db_password="$GRAPH_DB_PASSWORD"
    elif [[ -n "$STARDOG_PASSWORD" ]]; then
      l_graph_db_password="$STARDOG_PASSWORD"
    else
      echo "Error: Both GRAPH_DB_PASSWORD and STARDOG_PASSWORD are not set."
      exit 1
    fi
  elif [[ $l_graph_db_type == "jena" ]]; then
    if [[ -z $GRAPH_DB_HOME ]]; then
      echo "    ERROR: GRAPH_DB_HOME is not set"
      exit 1
    else
      l_graph_db_home="$GRAPH_DB_HOME"
    fi
  fi
}

get_file_extension() {
  local extension=$(echo $1 | perl -pe 's/.*\.//;')
  if [[ "x$extension" == "" ]]; then
    echo "    ERROR: unable to find file extension = $1"
    exit 1
  fi
  echo "$extension"
}

get_file_name() {
  echo $1 | perl -pe 's/^.*\///; s/([^\.]+)\..{2,5}$/$1/;'
}

get_owl_files() {
  extension=$(get_file_extension "$1")
  if [[ $extension == "owl" ]]; then
    filenames=("$1")
  else
    filenames=()
  fi
  # Loop through all the owl files in $INPUT_DIRECTORY. Ignore the OWL specified as the first
  while IFS= read -r filename; do
    # Add filename to the array
    filenames+=("$filename")
  done <<<"$(find "$INPUT_DIRECTORY" -maxdepth 1 -type f -name "*.owl" ! -name "*$2*" -print | sort)"
  echo "${filenames[*]}"
}

set_transformed_owl() {
  if [[ $? -ne 0 ]]; then
    echo "ERROR: failed to create $1 owl file"
    echo "$1 Script logs:"
    echo "$2"
    cleanup 1
  fi
  echo "$1 Script logs:"
  echo "$2"
  transformed_owl=$(echo "$2" | tail -1)
  echo "Generated owl file: $transformed_owl"
}

set_load_variables_of_transform() {
  echo "Setting up variables for the graph DB load. transformed owl file: $transformed_owl"
  if [[ ! -s $transformed_owl ]]; then
    echo "ERROR: Generated owl file is empty"
    cleanup 1
  fi
  # look up file ext again
  echo "  datafile:$datafile"
  if [[ ! $transformed_owl =~ f$$ ]]; then
    dataext=$(get_file_extension "$transformed_owl")
    datafile=$(get_file_name "$transformed_owl")
    mv "$transformed_owl" "$INPUT_DIRECTORY"/f$$."$datafile"."$dataext"
  else
    # When OWL file is extracted from compressed files, then it will already have the temp prefix. So strip that to find actual name and extension
    stripped_owl=${transformed_owl//f$$./}
    dataext=$(get_file_extension "$stripped_owl")
    datafile=$(get_file_name "$stripped_owl")
    echo "    after strip datafile:$datafile"
  fi
  file=$INPUT_DIRECTORY/f$$.$datafile.$dataext
  echo "    file = $file"
}

get_namespace() {
  echo $(grep -o 'xmlns="[^"]*"' "$1" | sed -e 's/xmlns="//g' -e 's/"//g' -e 's/#//g')
}

get_terminology() {
  lower_terminology=$(basename "$1" | sed 's/.owl//g; s/Ontology//; s/-//;' | tr '[:upper:]' '[:lower:]')
  if [[ $lower_terminology =~ "thesaurus" ]]; then
    echo "ncit"
  else
    #lower_terminology=$(basename "$1" | sed 's/.owl//g; s/Ontology//; s/-//;' | tr '[:upper:]' '[:lower:]')
    IFS='_' read -r -a array <<<"$lower_terminology"
    echo $array
  fi
}

get_version() {
  version=$(grep '<owl:versionInfo>' $1 | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//')
  if [[ -z "$version" ]]; then
    echo $(head -100 "$1" | grep 'owl:versionIRI' | perl -pe "s/.*\/(.*)\/$2.*/\1/")
  else
    echo $version
  fi
}

get_graph() {
  echo $(echo "$1" | sed -e "s/\.owl/_$2.owl/g")
}

get_data() {
  # If the file exists, copy it to /tmp preserving the extension
  if [[ -e $data ]]; then
    first_file_name="$INPUT_DIRECTORY"/f$$."$datafile"."$dataext"
    cp "$data" "$INPUT_DIRECTORY"/f$$."$datafile"."$dataext"

  # Otherwise, download it
  elif [[ $data = http* ]] || [[ $data = ftp* ]]; then
    IFS=',' read -r -a array <<<"$data"
    first_file_url=${array[0]}
    first_file_datafile=$(get_file_name "$first_file_url")
    first_file_dataext=$(get_file_extension "$first_file_url")
    first_file_name="$INPUT_DIRECTORY"/f$$."$first_file_datafile"."$first_file_dataext"
    for url in "${array[@]}"; do
      echo "    download = $url"
      datafile=$(get_file_name $url)
      dataext=$(get_file_extension $url)
      # there is no usable file name at the end of Canmed URLs. So using known string in the URL as file names
      if [[ $url == *"hcpcs"* ]]; then
        datafile="hcpcs"
        dataext="csv"
      fi
      if [[ $url == *"ndconc"* ]]; then
        datafile="ndconc"
        dataext="csv"
      fi
      echo "     download datafile:${datafile}"
      echo "     download dataext:${dataext}"
      curl --fail -v -o "$INPUT_DIRECTORY"/f$$."$datafile"."$dataext" "$url" >/tmp/x.$$.log 2>&1
      if [[ $? -ne 0 ]]; then
        cat /tmp/x.$$.log | sed 's/^/    /;'
        echo "ERROR: problem downloading file"
        cleanup 1
      fi
      # Setting the terminology name as $datafile to get to the correct transformation
      if [[ $datafile == "ndconc" ]]; then
        datafile="canmed"
      fi
    done
  else
    echo "ERROR: $data is not local or http/ftp"
    cleanup 1
  fi
}

extract_zipped_files() {
  echo "  extracting files from $1 to $INPUT_DIRECTORY"
  if [ -f "$1" ]; then
    if [[ $dataext == "zip" ]]; then
      echo "    extracting zip file"
      unzip "$1" -d "$INPUT_DIRECTORY"
      first_file_name=$(find "$INPUT_DIRECTORY" -maxdepth 1 -type f -name "*.owl" | head -n 1)
      first_file_datafile=$(get_file_name "$first_file_name")
      first_file_dataext=$(get_file_extension "$first_file_name")
    fi
    if [[ $dataext == "gz" ]]; then
      echo "    extracting gz file"
      # Based on gz naming convention, assuming the first part of the gz file name is the owl file name.
      gunzip "$INPUT_DIRECTORY"/f$$."$datafile"
      dataext=$(get_file_extension "$datafile")
      datafile=$(get_file_name "$datafile")
      first_file_datafile="$datafile"
      first_file_dataext="$dataext"
      first_file_name="$INPUT_DIRECTORY"/f$$."$first_file_datafile"."$first_file_dataext"
    fi
    if [[ $? -ne 0 ]]; then
      echo "ERROR: Problem unzipping file $1"
      cleanup 1
    fi
  else
    echo "  $1 does not exist. Exiting transformation"
    cleanup 1
  fi
}

apply_transformations() {
  if [[ ! -e $owl_file ]]; then
    echo "  Looking for transformations"
    IFS='_' read -r -a array <<<"$datafile"
    for terminology in "${array[@]}"; do
      echo "    Terminology from file name: $terminology"
      terminology_lower=$(echo "$terminology" | tr '[:upper:]' '[:lower:]')
      transformation_script=$DIR/transforms/"$terminology_lower".sh
      if [[ -e $transformation_script ]]; then
        echo "    Applying transformations for $terminology"
        script_output=$("$transformation_script" "$file")
        set_transformed_owl "$terminology" "$script_output"
        set_load_variables_of_transform
        break
      else
        echo "    No transformation script ($transformation_script) found"
      fi
    done
  else
    echo "  Found owl file: $owl_file"
    transformed_owl=$owl_file
    # The OWL file can either be extracted from a zip file or is native OWL file.
    # If extracted from zip file, we need to re-set the file name and extensions
    set_load_variables_of_transform
  fi
}

validate_owl_file() {
  # Verify that owl file is an owl file
  if [[ $dataext == "owl" ]] && [[ $(head -100 $file | grep -c owl:Ontology) -eq 0 ]]; then
    echo "ERROR: no owl:Ontology declaration in first 100 lines"
    cleanup 1
  fi
}

validate_weekly() {
  if [[ $weekly -eq 1 ]]; then
    if [[ $terminology != "ncit" ]]; then
      echo "ERROR: --weekly only makes sense when loading NCI Thesaurus"
      cleanup 1
    fi
    db=CTRP
  fi
}

qa_owl_file() {
  if [[ $force -eq 1 ]]; then
    echo "  SKIP QA on $file ...$(/bin/date)"
  else
    echo "  Run QA on $file ...$(/bin/date)"
    $DIR/stardog_qa.sh $terminology $file $weekly >/tmp/x.$$.log 2>&1
    if [[ $? -ne 0 ]]; then
      cat /tmp/x.$$.log | sed 's/^/    /;'
      echo "ERROR: QA errors, re-run with --force to bypass this"
      cleanup 1
    fi
  fi
}

check_if_version_exists() {
  # determine if there's a problem (duplicate graph/version)
  ct=$($DIR/list.sh $ncflag --quiet --graph_db | perl -pe 's/$l_graph_db_type/    /; s/\|/ /g;' | grep "$db.*$graph" | wc -l)
  if [[ $? -ne 0 ]]; then
    echo "ERROR: problem running list.sh"
    cleanup 1
  fi

  if [[ $ct -gt 0 ]] && [[ $force -eq 0 ]]; then
    echo "ERROR: graph is already loaded, use --force"
    cleanup 1
  fi
}

remove_graph() {
  echo "    Removing graph: $1. Db: $2"
  if [[ $l_graph_db_type == "stardog" ]]; then
    $l_graph_db_home/bin/stardog data remove -g $1 $2 -u $l_graph_db_username -p $l_graph_db_password | sed 's/^/    /'
  elif [[ $l_graph_db_type == "jena" ]]; then
    $l_graph_db_home/bin/s-delete $GRAPH_DB_URL/$2 $1 | sed 's/^/    /'
  fi
  if [[ $? -ne 0 ]]; then
    echo "ERROR: Problem running $l_graph_db_type to remove graph $1($2)"
    cleanup 1
  fi
}

force_remove_graph() {
  # Remove data if $force is set (remove from both DBs)
  if [[ $force -eq 1 ]]; then
    echo "  Remove graph (force mode) ...$(/bin/date)"
    remove_graph "$graph" "CTRP"
    remove_graph "$graph" "NCIT2"
  fi
}

load_data() {
  echo "  Load data ($db) ...$(/bin/date)"
  if [[ $l_graph_db_type == "stardog" ]]; then
    $l_graph_db_home/bin/stardog data add $db -g $graph $file -u $l_graph_db_username -p $l_graph_db_password | sed 's/^/    /'
  elif [[ $l_graph_db_type == "jena" ]]; then
    $l_graph_db_home/bin/s-put $GRAPH_DB_URL/$db $graph $file | sed 's/^/    /'
  fi
  if [[ $? -ne 0 ]]; then
    echo "ERROR: Problem loading $l_graph_db_type ($db)"
    cleanup 1
  fi
  # For monthly ncit, also load into CTRP db
  if [[ $terminology == "ncit" ]] && [[ $weekly -eq 0 ]]; then
    echo "  Load data (CTRP) ...$(/bin/date)"
    if [[ $l_graph_db_type == "stardog" ]]; then
      $l_graph_db_home/bin/stardog data add "CTRP" -g $graph $file -u $l_graph_db_username -p $l_graph_db_password | sed 's/^/    /'
    elif [[ $l_graph_db_type == "jena" ]]; then
      $l_graph_db_home/bin/s-put $GRAPH_DB_URL/$db $graph $file | sed 's/^/    /'
    fi
    if [[ $? -ne 0 ]]; then
      echo "ERROR: Problem loading $l_graph_db_type (CTRP)"
      cleanup 1
    fi
  fi
}

load_extra_owl_files() {
  # DUO has 2 OWL files. So load the other one (or others) as well.
  echo "  Loading other owl files in $INPUT_DIRECTORY"
  for of in "${owl_files[@]:1}"; do
    echo "    Loading $of"
    if [[ $l_graph_db_type == "stardog" ]]; then
      $l_graph_db_home/bin/stardog data add $db -g $graph $of -u $l_graph_db_username -p $l_graph_db_password | sed 's/^/    /'
    elif [[ $l_graph_db_type == "jena" ]]; then
      $l_graph_db_home/bin/s-put $GRAPH_DB_URL/$db $graph $file | sed 's/^/    /'
    fi
    if [[ $? -ne 0 ]]; then
      echo "ERROR: Problem loading $l_graph_db_type ($db)"
      cleanup 1
    fi
  done
}

remove_older_versions() {
  # Remove older versions here
  maxVersions=1
  if [[ $(grep -c maxVersions $DIR/../config/metadata/$terminology.json) -gt 0 ]]; then
    maxVersions=$(grep maxVersions $DIR/../config/metadata/$terminology.json | perl -pe 's/.*\:\s*(\d+),.*/$1/;')
  fi
  echo "  Remove old monthly version (maxVersions=$maxVersions) ...$(/bin/date)"
  monthly_graphs=$($DIR/list.sh $ncflag --quiet --graph_db | grep -w $terminology | grep -w NCIT2 | awk -F\| '{print $5}')
  monthly_graphs_array=(${monthly_graphs})
  echo "  Found ${#monthly_graphs_array[@]} versions"
  if [[ ${#monthly_graphs_array[@]} -gt maxVersions ]]; then
    for graph_to_remove in "${monthly_graphs_array[@]:0:${#monthly_graphs_array[@]}-maxVersions}"; do
      remove_graph "$graph_to_remove" "NCIT2"
    done
  fi

  echo "  Remove old weekly versions (will keep only 1)...$(/bin/date)"
  weekly_graphs=$($DIR/list.sh $ncflag --quiet --graph_db | grep -w $terminology | grep -w CTRP | awk -F\| '{print $5}')
  weekly_graphs_array=(${weekly_graphs})
  for graph_to_remove in "${weekly_graphs_array[@]:0:${#weekly_graphs_array[@]}-1}"; do
    remove_graph "$graph_to_remove" "CTRP"
  done
}

cleanup() {
  # cleanup log files
  local code=$1
  /bin/rm $DIR/f$$.$datafile.$dataext /tmp/x.$$.log >/dev/null 2>&1
  /bin/rm -rf "$WORK_DIRECTORY"

  if [ "$code" != "" ]; then
    exit $code
  fi
}

print_completion() {
  echo ""
  echo "--------------------------------------------------"
  echo "Finished ...$(/bin/date)"
  echo "--------------------------------------------------"
}

# Verify jq installed
jq --help >>/dev/null 2>&1
if [[ $? -eq 0 ]]; then
  jq="jq ."
else
  jq="python -m json.tool"
fi

# Set directory of this script so we can call relative scripts
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
WORK_DIRECTORY=$DIR/work
INPUT_DIRECTORY=$WORK_DIRECTORY/input
OUTPUT_DIRECTORY=$WORK_DIRECTORY/output

echo "--------------------------------------------------"
echo "Starting ...$(/bin/date)"
echo "--------------------------------------------------"
echo "DIR = $DIR"
echo "data = $data"
echo "force = $force"
echo "weekly = $weekly"

echo "  setup_configuration...$(/bin/date)"
setup_configuration
l_graph_db_type=${GRAPH_DB_TYPE:-"stardog"}
l_graph_db_home=$GRAPH_DB_HOME
l_graph_db_username=$GRAPH_DB_USERNAME
l_graph_db_password=$GRAPH_DB_PASSWORD
echo "    GRAPH_DB_TYPE = $l_graph_db_type"
echo ""

if [[ $data == "optimize" ]]; then
  optimize_stardog_dbs
  print_completion
  exit 0
fi

echo "  setup...$(/bin/date)"
setup
validate_setup
echo "  Put data in standard location - $INPUT_DIRECTORY ...$(/bin/date)"
dataext=$(get_file_extension $data)
datafile=$(get_file_name $data)
echo "  get_data...$(/bin/date)"
get_data
file="$INPUT_DIRECTORY"/f$$.$datafile.$dataext
echo "    file = $file"
if [[ $dataext == "zip" ]] || [[ $dataext == "gz" ]]; then
  extract_zipped_files "$file"
fi
echo "  first_file_name: $first_file_name"
echo "  first_file_datafile: $first_file_datafile"
str_owl_files=$(get_owl_files "$first_file_name" "$first_file_datafile")
echo "  str_owl_files:$str_owl_files"
read -r -a owl_files <<<"$str_owl_files"
if [ "${#owl_files[@]}" -gt 0 ]; then
  owl_file=${owl_files[0]}
fi
echo "  output from get_owl_file: $owl_file"
echo "  apply_transformations...$(/bin/date)"
apply_transformations
validate_owl_file
# determine graph/version
echo "  Determine graph and version ...$(/bin/date)"
namespace=$(get_namespace "$file")
echo "  Namespace of OWL file:$namespace"
terminology=$(get_terminology "$namespace")
echo "  Terminology:$terminology"
version=$(get_version "$file" "$terminology")
echo "  Version:$version"
graph=$(get_graph "$namespace" "$version")
echo "  Graph:$graph"

db=NCIT2
validate_weekly
echo "  qa_owl_file...$(/bin/date)"
qa_owl_file
check_if_version_exists
force_remove_graph
echo "  load_data...$(/bin/date)"
load_data
load_extra_owl_files
remove_older_versions
optimize_stardog_db $db
# For monthly ncit, also loaded into CTRP db. So optimize
if [[ $terminology == "ncit" ]] && [[ $weekly -eq 0 ]]; then
  optimize_stardog_db "CTRP"
fi
cleanup
print_completion