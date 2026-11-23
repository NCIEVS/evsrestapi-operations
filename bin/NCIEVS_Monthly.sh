USER=****
PASSWORD=****

# This script invokes an external Stardog installation. Select a JDK supported by that
# installation; do not override it with the EVS applications' Java 25 requirement.
: "${STARDOG_JAVA_HOME:=${JAVA_HOME:?Set STARDOG_JAVA_HOME or JAVA_HOME for this Stardog installation}}"
export JAVA_HOME="$STARDOG_JAVA_HOME"

./stardog data remove --all  NCIEVS -u $USER -p $PASSWORD
./stardog data remove --all  CTRP   -u $USER -p $PASSWORD
./stardog data add NCIEVS -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl /local/content/triplestore/stardog/bin/ThesaurusInferred_forTS.owl -u $USER -p $PASSWORD
./stardog data add NCIEVS -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.rdf /local/content/triplestore/stardog/bin/ThesaurusInferred_forTS.rdf -u $USER -p $PASSWORD
./stardog data add CTRP -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl   /local/content/triplestore/stardog/bin/ThesaurusInferred_forTS.owl -u $USER -p $PASSWORD
./stardog data add CTRP -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.rdf   /local/content/triplestore/stardog/bin/ThesaurusInferred_forTS.rdf -u $USER -p $PASSWORD

./stardog-admin db optimize -n CTRP
./stardog-admin db optimize -n NCIEVS

rm /admfs/triplestore/*
cp ./qa_ready_monthly /admfs/triplestore/qa_ready

