# create a bash script that would check if a configuration index exists in elasticsearch. If the configuration index does not exist, create the index. Call GRAPHDB_URL/$/server. It will return a JSON. Read the datasets field. It is an array. Use jq to read datasets field and each array entry will have ds.name. In the configuration index store the ds.name as the "name" field and if the database name is CTRP then store the weekly field as true. Otherwise set weekly field as false. So basically there will be a document per dataset in the configuration index.
config=1
ncflag=""
help=0
quite=0

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
DEFAULT_DBS=(CTRP NCIT2)

while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # avoid printing header/footer
    --quiet) quiet=1;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

if [[ $help -eq 1 ]]; then
    echo "Usage: $0 [--noconfig] [--quiet] [--help]"
    echo "  e.g. $0 --noconfig"
    echo "  e.g. $0 --quiet"
    exit 1
fi

# Verify jq installed
jq --help >> /dev/null 2>&1
if [[ $? -eq 0 ]]; then
    jq="jq ."
else
    echo "ERROR: jq is not installed. Please install jq to use this script."
    exit 1
fi

if [[ $quiet -eq 0 ]]; then
    echo "--------------------------------------------------"
    echo "Starting ...`/bin/date`"
    echo "--------------------------------------------------"
fi

# Setup configuration
if [[ $quiet -eq 0 ]]; then
    echo "  Setup configuration"
fi

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

validate_setup() {
  if [[ -z "$GRAPH_DB_HOST" ]]; then
    echo "Error: Both GRAPH_DB_HOST and STARDOG_HOST are not set."
    exit 1
  fi
  if [[ -z "$GRAPH_DB_PORT" ]]; then
    echo "GRAPH_DB_PORT is not set. Using default"
    GRAPH_DB_PORT="3030"
  fi
  GRAPH_DB_URL="${GRAPH_DB_SCHEME:-http}://${GRAPH_DB_HOST}:${GRAPH_DB_PORT}"
  # check if ${ES_SCHEME}://${ES_HOST}:${ES_PORT} is set
  if [[ -z "$ES_SCHEME" || -z "$ES_HOST" || -z "$ES_PORT" ]]; then
    echo "ERROR: ES_SCHEME, ES_HOST, or ES_PORT is not set."
    exit 1
  else
    ES="${ES_SCHEME}://${ES_HOST}:${ES_PORT}"
  fi
}

# Check if configuration index exists in Elasticsearch
check_and_create_index() {
  local index_name="configuration"
  local index_exists=$(curl -s -o /dev/null -w "%{http_code}" "$ES/$index_name")

  if [[ $index_exists -ne 200 ]]; then
    echo "Configuration index does not exist. Creating index: $index_name"
    curl -s -o /dev/null -X PUT "$ES/$index_name" -H 'Content-Type: application/json' -d '{
      "mappings": {
        "properties": {
          "name": { "type": "keyword" },
          "weekly": { "type": "boolean" }
        }
      }
    }'
  else
    echo "Configuration index already exists."
  fi
}

get_database_names(){
  local dbs=$(echo "$1" | jq -r '.[].name')
  echo "$dbs"
}

check_for_default_dbs(){
  local db_names=$(get_database_names "$1")
  local created_database=0
  for db in "${DEFAULT_DBS[@]}"; do
    if ! echo "$db_names" | grep -q "^$db$"; then
      echo "Database $db does not exist. Creating it."
      create_database "$db"
    fi
  done
}

# Read datasets from GraphDB and store in configuration index
store_datasets() {
  local jq_expression='[.datasets[] | {name: (.["ds.name"] | ltrimstr("/")), weekly: (.["ds.name"] == "/CTRP")}] | sort_by(.name)'
  local datasets=$(curl -s "$GRAPH_DB_URL/$/server" | jq -c "$jq_expression")
  check_for_default_dbs "$datasets"
  # Re-pull datasets after checking for default databases because the check may have created default databases if missing
  datasets=$(curl -s "$GRAPH_DB_URL/$/server" | jq -c "$jq_expression")
  # delete existing documents in configuration index
  echo "Deleting existing documents in configuration index"
  curl -s -o /dev/null -X POST "$ES/configuration/_delete_by_query" -H 'Content-Type: application/json' -d '{"query": {"match_all": {}}}'
  echo "$datasets" | jq -c '.[]' | while read -r dataset; do
    local name=$(echo "$dataset" | jq -r '.name')
    local weekly=$(echo "$dataset" | jq -r '.weekly')

    echo "Storing dataset: $name, Weekly: $weekly"
    curl -s -o /dev/null -X POST "$ES/configuration/_doc" -H 'Content-Type: application/json' -d "{\"name\": \"$name\", \"weekly\": $weekly}"

    if [[ $? -ne 0 ]]; then
      echo "ERROR: Failed to store dataset $name in configuration index."
      exit 1
    fi
  done
}

create_database(){
  echo "    Creating $1"
  curl -s -g -X POST -d "dbName=$1&dbType=tdb2" "$GRAPH_DB_URL/$/datasets" > /dev/null
  if [[ $? -ne 0 ]]; then
      echo "Error occurred when creating database $1. Response:$_"
      exit 1
  fi
}

setup_configuration
validate_setup
check_and_create_index
store_datasets