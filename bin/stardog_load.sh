#!/bin/bash -f
#
# This script takes a parameter locating a data file.
# If the data file is a remote file, it downloads that file
# to a local file.  The data is then loaded into stardog
# and this script takes responsibility for determining the
# "graph" and "version" needed for performing that load.
#
force=0
config=1
help=0
weekly=0
while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # ignore errors AND replace the specified terminology/verison/graph
    --force) force=1;;
    # weekly not monthly
    --weekly) weekly=1;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

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
echo "DIR = $DIR"
echo "data = $data"
echo "force = $force"
echo "weekly = $weekly"

# Setup configuration
echo "  Setup configuration"
if [[ $config -eq 1 ]]; then
    APP_HOME="${APP_HOME:-/local/content/evsrestapi}"
    CONFIG_DIR=${APP_HOME}/config
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

echo "    STARDOG_HOME = $STARDOG_HOME"
echo ""

# cleanup log files
cleanup() {
    local code=$1
    /bin/rm $DIR/f$$.$datafile.$dataext /tmp/x.$$.log > /dev/null 2>&1
    if [ "$code" != "" ]; then
      exit $code
    fi
}

remove_graph() {
    echo "    Removing graph: $1. Db: $2"
    $STARDOG_HOME/bin/stardog data remove -g $1 $2 -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem running stardog to remove graph $1($2)"
        cleanup 1
    fi
}

get_file_extension() {
    local extension=`echo $1 | perl -pe 's/.*\.//;'`
    if [[ "x$extension" == "" ]]; then
        echo "ERROR: unable to find file extension = $1"
        exit 1
    fi
    echo "$extension"
}

get_file_name() {
  echo $1 |  perl -pe 's/^.*\///; s/([^\.]+)\..{2,5}$/$1/;'
}

set_transformed_owl(){
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

set_load_variables_of_transform(){
  echo "Setting up variables for the Stardog load. transformed owl file: $transformed_owl"
  if [[ ! -s $transformed_owl ]]; then
        echo "ERROR: Generated owl file is empty"
	      cleanup 1
	fi
  # look up file ext again
  dataext=$(get_file_extension "$transformed_owl")
  datafile=$(get_file_name "$transformed_owl")
  mv "$transformed_owl" "$DIR"/f$$."$datafile"."$dataext"
  file=$DIR/f$$.$datafile.$dataext
  echo "    file = $file"
}

echo "  Put data in standard location - /tmp ...`/bin/date`"
dataext=`echo $data | perl -pe 's/.*\.//;'`
if [[ "x$dataext" == "" ]]; then
    echo "ERROR: unable to find file extension = $data"
    exit 1
fi
datafile=`echo $data |  perl -pe 's/^.*\///; s/([^\.]+)\..{2,5}$/$1/;'`

# If the file exists, copy it to /tmp preserving the extension
if [[ -e $data ]]; then
    cp $data $DIR/f$$.$datafile.$dataext

# Otherwise, download it
elif [[ $data = http* ]] || [[ $data = ftp* ]]; then
    echo "    download = $data"
    curl --fail -v -o $DIR/f$$.$datafile.$dataext $data > /tmp/x.$$.log 2>&1
    if [[ $? -ne 0 ]]; then
        cat /tmp/x.$$.log | sed 's/^/    /;'
        echo "ERROR: problem downloading file"
        cleanup 1
    fi

else
    echo "ERROR: $data is not local or http/ftp"
    cleanup 1
fi

file=$DIR/f$$.$datafile.$dataext
echo "    file = $file"

if [[ $dataext == "gz" ]]; then
    echo "    unpack gz file"
    gunzip $DIR/f$$.$datafile.$dataext
    if [[ $? -ne 0 ]]; then
        echo "ERROR: failed to gunzip file"
	cleanup 1
    fi
    
    # look up file ext again
    dataext=`echo $datafile | perl -pe 's/.*\.//;'`
    if [[ "x$dataext" == "" ]]; then
        echo "ERROR: unable to find file extension = $datafile"
        exit 1
    fi
    datafile=`echo $datafile |  perl -pe 's/^.*\///; s/([^\.]+)\..{2,5}$/$1/;'`
    file=$DIR/f$$.$datafile.$dataext
    echo "    file = $file"
fi

# If dataext is not owl. Look for transformations to apply
if [[ $dataext != "owl" ]] && [[ $dataext != "zip" ]]; then
  echo "Unknown extension. Looking for transformations"
  if [[ $datafile =~ "hgnc_" ]]; then
    echo "Applying transformations for HGNC"
    if [[ -z $APP_HOME ]]; then
      echo "ERROR: HGNC transformation needs APP_HOME to be set"
      exit 1
    fi
    script_output=$($DIR/transforms/hgnc.sh $file $APP_HOME)
    set_transformed_owl "hgnc" "$script_output"
    set_load_variables_of_transform
  fi
fi

# Verify that owl file is an owl file
if [[ $dataext == "owl" ]] && [[ `head -100 $file | grep -c owl:Ontology` -eq 0 ]]; then
    echo "ERROR: no owl:Ontology declaration in first 100 lines"
    cleanup 1
fi

# determine graph/version
echo "  Determine graph and version ...`/bin/date`"
if [[ $datafile =~ "ThesaurusInf" ]]; then

    terminology=ncit
    if [[ $dataext == "zip" ]]; then
        version=`unzip -p $file "*ThesaurusInferred_forTS.owl" | grep '<owl:versionInfo>' | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//'`

    elif [[ $dataext == "owl" ]]; then
        version=`grep '<owl:versionInfo>' $file | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//'`

    else
        echo "ERROR: unable to handle extension - $data"
        cleanup 1
    fi
    $STARDOG_HOME/bin/stardog data remove -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl CTRP -u $STARDOG_USERNAME -p $STARDOG_PASSWORD
    $STARDOG_HOME/bin/stardog data remove -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl NCIT2 -u $STARDOG_USERNAME -p $STARDOG_PASSWORD
    graph=http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus$version.owl

elif [[ $datafile == "go" ]]; then
    terminology=go
    version=`head -100 $file | grep '<owl:versionInfo>' | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//'`
    graph=http://purl.obolibrary.org/obo/go${version}.owl

elif [[ $datafile =~ "HGNC_" ]]; then
    terminology=hgnc
    # version is in the filename
    version=`echo $datafile | perl -pe 's/HGNC_//;'`
    graph=http://ncicb.nci.nih.gov/genenames.org/HGNC${version}.owl

elif [[ $datafile == "chebi" ]]; then
    terminology=chebi
    version=`head -100 $file | grep 'owl:versionIRI' | perl -pe 's/.*\/(\d+)\/chebi.*/$1/'`
    # This is from "owl:versionIRI"
    graph=http://purl.obolibrary.org/obo/chebi/${version}/chebi.owl

elif [[ $datafile == "umlssemnet" ]]; then
    terminology=umlssemnet
    if [[ $dataext == "zip" ]]; then
      echo "Applying transformations for UMLS Semnatic Network"
      script_output=$($DIR/transforms/umlssemnet.sh $file)
      # Done with zip file. Cleanup
      /bin/rm $DIR/f$$.$datafile.zip
      set_transformed_owl "umlssemnet" "$script_output"
      set_load_variables_of_transform
      version=`grep '<owl:versionInfo>' $file | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//'`
      graph=http://www.nlm.nih.gov/research/umls/UmlsSemNet/${version}/umlssemnet.owl
    else
        echo "ERROR: unable to handle extension - $data"
        cleanup 1
    fi

else
    echo "ERROR: Unsupported file type = $datafile"
    cleanup 1
fi

echo "    terminology = $terminology"
echo "    version = $version"
echo "    graph = $graph"

db=NCIT2
if [[ $weekly -eq 1 ]]; then
    if [[ $terminology != "ncit" ]]; then
        echo "ERROR: --weekly only makes sense when loading NCI Thesaurus"
        cleanup 1
    fi
    db=CTRP
fi

# Run QA on $file
if [[ $force -eq 1 ]]; then
    echo "  SKIP QA on $file ...`/bin/date`"
else
    echo "  Run QA on $file ...`/bin/date`"
    $DIR/stardog_qa.sh $terminology $file > /tmp/x.$$.log  2>&1
    if [[ $? -ne 0 ]]; then 
	cat /tmp/x.$$.log | sed 's/^/    /;'
        echo "ERROR: QA errors, re-run with --force to bypass this"
        cleanup 1
    fi
fi

# determine if there's a problem (duplicate graph/version)
ct=`$DIR/list.sh $ncflag --quiet --stardog | perl -pe 's/stardog/    /; s/\|/ /g;' | grep "$db.*$graph" | wc -l`
if [[ $? -ne 0 ]]; then
    echo "ERROR: problem running list.sh"
    cleanup 1
fi

if [[ $ct -gt 0 ]] && [[ $force -eq 0 ]]; then
    echo "ERROR: graph is already loaded, use --force"
    cleanup 1
fi

# Remove data if $force is set (remove from both DBs)
if [[ $force -eq 1 ]]; then
    echo "  Remove graph (force mode) ...`/bin/date`"
    $STARDOG_HOME/bin/stardog data remove -g $graph CTRP -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem running stardog to remove graph (CTRP)"
        cleanup 1
    fi
    $STARDOG_HOME/bin/stardog data remove -g $graph NCIT2 -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem running stardog to remove graph (NCIT2)"
        cleanup 1
    fi
fi

# Load Data

echo "  Load data ($db) ...`/bin/date`"
$STARDOG_HOME/bin/stardog data add $db -g $graph $file -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
if [[ $? -ne 0 ]]; then
    echo "ERROR: Problem loading stardog ($db)"
    cleanup 1
fi
echo "  Optimize database ($db) ...`/bin/date`"
$STARDOG_HOME/bin/stardog-admin db optimize -n $db -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
if [[ $? -ne 0 ]]; then
    echo "ERROR: Problem optimizing stardog ($db)"
    cleanup 1
fi

# For monthly ncit, also load into CTRP db
if [[ $terminology == "ncit" ]] && [[ $weekly -eq 0 ]]; then
    db=CTRP
    echo "  Load data ($db) ...`/bin/date`"
    $STARDOG_HOME/bin/stardog data add $db -g $graph $file -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem loading stardog ($db)"
        cleanup 1
    fi
    echo "  Optimize database ($db) ...`/bin/date`"
    $STARDOG_HOME/bin/stardog-admin db optimize -n $db -u $STARDOG_USERNAME -p $STARDOG_PASSWORD | sed 's/^/    /'
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Problem optimizing stardog ($db)"
        cleanup 1
    fi
fi

# Remove older versions here
maxVersions=1
if [[ `grep -c maxVersions $DIR/../config/metadata/$terminology.json` -gt 0 ]]; then
    maxVersions=`grep maxVersions $DIR/../config/metadata/$terminology.json | perl -pe 's/.*\:\s*(\d+),.*/$1/;'`
fi
echo "  Remove old monthly version (maxVersions=$maxVersions) ...`/bin/date`"
monthly_graphs=`$DIR/list.sh $ncflag --quiet --stardog | grep -w $terminology | grep -w NCIT2 | awk -F\| '{print $5}'`
monthly_graphs_array=(${monthly_graphs})
for graph_to_remove in "${monthly_graphs_array[@]:0:${#monthly_graphs_array[@]}-maxVersions}"
do
  remove_graph "$graph_to_remove" "NCIT2"
done

echo "  Remove old weekly versions (will keep only 1)...`/bin/date`"
weekly_graphs=`$DIR/list.sh $ncflag --quiet --stardog | grep -w $terminology | grep -w CTRP | awk -F\| '{print $5}'`
weekly_graphs_array=(${weekly_graphs})
for graph_to_remove in "${weekly_graphs_array[@]:0:${#weekly_graphs_array[@]}-1}"
do
  remove_graph "$graph_to_remove" "CTRP"
done

# Cleanup
echo "  Cleanup...`/bin/date`"
cleanup

echo ""
echo "--------------------------------------------------"
echo "Finished ...`/bin/date`"
echo "--------------------------------------------------"