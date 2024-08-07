#!/bin/bash -f
#
# This script takes a reference to a terminology metadata .json file
# and overrides the evs_metadata entry for the specified terminology/version.
#
config=1
ncflag=""
help=0
while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

# Set directory of this script so we can call relative scripts
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ ${#arr[@]} -ne 3 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--noconfig] [--help] <terminology> <version> <config>"
    echo "  e.g. $0 ncit 2106e ../path/to/ncit.json"
    echo "  e.g. $0 ncit 2106e https://example.com/path/to/ncit.json"
    echo "  e.g. $0 ncim 202102 ../path/to/ncim.json"

    # List versions and bail
    echo ""
    echo "List of stardog terminology versions:"
    $DIR/list.sh $ncflag --quiet --es | perl -pe 's/stardog/    /; s/\|/ /g;'
    exit 1
fi

terminology=${arr[0]}
version=${arr[1]}
indexVersion=`echo $version | perl -ne 's/[\.\-]//g; print lc($_)'`
uri=${arr[2]}

# Verify jq installed
jq --help >> /dev/null 2>&1
if [[ $? -eq 0 ]]; then
    jq="jq ."
else
    jq="python -m json.tool"
fi

echo "--------------------------------------------------"
echo "Starting ...`/bin/date`"
echo "--------------------------------------------------"
echo "terminology = $terminology"
echo "version = $version"
echo "indexVersion = $indexVersion"
echo "uri = $uri"


# Setup configuration
echo "  Setup configuration"
if [[ $config -eq 1 ]]; then
    APP_HOME="${APP_HOME:-/local/content/evsrestapi}"
    CONFIG_DIR=${APP_HOME}/config
    CONFIG_ENV_FILE=${CONFIG_DIR}/setenv.sh
    echo "    config = $CONFIG_ENV_FILE"
    . $CONFIG_ENV_FILE
    if [[ $? -ne 0 ]]; then
        echo "ERROR: $CONFIG_ENV_FILE does not exist or has a problem"
        echo "       consider using --noconfig (if working in dev environment)"
        exit 1
    fi
elif [[ -z $ES_SCHEME ]]; then
    echo "ERROR: ES_SCHEME is not set"
    exit 1
elif [[ -z $ES_HOST ]]; then
    echo "ERROR: ES_HOST is not set"
    exit 1
elif [[ -z $ES_PORT ]]; then
    echo "ERROR: ES_PORT is not set"
    exit 1
else
    ES=${ES_SCHEME}://${ES_HOST}:${ES_PORT}
fi

echo "    elasticsearch = $ES"
echo ""

# Verify that terminology/version is valid
echo "  Verify $terminology $indexVersion exists"
curl -s $ES/evs_metadata/_doc/concept_${terminology}_${indexVersion} > /tmp/x.$$ 2>&1
if [[ $? -ne 0 ]]; then
    echo "ERROR: unexpected error looking up index in elasticsearch, check config"
    exit 1
fi

ct=`grep '"found":false' /tmp/x.$$ | wc -l`
if [ $ct -ne 0 ]; then
   echo "ERROR: $terminology $indexVersion not found in evs_metadata index"
   exit 1
fi

echo "  Verify '$uri' exists"
ct=`echo $uri | grep -c 'http'`
# handle the uri case
if [ $ct -ne 0 ]; then
    curl -s -o /tmp/y.$$ $uri > /tmp/x.$$ 2>&1
    if [ $? -ne 0 ]; then
        cat /tmp/x.$$
        echo "ERROR: Problem downloading $uri"
        exit 1
    fi
    file=/tmp/y.$$
else
    file=$uri
fi

# At this point $file is set to a file that exists
echo "  Verfiy $file is valid json"
cat $file | $jq > /tmp/x.$$ 2>&1
if [ $? -ne 0 ]; then
   echo "ERROR: Unable to parse $file as json"
   exit 1
fi

# All checks passed, proceed with updating
data=`cat $file`
curl -X POST "$ES/evs_metadata/_doc/concept_${terminology}_${indexVersion}/_update" \
  -H 'Content-type: application/json' \
  -d '{"doc": {"terminology": {"metadata": '"$data"'}}}' > /tmp/x.$$ 2>&1
if [ $? -ne 0 ]; then
   echo "ERROR: Problem posting update payload for $terminology $indexVersion"
   exit 1
fi

# Cleanup
/bin/rm -f /tmp/[xy].$$.txt

echo ""
echo "--------------------------------------------------"
echo "Finished ...`/bin/date`"
echo "--------------------------------------------------"
