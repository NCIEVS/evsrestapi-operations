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

get_ignored_sources(){
  if [ -f "../config/metadata/ignore-source.txt" ]; then
    echo $(cat "../config/metadata/ignore-source.txt" | awk -vORS=">,<" '{ print $1 }' | sed 's/,<$//' | sed 's/^/</')
  else
    echo ""
  fi
}
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
sort -t\| -k 1,1 -k 2,2r -o /tmp/y.$$.txt /tmp/y.$$.txt

if [[ $quiet -eq 0 ]]; then
    echo "  List stardog graphs ...`/bin/date`"
fi
# Here determine the parts for each case
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

for x in `cat /tmp/y.$$.txt`; do
    version=`echo $x | cut -d\| -f 1 | perl -pe 's#.*/(.*)/[a-zA-Z]+.owl#$1#;'`
    db=`echo $x | cut -d\| -f 2`
    uri=`echo $x | cut -d\| -f 3`
    graph_uri=`echo $x | cut -d\| -f 4`
    term=$(get_terminology "$uri")
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

curl -s "$ES/evs_metadata/_search?size=10000"  |\
   $jq | grep terminologyVersion | perl -pe 's/(?<!snomedct)_/ /; s/.*"\: ?"//; s/".*//' |\
   sort -u -o /tmp/x.txt

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
sort /tmp/x.txt| sed 's/^/es|/'
fi
if [[ $? -ne 0 ]]; then
    echo "ERROR: problem looking up indexes"
    exit 1
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
