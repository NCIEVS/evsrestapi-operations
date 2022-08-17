#!/bin/bash -f
#
# This script takes a parameter locating a data file.
# If the data file is a remote file, it downloads that file
# to a local file.  The data is then loaded into stardog
# and this script takes responsibility for determining the
# "graph" and "version" needed for performing that load.
#
replace=0
config=1
help=0
while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # replace the specified terminology/verison/graph
    --replace) replace=1;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

if [ ${#arr[@]} -ne 1 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--noconfig] [--replace] [--help] <data>"
    echo "  e.g. $0 /local/content/downloads/Thesaurus.owl"
    echo "  e.g. $0 ../../data/ncit_22.07c/ThesaurusInferred_forTS.owl"
    echo "  e.g. $0 https://evs.nci.nih.gov/ftp1/upload/ThesaurusInferred_forTS.zip"
    echo "  e.g. $0 http://current.geneontology.org/ontology/go.owl"
    exit 1
fi

data=${arr[0]}

# Verify jq installed
jq --help >> /dev/null 2>&1
if [[ $? -eq 0 ]]; then
    jq="jq ."
else
    jq="python -m json.tool"
fi

# Set directory of this script so we can call relative scripts
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "--------------------------------------------------"
echo "Starting ...`/bin/date`"
echo "--------------------------------------------------"
echo "data = $data"
echo "config = $config"
echo "replace = $replace"

# Setup configuration
echo "  Setup configuration"
if [[ $config -eq 1 ]]; then
    APP_HOME=/local/content/evsrestapi-operations
    CONFIG_DIR=${APP_HOME}/${APP_NAME}/config
    CONFIG_ENV_FILE=${CONFIG_DIR}/setenv.sh
    echo "    config = $CONFIG_ENV_FILE"
    . $CONFIG_ENV_FILE
    if [[ $? -ne 0 ]]; then
        echo "ERROR: $CONFIG_ENV_FILE does not exist or has a problem"
        echo "       consider using --noconfig (if working in dev environment)"
        exit 1
    fi
elif [[ -z $STARDOG_HOME ]]; then
    echo "ERROR: STARDOG_HOME is not set"
    exit 1
elif [[ -z $STARDOG_USERNAME ]]; then
    echo "ERROR: STARDOG_USERNAME is not set"
    exit 1
elif [[ -z $STARDOG_PASSWORD ]]; then
    echo "ERROR: STARDOG_PASWORD is not set"
    exit 1
fi

echo "STARDOG_HOME = $STARDOG_HOME"
echo ""


echo "  Put data in standard location - /tmp ...`/bin/date`"
dataext=`echo $data | perl -pe 's/.*\.//;'`
if [[ "x$dataext" == "" ]]; then
    echo "ERROR: unable to find file extension = $data"
    exit 1
fi
datafile=`echo $data |  perl -pe 's/^.*\///; s/([^\.]+)\..{3,5}$/$1/;'`

# If the file exists, copy it to /tmp preserving the extension
if [[ -e $data ]]; then
    cp  $data ./$datafile.$$.$dataext

# Otherwise, download it
else
    echo "    download = $data"
    curl -o ./$datafile.$$.$dataext $data
    # curl -v -o ./$datafile.$$.$dataext $data
    # > /tmp/x.$$.log 2>&1
    if [[ $? -ne 1 ]]; then
        #cat /tmp/x.$$.log | sed 's/^/    /;'
        echo "ERROR: problem downloading file"
        exit 1
    fi
fi
file=./$datafile.$$.$dataext
echo "    file = $file"

# determine graph/version
echo "  Determine graph and version ...`/bin/date`"
if [[ $datafile =~ "ThesaurusInferred" ]]; then

    if [[ $dataext == "zip" ]]; then
        version=`unzip -p $file "*ThesaurusInferred_forTS.owl" | grep '<owl:versionInfo>' | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//'`

    elif [[ $dataext == "owl" ]]; then
        version=`grep '<owl:versionInfo>' $file | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//'`

    else
        echo "ERROR: unable to handle extension - $data"
        exit 1
    fi

    graph=http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus$version.owl

elif [[ $datafile == "go" ]]; then
    version=`grep '<owl:versionInfo>' $file | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//'`
    graph=http://purl.obolibrary.org/obo/go${version}.owl

else
echo "3"
    echo "ERROR: Unsupported file type = $data"
    exit 1
fi

echo "    version = $version"
echo "    graph = $graph"

# determine what's loaded in stardog already
echo "xxx"
$DIR/list.sh $ncflag --quiet --stardog | perl -pe 's/stardog/    /; s/\|/ /g;' | grep $version
echo "xxx2"


# determine if there's a problem (duplicate graph/version)


exit 0

# Remove data if $replace is set
if [[ $replace -eq 1 ]]; then
    echo "  Remove graph (replace mode) ...`/bin/date`"
    $STARDOG_HOME/stardog data remove -g $graph CTRP -u $STARDOG_USER -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem running stardog to remove graph (CTRP)"
        exit 1
    fi
    $STARDOG_HOME/stardog data remove -g $graph NCIT2 -u $STARDOG_USER -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem running stardog to remove graph (NCIT2)"
        exit 1
    fi
fi

# Load Data
echo "  Load data ...`/bin/date`"
$STARDOG_HOME/stardog data add CTRP -g $graph $file -u $STARDOG_USER -p $STARDOG_PASSWORD | sed 's/^/    /'
if [[ $? -ne 0 ]]; then
    echo "ERROR: Problem loading stardog (CTRP)"
    exit 1
fi

$STARDOG_HOME/stardog data add NCIT2 -g $graph $file -u $STARDOG_USER -p $STARDOG_PASSWORD | sed 's/^/    /'
if [[ $? -ne 0 ]]; then
    echo "ERROR: Problem loading stardog (NCIT2)"
    exit 1
fi

# Cleanup
echo "  Cleanup...`/bin/date`"
/bin/rm ./$datafile.$$.$dataext /tmp/x.$$.log > /dev/null 2>&1

echo ""
echo "--------------------------------------------------"
echo "Finished ...`/bin/date`"
echo "--------------------------------------------------"


