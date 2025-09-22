config=1
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
if [[ "$DIR" == /cygdrive/* ]]; then DIR=$(echo "$DIR" | sed 's|^/cygdrive/\([a-zA-Z]\)/\(.*\)|\1:/\2|'); fi
PATCHES_DIRECTORY=$DIR/patches

while [[ "$#" -gt 0 ]]; do
  case $1 in
  --noconfig)
    config=0
    ncflag="--noconfig"
    ;;
  *) arr=("${arr[@]}" "$1") ;;
  esac
  shift
done

data="${arr[0]}"

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

print_env(){
  echo "Printing Environment"
  echo "GRAPH_DB_TYPE=$GRAPH_DB_TYPE"
  echo "GRAPH_DB_HOME=$GRAPH_DB_HOME"
  echo "GRAPH_DB_URL=$GRAPH_DB_URL"
  echo "GRAPH_DB_USERNAME=$GRAPH_DB_USERNAME"
  echo "GRAPH_DB_PASSWORD=****"
  echo "STARDOG_HOME=$STARDOG_HOME"
  echo "STARDOG_USERNAME=$STARDOG_USERNAME"
  echo "STARDOG_PASSWORD=****"
  java -version
  if [[ $config -eq 1 ]]; then
    echo "Printing config file: $CONFIG_ENV_FILE"
    cat "$CONFIG_ENV_FILE"
  fi
  if [[ -n $GRAPH_DB_URL ]]; then
    success=$(curl -s -f -o /dev/null -w "%{http_code}" "$GRAPH_DB_URL/$/server" | grep -q "200")
    if [[ $success -eq 0 ]]; then
      echo "Jena server is running"
    else
      echo "Jena server is not running"
    fi
  fi
  evsrestapi_operations_version=$(head -1 "$DIR"/../Makefile | perl -pe 's/.*=(.*)/\1/')
  echo "evsrestapi_operations_version=$evsrestapi_operations_version"
  print_completion
  exit 0
}

run_list_command(){
    # call list.sh to check DBs exist. If not, that script will create them.
    # Note that there is a security restriction in Fuseki that only allows localhost host name to call admin endpoints.
    if [[ $config -eq 1 ]]; then
      GRAPH_HOST=localhost "$DIR"/list.sh 2>&1
    else
      GRAPH_HOST=localhost "$DIR"/list.sh --noconfig 2>&1
    fi
    if [[ $? -ne 0 ]]; then
      echo "ERROR: problem running list.sh"
    fi
    print_completion
    exit 0
}

run_remove_command(){
    echo "  Running remove.sh ...$(/bin/date)"
    
    # Check if --mapset flag is present
    mapset_flag=0
    for token in "${arr[@]}"; do
        if [[ $token == "--mapset" ]]; then
            mapset_flag=1
            break
        fi
    done
    

    # Validate arguments based on mapset flag
    if [[ $mapset_flag -eq 1 ]]; then
        # For mapset removal, we need exactly 3 arguments: "remove", "--mapset", "<mapset_code>"
        if [ ${#arr[@]} -ne 3 ]; then
            echo "Usage: $0 [--noconfig] [--help] remove --mapset <mapset_code>"
            echo "  e.g. $0 remove --mapset NCIt_to_HGNC_Mapping"
            exit 1
        fi
    else
        # For terminology removal, we need exactly 4 arguments: "remove", "<terminology>", "<version>", "<flag>"
        if [ ${#arr[@]} -ne 4 ]; then
            echo "Usage: $0 [--noconfig] [--help] remove [--graphdb] [--es] <terminology> <version>"
            echo "  e.g. $0 remove ncit 20.09d --graphdb"
            echo "  e.g. $0 remove ncim 202102 --es"
            exit 1
        fi
    fi

    # Build the remove arguments array (excluding "remove")
    remove_args=()
    for token in "${arr[@]}"; do
        if [[ $token == "remove" ]]; then
            continue
        fi
        # add the token to the remove arguments array
        remove_args+=("$token")
    done
    
    # print all remove args for debugging
    echo "    remove.sh arguments: ${remove_args[@]}"
    
    # Call remove.sh with the arguments
    "$DIR/remove.sh" $ncflag "${remove_args[@]}" 2>&1
    exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo "ERROR: remove.sh failed with exit code $exit_code"
        exit $exit_code
    fi
    print_completion
    exit 0
}
run_metadata_command(){
    echo "  Running metadata.sh ...$(/bin/date)"
    if [ ${#arr[@]} -ne 4 ]; then
        echo "Usage: $0 [--noconfig] [--help] metadata <terminology> <version> <config>"
        echo "  e.g. $0 metadata ncit 2106e ../path/to/ncit.json"
        echo "  e.g. $0 metadata ncit 2106e https://example.com/path/to/ncit.json"
        echo "  e.g. $0 metadata ncim 202102 ../path/to/ncim.json"
        exit 1
    fi
    for token in "${arr[@]}"; do
      if [[ $token == "metadata" ]]; then
        continue
      fi
      # add the token to the metadata arguments array
      metadata_args+=("$token")
    done
    # print all remove args
    "$DIR/metadata.sh" $ncflag "${metadata_args[@]}" 2>&1
    exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
      echo "ERROR: metadata.sh failed with exit code $exit_code"
      exit $exit_code
    fi
    print_completion
    exit 0
}

run_patch_command(){
    echo "  Running patch run.sh ...$(/bin/date)"

    for token in "${arr[@]}"; do
      if [[ $token == "patch" ]]; then
        continue
      fi
      # add the token to the remove arguments array
      patch_args+=("$token")
    done
    if [[ ${#patch_args[@]} -lt 1 ]]; then
      echo "ERROR: No patch version specified"
      exit 1
    fi
    l_patches_directory=$PATCHES_DIRECTORY/${patch_args[0]}
    # check if patches directory exists
    if [[ ! -d "$l_patches_directory" ]]; then
      echo "ERROR: Patches directory ${l_patches_directory} does not exist"
      exit 1
    fi
    # call run.sh in patches directory.
    "$l_patches_directory/run.sh" $ncflag "${patch_args[@]:1}" 2>&1
    exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
      echo "ERROR: $l_patches_directory/run.sh failed with exit code $exit_code"
      exit $exit_code
    fi
    print_completion
    exit 0
}

run_drop_ctrp_db() {
    echo "    Dropping CTRP DB ...`/bin/date`"
    curl -i -s -f -X DELETE "$GRAPH_DB_URL/$/datasets/CTRP" > /dev/null 2>&1
    if [[ $? -ne 0 ]]; then
        echo "Error occurred when dropping CTRP database. Response:$_"
        exit 1
    fi
    exit 0
}

run_commands(){
  if [[ $data == "print_env" ]]; then
    print_env
  fi
  if [[ $data == "list" ]]; then
    run_list_command
  fi
  if [[ $data =~ "remove" ]]; then
    run_remove_command
  fi
  if [[ $data =~ "patch" ]]; then
    run_patch_command
  fi
  if [[ $data == "drop_ctrp_db" ]]; then
    run_drop_ctrp_db
  fi
  if [[ $data == "metadata" ]]; then
    run_metadata_command
  fi
}

print_completion() {
  echo ""
  echo "--------------------------------------------------"
  echo "Finished ...$(/bin/date)"
  echo "--------------------------------------------------"
}

run_commands "$@"
