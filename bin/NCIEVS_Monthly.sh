USER=tripleroot
PASSWORD=ArofThe4ewR

export JAVA_HOME=/usr/local/jdk1.8

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

