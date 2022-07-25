# This script runs the asserted file processing steps one by one.
# Pass in the name of the current and previous asserted files
echo The current asserted file to be processed is $1

#ProtegeKbQA
#echo ----------------------------
#echo PERFORMING PROTEGEKBQA
#cd ./ProtegeKbQA
#QAOutput=$1_QAOutput.txt
#echo The output file is $QAOutput
#/usr/java8/bin/java -jar ./owlnciqa-2.0.0-jar-with-dependencies.jar -c config/nciowlqa.properties -i $1 -o $QAOutput
#cd /local/content/vocab_processing_OWL2

#Run LVG
echo ----------------------------
echo STARTING LVG
sh runLVG.sh $1
LVGOutput=$1-lvg.owl
echo LVG FINISHED
echo LVG output $LVGOutput

#Scrub asserted for FTP and Flat
echo ------------------------------
echo RUNNING OWL SCRUBBER
cd OWLScrubber
FlatOutput=$1_Flat.txt
FtpOutput=$1_forFTP.owl
echo outputFile $FtpOutput
/usr/java8/bin/java -jar ./owlscrubber-2.1.0-jar-with-dependencies.jar -F $FlatOutput -C ./owlscrubber.properties -E -N $LVGOutput -O $FtpOutput

#classify with Pellet
echo -------------------------------
echo We should probably classify here.

echo -------------------------------
echo ASSERTED PROCESSING COMPLETE
