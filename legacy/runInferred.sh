#This will run the inferred file through the processsing steps one by one
#Pass in the name of the current and previous inferred files
echo The inferred file to be processed is $1
echo The previous inferred file to be diffed is $2
echo the start date for monthly history in yyyy-mm-dd form is $3
echo the end date for monthly history in yyyy-mm-dd form is $4
echo the current version is $5
echo ------------------------------------------------------------
#PRODUCTION FILE

#Run Value Set Production
echo RUN VALUE SET PRODUCTION
cd ValueSetProduction
rm -f *.xml
/usr/java8/bin/java -jar ./valuesetproduction.jar $1 $2 $5
cd /local/content/vocab_processing_OWL2

#Run OWLSUMMARY on raw files
echo RUN OWLSUMMARY ON RAW FILES
cd OWLSummary
/usr/java8/bin/java -Xmx9000m -jar ./owlsummary-2.0.0-jar-with-dependencies.jar -I $1 -P $2 -S file:///local/content/ProcessingData/rawSummary.txt
cd /local/content/vocab_processing_OWL2

#Run LVG
echo ----------------------------
echo STARTING LVG
sh runLVG.sh $1
LVGOutput=$1-lvg.owl
echo LVG FINISHED
echo LVG output $LVGOutput

#Scrub inferred file for Production
echo SCRUBBING INFERRED FILE FOR PRODUCTION
cd OWLScrubber

ProdOutput=$1-forProduction.owl
echo the output file is $ProdOutput
/usr/java8/bin/java -jar ./owlscrubber-2.1.0-jar-with-dependencies.jar -C ./owlscrubber.properties -E -N $LVGOutput -O $ProdOutput
ProdOutput=`echo $ProdOutput | sed 's/file:\/\/\/local\/content\/ProcessingData\///'`
cp "/local/content/ProcessingData/"$ProdOutput /LexBIG/rawdata/Thesaurus
chmod 775 /LexBIG/rawdata/Thesaurus/$ProdOutput
cd /local/content/vocab_processing_OWL2

echo --------------------------------
echo EXPORT HISTORY
# Export history
# cd ExportHistory
# sh runHistory.sh $3 $4 $5
# cd /local/content/vocab_processing_OWL2

echo RUN HISTORY VALIDATION
# run through HistoryQA
# cd HistoryValidation
# currentPath=pwd
# currentURI=file:///$currentPath
# outputHistory=$1_HistoryValidation.txt
# /usr/java8/bin/java -jar ./historyvalidation-2.0.0-jar-with-dependencies.jar -g ./config/ProtegeHistoryQA.properties -u $1 -p $2 -o $outputHistory
# cd /local/content/vocab_processing_OWL2


#Run through OWLDiff and grep
echo -------------------------------
echo RUN OWLDIFF
cd OWLDiff
outputDiff=file:///local/content/ProcessingData/OWLDiff.txt
/usr/java8/bin/java -Xmx8000m -jar ./owldiff-2.0.0-jar-with-dependencies.jar -i $1 -p $2 -o $outputDiff

grep --file=./config/diffClean.txt /local/content/ProcessingData/OWLDiff.txt > /local/content/ProcessingData/Grepped_OwlDiff.txt
cd /local/content/vocab_processing_OWL2

#****************************************
#MEME FILE

#scrub inferred file for MEME
echo -------------------------------
echo SCRUBBING INFERRED FILE FOR MEME
cd OWLScrubber
MemeOutput=$1-forMEME.owl
echo The output file is $MemeOutput
/usr/java8/bin/java -jar ./owlscrubber-2.1.0-jar-with-dependencies.jar -c ./owlscrubber_meme.properties -E -N $LVGOutput -O $MemeOutput
cd /local/content/vocab_processing_OWL2

#run through OWLSummary
echo ---------------------------------
echo RUN OWLSUMMARY
cd OWLSummary
previousFile=$2-forMEME.owl
echo Current file is $MemeOutput
echo Previous processed file is $previousFile
/usr/java8/bin/java -Xmx9000m -jar ./owlsummary-2.0.0-jar-with-dependencies.jar -I $MemeOutput -P $previousFile -S file:///local/content/ProcessingData/Summary.txt -D file:///local/content/ProcessingData/Details.txt

