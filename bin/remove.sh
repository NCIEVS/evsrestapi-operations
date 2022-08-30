#!/bin/sh -f
#
# Used to remove indexes for a particular terminology/version.
#
help=0
config=1
ncflag=""
stardog=1
es=1
while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # show stardog data only
    --stardog) es=0;;
    # show es data only
    --es) stardog=0;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

if [ ${#arr[@]} -ne 2 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--noconfig] [--help] [--stardog] [--es] <terminology> <version>"
    echo "  e.g. $0 ncit 20.09d --stardog"
    echo "  e.g. $0 ncim 202102 --es"
    exit 1
fi

terminology=${arr[0]}
version=${arr[1]}

# Set directory of this script so we can call relative scripts
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "--------------------------------------------------"
echo "Starting ...`/bin/date`"
echo "--------------------------------------------------"
echo "terminology = $terminology"
echo "version = $version"
echo ""

# Setup configuration
echo "  Setup configuration"
if [[ $config -eq 1 ]]; then
    APP_HOME=/local/content/evsrestapi-operations
    CONFIG_DIR=${APP_HOME}/${APP_NAME}/config
    CONFIG_ENV_FILE=${CONFIG_DIR}/setenv.sh
    if [[ -e $CONFIG_ENV_FILE ]]; then
        echo "    config = $CONFIG_ENV_FILE"
        . $CONFIG_ENV_FILE
    else
        echo "ERROR: $CONFIG_ENV_FILE does not exist, consider using --noconfig"
        exit 1
    fi
elif [[ -z $STARDOG_HOST ]]; then
    echo "ERROR: STARDOG_HOST is not set"
    exit 1
elif [[ -z $STARDOG_PORT ]]; then
    echo "ERROR: STARDOG_PORT is not set"
    exit 1
elif [[ -z $STARDOG_USERNAME ]]; then
    echo "ERROR: STARDOG_USERNAME is not set"
    exit 1
elif [[ -z $STARDOG_PASSWORD ]]; then
    echo "ERROR: STARDOG_PASSWORD is not set"
    exit 1
elif [[ -z $ES_SCHEME ]]; then
    echo "ERROR: ES_SCHEME is not set"
    exit 1
elif [[ -z $ES_HOST ]]; then
    echo "ERROR: ES_HOST is not set"
    exit 1
elif [[ -z $ES_PORT ]]; then
    echo "ERROR: ES_PORT is not set"
    exit 1
fi

echo "    stardog = http://${STARDOG_HOST}:${STARDOG_PORT}"
echo "    elasticsearch = ${ES_SCHEME}://${ES_HOST}:${ES_PORT}"
echo ""

echo "  Lookup stardog info ...`/bin/date`"

if [[ $stardog -eq 1 ]]; then

    $DIR/list.sh $ncflag --quiet --stardog | perl -pe 's/stardog/    /;' | grep "$terminology\|$version" > /tmp/x.$$
	ct=`cat /tmp/x.$$ | wc -l`
	if [[ $ct -eq 1 ]]; then

        db=`cat /tmp/x.$$ | cut -d\| -f 2`
        graph=`cat /tmp/x.$$ | cut -d\| -f 5`
        echo "  Remove $db graph $graph ...`/bin/date`"
        $STARDOG_HOME/stardog data remove -g $graph $db -u $STARDOG_USER -p $STARDOG_PASSWORD | sed 's/^/    /'
        if [[ $? -ne 0 ]]; then
            echo "ERROR: Problem running stardog to remove graph ($db)"
            exit 1
        fi
    else
        cat /tmp/x.$$ | sed 's/^/    /'
        echo "ERROR: unexpected number of matching graphs = $ct"
    fi

fi

if [[ $es -eq 1 ]]; then

    # Strip dot and dash chars from version
    version=`echo $version | perl -pe 's/[\.\-]//g;'`

    echo "  Remove indexes for $terminology $version"
    curl -s $ES_SCHEME://$ES_HOST:$ES_PORT/_cat/indices | perl -pe 's/^.* open ([^ ]+).*/$1/; s/\r//;' | grep $version | grep ${terminology}_ | cat > /tmp/x.$$
    if [[ $? -ne 0 ]]; then
        echo "ERROR: unexpected error looking up indices for $terminology $version"
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

    echo "  Remove ${terminology}_$version from evs_metadata"
    curl -s -X DELETE $ES_SCHEME://$ES_HOST:$ES_PORT/evs_metadata/_doc/concept_${terminology}_$version > /tmp/x.$$
    if [[ $? -ne 0 ]]; then
        cat /tmp/x.$$ | sed 's/^/    /'
        echo "ERROR: unexpected error removing concept_${terminology}_$version from evs_metadata index"
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
