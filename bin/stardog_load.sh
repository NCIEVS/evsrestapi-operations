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
weekly=0
while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # replace the specified terminology/verison/graph
    --replace) replace=1;;
    # weekly not monthly
    --weekly) weekly=1;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

if [ ${#arr[@]} -ne 1 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--noconfig] [--replace] [--weekly] [--help] <data>"
    echo "  e.g. $0 /local/content/downloads/Thesaurus.owl --weekly"
    echo "  e.g. $0 ../../data/ncit_22.07c/ThesaurusInferred_forTS.owl"
    echo "  e.g. $0 https://evs.nci.nih.gov/ftp1/upload/ThesaurusInferred_forTS.zip"
    echo "  e.g. $0 http://current.geneontology.org/ontology/go.owl"
    echo "  e.g. $0 /local/content/downloads/HGNC_202209.owl"
    echo "  e.g. $0 /local/content/downloads/chebi_213.owl"
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
echo "replace = $replace"
echo "weekly = $weekly"

# Setup configuration
echo "  Setup configuration"
if [[ $config -eq 1 ]]; then
    APP_HOME="${APP_HOME:-/local/content/evsrestapi-operations}"
    CONFIG_DIR=${APP_HOME}/${APP_NAME}/config
    CONFIG_ENV_FILE=${CONFIG_DIR}/setenv.sh
    if [[ -e $CONFIG_ENV_FILE ]]; then
        echo "    config = $CONFIG_ENV_FILE"
        . $CONFIG_ENV_FILE
	else
        echo "ERROR: $CONFIG_ENV_FILE does not exist, consider using --noconfig"
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
    #curl -o ./$datafile.$$.$dataext $data
    curl -v -o ./$datafile.$$.$dataext $data > /tmp/x.$$.log 2>&1
    if [[ $? -ne 0 ]]; then
        cat /tmp/x.$$.log | sed 's/^/    /;'
        echo "ERROR: problem downloading file"
        exit 1
    fi
fi
file=./$datafile.$$.$dataext
echo "    file = $file"

# determine graph/version
echo "  Determine graph and version ...`/bin/date`"
if [[ $datafile =~ "ThesaurusInferred" ]]; then

    terminology=ncit
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
    terminology=go
    version=`grep '<owl:versionInfo>' $file | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//'`
    graph=http://purl.obolibrary.org/obo/go${version}.owl

elif [[ $datafile =~ "HGNC_" ]]; then
    terminology=hgnc
    # version is in the filename
    version=`echo $datafile | perl -pe 's/HGNC_//;'`
    graph=http://ncicb.nci.nih.gov/genenames.org/HGNC${version}.owl

elif [[ $datafile =~ "chebi_" ]]; then
    terminology=chebi
    # version is in the filename
    version=`echo $datafile | perl -pe 's/chebi_//;'`
    graph=http://purl.obolibrary.org/obo/chebi${version}.owl

else
    echo "ERROR: Unsupported file type = $data"
    exit 1
fi

echo "    terminology = $terminology"
echo "    version = $version"
echo "    graph = $graph"

db=NCIT2
if [[ $weekly -eq 1 ]]; then
    db=CTRP
fi

# determine if there's a problem (duplicate graph/version)
ct=`$DIR/list.sh $ncflag --quiet --stardog | perl -pe 's/stardog/    /; s/\|/ /g;' | grep "$db.*$graph" | wc -l`
if [[ $ct -gt 0 ]] && [[ $replace -eq 0 ]]; then
    echo "ERROR: graph is already loaded, use --replace"
    exit 1
fi

# Remove data if $replace is set (remove from both DBs)
if [[ $replace -eq 1 ]]; then
    echo "  Remove graph (replace mode) ...`/bin/date`"
    $STARDOG_HOME/bin/stardog data remove -g $graph CTRP -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem running stardog to remove graph (CTRP)"
        exit 1
    fi
    $STARDOG_HOME/bin/stardog data remove -g $graph NCIT2 -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem running stardog to remove graph (NCIT2)"
        exit 1
    fi
fi

# Load Data

echo "  Load data ($db) ...`/bin/date`"
$STARDOG_HOME/bin/stardog data add $db -g $graph $file -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
if [[ $? -ne 0 ]]; then
    echo "ERROR: Problem loading stardog ($db)"
    exit 1
fi
$STARDOG_HOME/bin/stardog-admin db optimize -n $db -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
if [[ $? -ne 0 ]]; then
    echo "ERROR: Problem optimizing stardog ($db)"
    exit 1
fi

# Cleanup
echo "  Cleanup...`/bin/date`"
/bin/rm ./$datafile.$$.$dataext /tmp/x.$$.log > /dev/null 2>&1

echo ""
echo "--------------------------------------------------"
echo "Finished ...`/bin/date`"
echo "--------------------------------------------------"


