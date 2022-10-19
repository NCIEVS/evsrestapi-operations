#!/bin/bash -f
#
# This script lists databases, terminologies, versions, graphs
# available in the configured stardog and elasticsearch.
# The --noconfig flag is for running in the dev environment
# where the setenv.sh file does not exist.
#
config=1
ncflag=""
help=0
quiet=0
stardog=1
es=1
while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    # use environment variable config (dev env)
    --noconfig) config=0; ncflag="--noconfig";;
    # avoid printing header/footer
    --quiet) quiet=1;;
    # show stardog data only
    --stardog) es=0;;
    # show es data only
    --es) stardog=0;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

if [ ${#arr[@]} -ne 0 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--noconfig] [--quiet] [--stardog] [--es] [--help]"
    echo "  e.g. $0 --noconfig"
    echo "  e.g. $0 --noconfig --stardog"
    echo "  e.g. $0 --noconfig --quiet --stardog"
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
else
    ES=${ES_SCHEME}://${ES_HOST}:${ES_PORT}
fi

if [[ $quiet -eq 0 ]]; then
    echo "    stardog = http://${STARDOG_HOST}:${STARDOG_PORT}"
    echo "    elasticsearch = ${ES}"
    echo ""
fi

if [[ $quiet -eq 0 ]]; then
    echo "  Lookup stardog info ...`/bin/date`"
fi

if [[ $stardog -eq 1 ]]; then

curl -s -g -u "${STARDOG_USERNAME}:$STARDOG_PASSWORD" \
    "http://${STARDOG_HOST}:${STARDOG_PORT}/admin/databases" |\
    $jq | perl -ne 's/\r//; $x=0 if /\]/; if ($x) { s/.* "//; s/",?$//; print "$_"; }; 
                    $x=1 if/\[/;' > /tmp/db.$$.txt
if [[ $? -ne 0 ]]; then
    echo "ERROR: unexpected problem listing databases"
    exit 1
fi

if [[ $quiet -eq 0 ]]; then
    echo "    databases = " `cat /tmp/db.$$.txt`
fi
ct=`cat /tmp/db.$$.txt | wc -l`
if [[ $ct -eq 0 ]]; then
    echo "ERROR: no stardog databases, this is unexpected"
    exit 1
fi


# Prep query to read all version info
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
      ?source owl:versionInfo ?version
    }
    UNION
    {
      ?source a owl:Ontology .
      ?source owl:versionIRI ?version .
      FILTER NOT EXISTS { ?source owl:versionInfo ?versionInfo }
    }
  }
}
EOF
query=`cat /tmp/x.$$.txt`

# Run the query against each of the databases
/bin/rm -f /tmp/y.$$.txt
touch /tmp/y.$$.txt
for db in `cat /tmp/db.$$.txt`; do
    curl -s -g -u "${STARDOG_USERNAME}:$STARDOG_PASSWORD" \
        http://${STARDOG_HOST}:${STARDOG_PORT}/$db/query \
        --data-urlencode "$query" -H "Accept: application/sparql-results+json" |\
        $jq | perl -ne '
            chop; $x="version" if /"version"/;
            $x="source" if /"source"/;
            $x="graphName" if /"graphName"/; 
            $x=0 if /\}/; 
            if ($x && /"value"/) { 
                s/.* "//; s/".*//;
                ${$x} = $_;                
                print "$version|'$db'|$source|$graphName\n" if $x eq "version"; 
            } ' >> /tmp/y.$$.txt
    if [[ $? -ne 0 ]]; then
        echo "ERROR: unexpected problem obtaining $db versions from stardog"
        exit 1
    fi    
done

# Sort by version then reverse by DB (NCIT2 goes before CTRP)
# this is because we need "monthly" to be indexed from the "monthlyDb"
# defined in ncit.json
/bin/sort -t\| -k 1,1 -k 2,2r -o /tmp/y.$$.txt /tmp/y.$$.txt

if [[ $quiet -eq 0 ]]; then
    echo "  List stardog graphs ...`/bin/date`"
fi
# Here determine the parts for each case
for x in `cat /tmp/y.$$.txt`; do
    version=`echo $x | cut -d\| -f 1 | perl -pe 's#.*/(\d+)/[a-zA-Z]+.owl#$1#;'`
    db=`echo $x | cut -d\| -f 2`
    uri=`echo $x | cut -d\| -f 3`
    graph_uri=`echo $x | cut -d\| -f 4`
    term=`echo $uri | perl -pe 's/.*Thesaurus.owl/ncit/; s/.*obo\/go.owl/go/; s/.*\/HGNC.owl/hgnc/; s/.*\/chebi.owl/chebi/'`
    if [[ $quiet -eq 1 ]]; then
        echo "stardog|$db|$term|$version|$graph_uri"
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
   $jq | grep terminologyVersion | perl -pe 's/_/ /; s/.*"\: ?"//; s/".*//' |\
   sort | sed 's/^/    /'
else
curl -s "$ES/evs_metadata/_search?size=10000"  |\
   $jq | grep terminologyVersion | perl -pe 's/_/|/; s/.*"\: ?"//; s/".*//' |\
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
