#!/bin/bash -f
#
# Used to remove indexes for a particular terminology/version.
#
help=0
config=1
ncflag=""
graphdb=0
es=0

l_graph_db_type=${GRAPH_DB_TYPE:-"stardog"}
l_graph_db_host=${GRAPH_DB_HOST:-"localhost"}
l_graph_db_port=${GRAPH_DB_PORT:-"5820"}
l_graph_db_home=""
l_graph_db_username=""
l_graph_db_password=""
l_graph_db_url=""

while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # remove graphdb data
    --graphdb) graphdb=1;;
    --stardog) graphdb=1;;
    --jena) graphdb=1;;
    # remove es data
    --es) es=1;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

if [ ${#arr[@]} -ne 2 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--noconfig] [--help] [--graphdb] [--es] <terminology> <version>"
    echo "  e.g. $0 ncit 20.09d --graphdb"
    echo "  e.g. $0 ncim 202102 --es"
    exit 1
fi

terminology=${arr[0]}
version=${arr[1]}
# Strip dot and dash chars from version
indexVersion=`echo $version | perl -ne 's/[\.\-]//g; print lc($_)'`


# Set directory of this script so we can call relative scripts
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "--------------------------------------------------"
echo "Starting ...`/bin/date`"
echo "--------------------------------------------------"
echo "terminology = $terminology"
echo "version = $version"
echo "indexVersion = $indexVersion"
echo ""

# Setup configuration
echo "  Setup configuration"
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

validate_configuration() {
  if [[ -z $ES_SCHEME ]]; then
    echo "ERROR: ES_SCHEME is not set"
    exit 1
  elif [[ -z $ES_HOST ]]; then
    echo "ERROR: ES_HOST is not set"
    exit 1
  elif [[ -z $ES_PORT ]]; then
    echo "ERROR: ES_PORT is not set"
    exit 1
  fi
}

validate_setup() {
  if [[ $graphdb -eq 1 ]]; then
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
      if [[ -z $GRAPH_DB_URL ]]; then
        echo "    ERROR: GRAPH_DB_URL is not set"
        exit 1
      else
        l_graph_db_url="$GRAPH_DB_URL"
      fi
    else
      echo "Error: GRAPH_DB_TYPE is not set."
      exit 1
    fi
  fi
}

validate_arguments() {
# Require specifying --es or --graphdb so you don't accidentally delete from both
if [[ $graphdb -eq 0 ]] && [[ $es -eq 0 ]]; then
    echo "Must specify --es and/or --graphdb"
    exit 1
fi
}

setup_configuration
validate_configuration
validate_setup
validate_arguments

ES=${ES_SCHEME}://${ES_HOST}:${ES_PORT}

echo "    graphdb type = ${l_graph_db_type}"
echo "    elasticsearch = ${ES}"
echo ""

if [[ $graphdb -eq 1 ]]; then

    echo "  Lookup graphdb info ...`/bin/date`"
    $DIR/list.sh $ncflag --quiet --graphdb | perl -pe 's/$l_graph_db_type/    /;' | grep "$terminology|$version" > /tmp/x.$$
	ct=`cat /tmp/x.$$ | wc -l`
	if [[ $ct -eq 1 ]] || [[ $ct -eq 2 ]]; then
        for line in `cat /tmp/x.$$`; do
            db=`echo $line | cut -d\| -f 2`
            graph=`echo $line | cut -d\| -f 5`
            echo "  Remove $db graph $graph ...`/bin/date`"
            if [[ $l_graph_db_type == "stardog" ]]; then
              echo "    $l_graph_db_home/bin/stardog data remove -g $graph $db -u $l_graph_db_username -p ****"
              $l_graph_db_home/bin/stardog data remove -g $graph $db -u $l_graph_db_username -p $l_graph_db_password | sed 's/^/    /'
            elif [[ $l_graph_db_type == "jena" ]]; then
              echo "    curl -s -f $l_graph_db_url/$db/update -d\"update=DROP GRAPH <$graph>\" > /dev/null"
              curl -s -f "$l_graph_db_url/$db/update" -d"update=DROP GRAPH <$graph>" > /dev/null
            fi
            if [[ $? -ne 0 ]]; then
                echo "ERROR: Problem removing graph ($db)"
                exit 1
            fi
        done
    else
        cat /tmp/x.$$ | sed 's/^/    /'
        echo "ERROR: unexpected number of matching graphs = $ct"
    fi

fi

if [[ $es -eq 1 ]]; then

    echo "  Remove indexes for $terminology $indexVersion"
    curl -s $ES_SCHEME://$ES_HOST:$ES_PORT/_cat/indices | perl -pe 's/^.* open ([^ ]+).*/$1/; s/\r//;' | grep $indexVersion | grep ${terminology}_ | cat > /tmp/x.$$
    if [[ $? -ne 0 ]]; then
        echo "ERROR: unexpected error looking up indices for $terminology $indexVersion"
        exit 1
    fi

    ct=`cat /tmp/x.$$ | wc -l`
    if [[ $ct -eq 0 ]]; then
        echo "    NO indexes to delete"
    fi
    for i in `cat /tmp/x.$$`; do
        echo "    delete $i"
        curl -s -X DELETE $ES_SCHEME://$ES_HOST:$ES_PORT/$i > /tmp/x.$$
        if [[ $? -ne 0 ]]; then
            cat /tmp/x.$$ | sed 's/^/    /'
            echo "ERROR: unexpected error removing index $i"
            exit 1
        fi
    done

    echo "  Remove ${terminology}_$indexVersion from evs_metadata"
    curl -s -X DELETE $ES_SCHEME://$ES_HOST:$ES_PORT/evs_metadata/_doc/concept_${terminology}_$indexVersion > /tmp/x.$$
    if [[ $? -ne 0 ]]; then
        cat /tmp/x.$$ | sed 's/^/    /'
        echo "ERROR: unexpected error removing concept_${terminology}_$indexVersion from evs_metadata index"
        exit 1
    fi
    ct=`grep 'not_found' /tmp/x.$$ | wc -l`
    if [[ $ct -ne 0 ]]; then
        echo "    NO matching evs_metadata entry"
    fi

fi

# cleanup
/bin/rm -f /tmp/x.$$

echo ""
echo "--------------------------------------------------"
echo "Finished ...`/bin/date`"
echo "--------------------------------------------------"
