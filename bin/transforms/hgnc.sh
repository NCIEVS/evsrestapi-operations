#!/bin/bash

dir=`pwd | perl -pe 's#/cygdrive/c#C:#;'`
APP_HOME="${2:-$dir/../../}"
CONFIG_DIR="$APP_HOME/config/transforms/hgnc"
LIB_HOME="$APP_HOME/lib"
# We sort on version to determine "latest" programmatically in a consistent way
date=`/bin/date +%Y%m`

cleanup() {
    echo "hgnc.sh:Cleaning up. code:$1"
    local code=$1
    /bin/rm $dir/*hgnc_complete_set.txt > /dev/null 2>&1
    if [ "$code" != "" ]; then
      exit $code
    fi
}


setup(){
  echo "hgnc.sh:Setting up transform script"
  if [[ ! -d $APP_HOME ]]; then
      echo "ERROR: hgnc.sh:APP_HOME is not set"
      exit 1
  fi
}

download_hgnc_file() {
  echo "hgnc.sh:Downloading file from $1"
  curl --fail -v -o hgnc_complete_set.txt $1 > /tmp/x.$$.log 2>&1
  if [[ $? -ne 0 ]]; then
      cat /tmp/x.$$.log | sed 's/^/    /;'
      echo "ERROR: hgnc.sh:problem downloading file"
      cleanup 1
  fi
  mv hgnc_complete_set.txt hgnc_complete_set_$date.txt
}

create_properties_file() {
echo "hgnc.sh:Creating properties file. source:$1"
cat > /tmp/hgnc_to_owl.properties << EOF
source=file\:///$1
target=file\:///$dir/HGNC_$date_tmp.owl
columns=file\:///$CONFIG_DIR/DelimitedColumns.properties
delimiters=file\:///$CONFIG_DIR/Delimiters.properties
specialist=file\:///$CONFIG_DIR/SpecialistDatabase.properties
EOF
}

create_owl_file(){
  echo "hgnc.sh:Creating OWL file"
  java -jar $LIB_HOME/HGNCtoOWL-2.0-jar-with-dependencies.jar /tmp/hgnc_to_owl.properties > /tmp/x.$$.log 2>&1

  if [[ $? -ne 0 ]]; then
      cat /tmp/x.$$.log | sed 's/^/    /;'
      echo "ERROR: hgnc.sh:error converting to OWL file"
      cleanup 1
  fi
}

set_version(){
  echo "hgnc.sh:Adding version to OWL file"
  # Add "owl:versionInfo"
  perl -pe 's/(.*<owl:Ontology.*)\/>/$1>\n      <owl:versionInfo>'$date'<\/owl:versionInfo>\n    <\/owl:Ontology>/' \
  HGNC_$date_tmp.owl > HGNC_$date.owl
  rm HGNC_$date_tmp.owl
}

setup
#download_hgnc_file $1
create_properties_file $1
create_owl_file
set_version
cleanup
echo $dir/HGNC_$date.owl