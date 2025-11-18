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
graphdb=1
es=1

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
if [[ "$DIR" == /cygdrive/* ]]; then DIR=$(echo "$DIR" | sed 's|^/cygdrive/\([a-zA-Z]\)/\(.*\)|\1:/\2|'); fi

while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # avoid printing header/footer
    --quiet) quiet=1;;
    # show graph DB data only
    --graphdb) es=0;;
    --stardog) es=0;;
    --jena) es=0;;
    # show es data only
    --es) graphdb=0;;
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
  if [[ -n "$GRAPH_DB_PASSWORD" ]]; then
    l_graph_db_password="$GRAPH_DB_PASSWORD"
  elif [[ -n "$STARDOG_PASSWORD" ]]; then
    l_graph_db_password="$STARDOG_PASSWORD"
  else
    echo "Error: Both GRAPH_DB_HOME and STARDOG_PASSWORD are not set."
    exit 1
  fi
  
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
  if [[ -z "$ES_SCHEME" || -z "$ES_HOST" || -z "$ES_PORT" ]]; then
    echo "  ERROR: ES_SCHEME, ES_HOST, or ES_PORT is not set."
    exit 1
  else
    ES="${ES_SCHEME}://${ES_HOST}:${ES_PORT}"
  fi
}

setup_configuration
validate_setup

l_graph_db_type=${GRAPH_DB_TYPE:-"stardog"}
l_graph_db_host=${GRAPH_DB_HOST:-"localhost"}
l_graph_db_port=${GRAPH_DB_PORT:-"5820"}
export GRAPH_DB_TYPE=$l_graph_db_type

if [[ $quiet -eq 0 ]]; then
    echo "    graphdb type = ${l_graph_db_type}"
    echo "    graphdb = http://${l_graph_db_host}:${l_graph_db_port}"
    echo "    elasticsearch = ${ES}"
    echo ""
fi

if [[ $quiet -eq 0 ]]; then
    echo "  Lookup graphdb info ...`/bin/date`"
fi

get_databases(){

  if [[ $l_graph_db_type == "stardog" ]]; then
    # print the curl command to stdout
    echo "    curl -s -g -u \"${l_graph_db_username}:****\" \"http://${l_graph_db_host}:${l_graph_db_port}/admin/databases\""
    curl -s -g -u "${l_graph_db_username}:$l_graph_db_password" \
        "http://${l_graph_db_host}:${l_graph_db_port}/admin/databases" |\
        python3 "$DIR/get_databases.py" "$GRAPH_DB_TYPE" > /tmp/db.$$.txt
  elif [[ $l_graph_db_type == "jena" ]]; then
    # query ES for the databases. The databases are stored in the configuration index. if the index does not exist, print an error and exit
    # check if the configuration index exists
    if [[ -z $(curl -s "$ES/configuration/_search?size=1" | jq -r '.hits.hits[0]') ]]; then
      echo "ERROR: configuration index does not exist. Run init.sh first."
      exit 1
    fi
    curl -s "$ES/configuration/_search" | jq -r '.hits.hits[]._source.name' > /tmp/db.$$.txt
  fi
  if [[ $? -ne 0 ]]; then
      echo "ERROR: unexpected problem listing databases. Try running init.sh first."
      exit 1
  fi

  if [[ $quiet -eq 0 ]]; then
      echo "    databases = `cat /tmp/db.$$.txt | perl -ne 'chop; s/\r//; print "$_ "'`"
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

if [[ $graphdb -eq 1 ]]; then
echo "  Getting databases"
get_databases
get_graphs
query=`cat /tmp/x.$$.txt`

# Run the query against each of the databases
/bin/rm -f /tmp/y.$$.txt
touch /tmp/y.$$.txt
for db in `cat /tmp/db.$$.txt`; do
    # Remove any whitespace or carriage returns for dos/unix compatibility
    db=$(echo "$db" | perl -pe 's/\r//;')
    curl -s -g -u "${l_graph_db_username}:$l_graph_db_password" \
        http://${l_graph_db_host}:${l_graph_db_port}/$db/query \
        --data-urlencode "$query" -H "Accept: application/sparql-results+json" |\
        python3 "$DIR/get_graphs.py" "$db" >> /tmp/y.$$.txt
    if [[ $? -ne 0 ]]; then
        echo "ERROR: unexpected problem obtaining $db versions from $l_graph_db_type"
        exit 1
    fi
done

# Sort by version then reverse by DB (NCIT2 goes before CTRP)
# this is because we need "monthly" to be indexed from the "monthlyDb"
# defined in ncit.json
sort -t\| -k 1,1 -k 2,2r /tmp/y.$$.txt > /tmp/z.$$.txt && mv /tmp/z.$$.txt /tmp/y.$$.txt

if [[ $quiet -eq 0 ]]; then
    echo "  List $l_graph_db_type graphs ...`/bin/date`"
fi

# Get graphs and sort by graphdb
for x in `cat /tmp/y.$$.txt | perl -pe 's/\r//;' | sort -t\| -k 2,2`; do
    if [[ -n "$x" ]]; then
        # Debug: Check if we have the expected pipe-separated format
        field_count=$(echo "$x" | tr -cd '|' | wc -c)
        if [[ $field_count -lt 3 ]]; then
            echo "    WARNING: Malformed data line: $x" >&2
            continue
        fi

        version=`echo $x | cut -d\| -f 1 | perl -pe 's#.*/(.*)/[a-zA-Z]+.owl#$1#;' | perl -pe 's/\r//;'`
        db=`echo $x | cut -d\| -f 2 | perl -pe 's/\r//;'`
        graph_uri=`echo $x | cut -d\| -f 3 | perl -pe 's/\r//;'`
        uri=`echo $x | cut -d\| -f 4 | perl -pe 's/\r//;'`
        term=$(get_terminology "$uri")

        if [[ $quiet -eq 1 ]]; then
            echo "$l_graph_db_type|$db|$term|$version|$graph_uri"
        else
            printf "    %-10s %-15s %-15s %s\n" "$db" "$term" "$version" "$graph_uri"
        fi
    fi
done

fi

if [[ $es -eq 1 ]]; then

if [[ $quiet -eq 0 ]]; then echo "  List elasticsearch indexes ...`/bin/date`"; fi

curl -s "$ES/evs_metadata/_search?size=10000"  |\
    $jq | grep terminologyVersion | perl -pe 's/(?<!snomedct)_/ /; s/.*"\: ?"//; s/".*//' |\
    sort -u -o /tmp/x.txt

if [[ $? -ne 0 ]]; then
    echo "ERROR: problem looking up indexes"
    exit 1
fi

if [[ $quiet -eq 0 ]]; then

    sort /tmp/x.txt| sed 's/^/    /'

    # Fix up versions for compare
    curl -s "$ES/_cat/indices" | grep concept_ | cut -d\  -f 3 | perl -pe 's/concept_//; s/_/ /; s/ us_/_us /;' |\
       perl -ne 'chop; @_=split/ /; if ($_[0] eq "umlssemnet") { print "$_[0] ".uc($_[1])."\n"; } else { print "$_[0] $_[1]\n" }' |\
       sort -u -o /tmp/y.txt

    curl -s "$ES/_cat/indices" | grep evs_object_ | cut -d\  -f 3 | perl -pe 's/evs_object_//; s/_/ /; s/ us_/_us /;' |\
       perl -ne 'chop; @_=split/ /; if ($_[0] eq "umlssemnet") { print "$_[0] ".uc($_[1])."\n"; } else { print "$_[0] $_[1]\n" }' |\
       sort -u -o /tmp/z.txt

    ct=`perl -ne 'chop; @_=split/ /; $_[1]=~ s/[\-\.]//g; print "$_[0] $_[1]\n"' /tmp/x.txt | comm -23 - /tmp/y.txt | wc -l`
    if [ $ct -ne 0 ]; then
        echo "WARNING: evs_metadata entries without concept indexes"
        perl -ne 'chop; @_=split/ /; $_[1]=~ s/[\-\.]//g; print "$_[0] $_[1]\n"' /tmp/x.txt | comm -23 - /tmp/y.txt | sed 's/^/    /'
    fi

    ct=`perl -ne 'chop; @_=split/ /; $_[1]=~ s/[\-\.]//g; print "$_[0] $_[1]\n"' /tmp/x.txt | comm -13 - /tmp/y.txt | wc -l`
    if [ $ct -ne 0 ]; then
        echo "WARNING: concept indexes without evs_metadata entries"
        perl -ne 'chop; @_=split/ /; $_[1]=~ s/[\-\.]//g; print "$_[0] $_[1]\n"' /tmp/x.txt | comm -13 - /tmp/y.txt | sed 's/^/    /'
    fi

    ct=`perl -ne 'chop; @_=split/ /; $_[1]=~ s/[\-\.]//g; print "$_[0] $_[1]\n"' /tmp/x.txt | comm -23 - /tmp/z.txt | wc -l`
    if [ $ct -ne 0 ]; then
        echo "WARNING: evs_metadata entries without evs_object indexes"
        perl -ne 'chop; @_=split/ /; $_[1]=~ s/[\-\.]//g; print "$_[0] $_[1]\n"' /tmp/x.txt | comm -23 - /tmp/z.txt | sed 's/^/    /'
    fi

    ct=`perl -ne 'chop; @_=split/ /; $_[1]=~ s/[\-\.]//g; print "$_[0] $_[1]\n"' /tmp/x.txt | comm -13 - /tmp/z.txt | wc -l`
    if [ $ct -ne 0 ]; then
        echo "WARNING: evs_object indexes without evs_metadata entries"
        perl -ne 'chop; @_=split/ /; $_[1]=~ s/[\-\.]//g; print "$_[0] $_[1]\n"' /tmp/x.txt | comm -13 - /tmp/z.txt | sed 's/^/    /'
    fi

else
    sort /tmp/x.$$ | sed 's/^/es|/'
fi

fi

# Cleanup
/bin/rm -f /tmp/db.$$.txt /tmp/[xyz].$$.txt

if [[ $quiet -eq 0 ]]; then
    echo ""
    echo "--------------------------------------------------"
    echo "Finished ...`/bin/date`"
    echo "--------------------------------------------------"
fi
