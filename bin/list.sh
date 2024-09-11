#!/bin/bash -f
#
# This script lists databases, terminologies, versions, graphs
# available in the configured graph db and elasticsearch.
# The --noconfig flag is for running in the dev environment
# where the setenv.sh file does not exist.
#
config=1
ncflag=""
help=0
quiet=0
graph_db=1
es=1

l_graph_db_type=${GRAPH_DB_TYPE:-"stardog"}
l_graph_db_host="localhost"
l_graph_db_port="5820"
l_graph_db_username=""
l_graph_db_password=""

while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # avoid printing header/footer
    --quiet) quiet=1;;
    # show graph DB data only
    --graph_db) es=0;;
    # show es data only
    --es) graph_db=0;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

if [ ${#arr[@]} -ne 0 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--noconfig] [--quiet] [--graphdb] [--es] [--help]"
    echo "  e.g. $0 --noconfig"
    echo "  e.g. $0 --noconfig --graphdb"
    echo "  e.g. $0 --noconfig --quiet --graphdb"
    echo "  e.g. $0 --noconfig --es"
    echo "  e.g. $0 --noconfig --quiet --es"
    exit 1
fi

# Set up ability to format json
jq --help >> /dev/null 2>&1
if [[ $? -eq 0 ]]; then
    jq="jq ."
else
    jq="python -m json.tool"
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
  if [[ $l_graph_db_type == "stardog" ]]; then
    if [[ -n "$GRAPH_DB_HOST" ]]; then
      l_graph_db_host="$GRAPH_DB_HOST"
    elif [[ -n "$STARDOG_HOST" ]]; then
      l_graph_db_host="$STARDOG_HOST"
    else
      echo "Error: Both GRAPH_DB_HOST and STARDOG_HOST are not set."
      exit 1
    fi
    if [[ -n "$GRAPH_DB_PORT" ]]; then
      l_graph_db_port="$GRAPH_DB_PORT"
    elif [[ -n "$STARDOG_PORT" ]]; then
      l_graph_db_port="$STARDOG_PORT"
    else
      echo "Both GRAPH_DB_PORT and STARDOG_PORT are not set. Using default"
      l_graph_db_port="5820"
    fi
    if [[ -n "$GRAPH_DB_USERNAME" ]]; then
      l_graph_db_username="$GRAPH_DB_USERNAME"
    elif [[ -n "$STARDOG_USERNAME" ]]; then
      l_graph_db_username="$STARDOG_USERNAME"
    else
      echo "Error: Both GRAPH_DB_HOME and STARDOG_USERNAME are not set."
      exit 1
    fi
    if [[ -n "$GRAPH_DB_PASSWORD" ]]; then
      l_graph_db_password="$GRAPH_DB_PASSWORD"
    elif [[ -n "$STARDOG_PASSWORD" ]]; then
      l_graph_db_password="$STARDOG_PASSWORD"
    else
      echo "Error: Both GRAPH_DB_HOME and STARDOG_PASSWORD are not set."
      exit 1
    fi
  elif [[ $l_graph_db_type == "jena" ]]; then
    if [[ -z $GRAPH_DB_HOST ]]; then
      echo "    ERROR: $GRAPH_DB_HOST is not set"
      exit 1
    else
      l_graph_db_host="$GRAPH_DB_HOST"
    fi
    if [[ -z $GRAPH_DB_PORT ]]; then
      echo "    $GRAPH_DB_PORT is not set. Setting default"
      l_graph_db_port="3030"
    else
      l_graph_db_port="$GRAPH_DB_PORT"
    fi
  fi
}

setup_configuration
validate_setup
ES=${ES_SCHEME}://${ES_HOST}:${ES_PORT}

if [[ $quiet -eq 0 ]]; then
    echo "    graph_db = http://${l_graph_db_host}:${l_graph_db_port}"
    echo "    elasticsearch = ${ES}"
    echo ""
fi

if [[ $quiet -eq 0 ]]; then
    echo "  Lookup graph_db info ...`/bin/date`"
fi

get_databases(){
  if [[ $l_graph_db_type == "stardog" ]]; then
    curl -s -g -u "${l_graph_db_username}:$l_graph_db_password" \
        "http://${l_graph_db_host}:${l_graph_db_port}/admin/databases" |\
        jq -r '.databases[]' > /tmp/db.$$.txt
  elif [[ $l_graph_db_type == "jena" ]]; then
    curl -s -g "http://${l_graph_db_host}:${l_graph_db_port}/$/server" |\
        jq -r '.datasets[]."ds.name"|.[1:]' > /tmp/db.$$.txt
  fi
  if [[ $? -ne 0 ]]; then
      echo "ERROR: unexpected problem listing databases"
      exit 1
  fi

  if [[ $quiet -eq 0 ]]; then
      echo "    databases = " `cat /tmp/db.$$.txt`
  fi
  ct=`cat /tmp/db.$$.txt | wc -l`
  if [[ $ct -eq 0 ]]; then
      echo "ERROR: no graph databases, this is unexpected"
      exit 1
  fi
}

get_ignored_sources(){
  if [ -f "../config/metadata/ignore-source.txt" ]; then
    echo $(cat "../config/metadata/ignore-source.txt" | awk -vORS=">,<" '{ print $1 }' | sed 's/,<$//' | sed 's/^/</')
  else
    echo ""
  fi
}

get_graphs(){
ignored_sources=$(get_ignored_sources)
echo "    Ignored source URLs:${ignored_sources}"
if [ -n "$ignored_sources" ];then
cat > /tmp/x.$$.txt << EOF
query=PREFIX owl:<http://www.w3.org/2002/07/owl#>
PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:<http://www.w3.org/2001/XMLSchema#>
PREFIX dc:<http://purl.org/dc/elements/1.1/>
PREFIX xml:<http://www.w3.org/2001/XMLSchema>
select distinct ?source ?graphName ?version where {
  graph ?graphName {
    {
      ?source a owl:Ontology .
      ?source owl:versionInfo ?version .
      FILTER (?source NOT IN ($ignored_sources))
    }
    UNION
    {
      ?source a owl:Ontology .
      ?source owl:versionIRI ?version .
      FILTER NOT EXISTS { ?source owl:versionInfo ?versionInfo } .
      FILTER (?source NOT IN ($ignored_sources))
    }
  }
}
EOF
else
cat > /tmp/x.$$.txt << EOF
query=PREFIX owl:<http://www.w3.org/2002/07/owl#>
PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:<http://www.w3.org/2001/XMLSchema#>
PREFIX dc:<http://purl.org/dc/elements/1.1/>
PREFIX xml:<http://www.w3.org/2001/XMLSchema>
select distinct ?source ?graphName ?version where {
  graph ?graphName {
    {
      ?source a owl:Ontology .
      ?source owl:versionInfo ?version .
    }
    UNION
    {
      ?source a owl:Ontology .
      ?source owl:versionIRI ?version .
      FILTER NOT EXISTS { ?source owl:versionInfo ?versionInfo } .
    }
  }
}
EOF
fi
}

get_terminology(){
  lower_terminology=$(basename "$1" | sed 's/.owl//g; s/Ontology//; s/-//;' | tr '[:upper:]' '[:lower:]')
  if [[ $lower_terminology =~ "thesaurus" ]]; then
    echo "ncit"
  else
    #lower_terminology=$(basename "$1" | sed 's/.owl//g; s/Ontology//; s/-//;' | tr '[:upper:]' '[:lower:]')
    IFS='_' read -r -a array <<<"$lower_terminology"
    echo $array
  fi
}

if [[ $graph_db -eq 1 ]]; then
echo "  Getting databases"
get_databases
get_graphs
query=`cat /tmp/x.$$.txt`

# Run the query against each of the databases
/bin/rm -f /tmp/y.$$.txt
touch /tmp/y.$$.txt
for db in `cat /tmp/db.$$.txt`; do
    curl -s -g -u "${l_graph_db_username}:$l_graph_db_password" \
        http://${l_graph_db_host}:${l_graph_db_port}/$db/query \
        --data-urlencode "$query" -H "Accept: application/sparql-results+json" |\
        jq -r --arg db "$db" '.results.bindings[] | .version.value + "|"+$db+"|" + .source.value + "|" + .graphName.value' >> /tmp/y.$$.txt
    if [[ $? -ne 0 ]]; then
        echo "ERROR: unexpected problem obtaining $db versions from $l_graph_db_type"
        exit 1
    fi
done

# Sort by version then reverse by DB (NCIT2 goes before CTRP)
# this is because we need "monthly" to be indexed from the "monthlyDb"
# defined in ncit.json
sort -t\| -k 1,1 -k 2,2r -o /tmp/y.$$.txt /tmp/y.$$.txt

if [[ $quiet -eq 0 ]]; then
    echo "  List $l_graph_db_type graphs ...`/bin/date`"
fi
# Here determine the parts for each case

for x in `cat /tmp/y.$$.txt`; do
    version=`echo $x | cut -d\| -f 1 | perl -pe 's#.*/(.*)/[a-zA-Z]+.owl#$1#;'`
    db=`echo $x | cut -d\| -f 2`
    uri=`echo $x | cut -d\| -f 3`
    graph_uri=`echo $x | cut -d\| -f 4`
    term=$(get_terminology "$uri")
    if [[ $quiet -eq 1 ]]; then
        echo "$l_graph_db_type|$db|$term|$version|$graph_uri"
    else
        echo "    $db $term $version $graph_uri"
    fi
done

fi

if [[ $es -eq 1 ]]; then

if [[ $quiet -eq 0 ]]; then
    echo "  List elasticsearch indexes ...`/bin/date`"
fi
if [[ $quiet -eq 0 ]]; then
# TODO: this doesn't work without "jq" installed
curl -s "$ES/evs_metadata/_search?size=10000"  |\
   $jq | grep terminologyVersion | perl -pe 's/(?<!snomedct)_/ /; s/.*"\: ?"//; s/".*//' |\
   sort | sed 's/^/    /'
else
curl -s "$ES/evs_metadata/_search?size=10000"  |\
   $jq | grep terminologyVersion | perl -pe 's/(?<!snomedct)_/|/; s/.*"\: ?"//; s/".*//' |\
   sort | sed 's/^/es|/'
fi
if [[ $? -ne 0 ]]; then
    echo "ERROR: problem looking up indexes"
    exit 1
fi

fi

# Cleanup
/bin/rm -f /tmp/db.$$.txt /tmp/[xy].$$.txt

if [[ $quiet -eq 0 ]]; then
    echo ""
    echo "--------------------------------------------------"
    echo "Finished ...`/bin/date`"
    echo "--------------------------------------------------"
fi
