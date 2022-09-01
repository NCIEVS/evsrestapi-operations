USER=***
PASSWORD=***

./stardog data remove --all  CTRP -u $USER -p $PASSWORD
#./stardog data add CTRP -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl /LexBIG/rawdata/TripleStore/ThesaurusInferred_forTS.owl -u $USER -p $PASSWORD
#./stardog data remove   -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.rdf CTRP -u $USER -p $PASSWORD

./stardog data add CTRP -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl /local/content/triplestore/stardog/bin/ThesaurusInferred_forTS.owl -u $USER -p $PASSWORD
#./stardog data add CTRP -g http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.rdf /local/content/triplestore/stardog/bin/ThesaurusInferred_forTS.rdf -u $USER -p $PASSWORD

./stardog-admin db optimize -n CTRP

rm /admfs/triplestore/*
cp ./qa_ready_weekly /admfs/triplestore/qa_ready

