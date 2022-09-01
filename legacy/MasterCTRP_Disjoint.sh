#!/bin/bash
set -e
echo The current asserted filename to be processed is $1

# Variables
mainDir=${PWD}
echo Main Directory $mainDir
dataDir="/local/content/vocab_processing_OWL2/ProcessingData"
disjointDir="/local/content/vocab_processing_OWL2/disjoint"
downloadDir="/local/content/downloads"
echo Data Directory $dataDir
prefix="file://"
assertedFilename=CTRP$1
memeDate=$(date +"%Y%m%d")
uploadHost="ncicbftp2.nci.nih.gov"
uploadDir="cacore/EVS/upload"
ftpUser1=***
ftpPassword1=***
awsdevUser=***
awsdevPassword=***
awsdevServer="ncias-d2175-c.nci.nih.gov"
awsdevDir="/local/content/downloads"
awsqaServer="ncidb-q294-c.nci.nih.gov"
awsqaDir="/local/content/downloads"

# Start script
echo MASTER SCRIPT START RUN
echo "***********************"
echo 
echo FETCH FILE
echo "***********************"
echo 
echo $dataDir/$1
#cp $downloadDir/$1 $dataDir/$1
cp $downloadDir/$1 $dataDir/$assertedFilename

inferredFileName=`echo $assertedFilename | sed 's/^C[a-zA-Z]*/&Inf/'`
echo Inferred File Name $inferredFileName

thisVersion=`echo $1 | sed 's/^T[a-zA-Z]*-//' | sed 's/[0-9]*//' | sed 's/\.[^\.]*$//' | sed 's/\-//'`
echo This Version $thisVersion

echo
echo "***************************"
echo 
echo Generate OWL Inferred file
echo
echo "***************************"
echo

cd ./GenerateOWLAPIInferred
/usr/java8/bin/java -Xmx15000m -jar ./GenerateOWLAPIInferred-1.0-jar-with-dependencies.jar $prefix$dataDir/$assertedFilename
cd ..


assertedPath=$prefix$dataDir/$assertedFilename
inferredPath=$prefix$dataDir/$inferredFileName
sedFile=$inferredFileName-forProduction.owl
echo $sedFile

#Get the version and filenames
version=$(echo $1 | sed 's/.*\-//' | sed 's/\.owl//')


echo "Working with asserted file: " $assertedPath
echo "Working with inferred file: " $inferredPath

echo
echo "*************************"
echo
echo  "Processed Inferred File"
echo
echo "***********************"
echo



#Run LVG
echo ----------------------------
echo STARTING LVG
sh runLVG.sh $inferredPath
LVGOutput=$inferredPath-lvg.owl
echo LVG FINISHED
echo LVG output $LVGOutput

#ProtegeKbQA
#echo ----------------------------
#echo PERFORMING PROTEGEKBQA
#cd ./ProtegeKbQA
#QAOutput=$1_CTRP_QA.txt
#echo The output file is $QAOutput
#/usr/java8/bin/java -jar ./owlnciqa-2.0.0-jar-with-dependencies.jar -c config/nciowlqa.properties -i $assertedFilename -o $QAOutput
#cd /local/content/vocab_processing_OWL2

#Scrub inferred file for Production
echo SCRUBBING INFERRED FILE FOR PRODUCTION
cd OWLScrubber

ProdOutput=$inferredPath-forProduction.owl
echo the output file is $ProdOutput
/usr/java8/bin/java -Xmx15000M -jar ./owlscrubber-2.1.0-jar-with-dependencies.jar -C ./owlscrubber.properties -E -N $LVGOutput -O $ProdOutput
cd /local/content/vocab_processing_OWL2

#echo Check that NCI-DEFCURATOR replaced
#./grepTest.sh $ProdOutput


#Run through OWLDiff and grep
#echo -------------------------------
#echo RUN OWLDIFF
#cd OWLDiff
#outputDiff="file:///local/content/ProcessingData/CTRP_Diff.txt"
#/usr/java8/bin/java -Xmx8000m -jar ./owldiff-2.0.0-jar-with-dependencies.jar -i $inferredPath -p $previousInferredPath -o $outputDiff

#grep --file=./config/diffClean.txt /local/content/ProcessingData/CTRP_Diff.txt > /local/content/ProcessingData/Grepped_CTRP_Diff.txt
#cd /local/content/vocab_processing_OWL2


#TEMPORARY
echo Making ByCode through Sed
#Sed the file to get rid of Term Source, etc
 cd OWLScrubber/scripts
 ./Sed_Command_Script_byCode.sh $dataDir/$sedFile
 cd ../../
cp $dataDir/$sedFile $dataDir/ThesaurusInferred_forTS.owl



##########################
### Apply Disjoint 
cd $disjointDir 
/usr/java8/bin/java -Xms512m -Xmx8g OWLDisjointWithProcessor  $dataDir/ThesaurusInferred_forTS.owl

sleep 10s
cp $dataDir/ThesaurusInferred_forTS_disjoint.owl $dataDir/ThesaurusInferred_forTS.owl

##########################

echo
echo "********************"
echo
echo  "Preparing FTP"
echo
echo "*******************"
echo
echo "Changing to the data directory"
cd $dataDir

echo "Creating Flat File"
../bin/owl2rdf $dataDir/ThesaurusInferred_forTS.owl > $dataDir/ThesaurusInferred_forTS.rdf

echo "zipping Stardog data" 
inferredByCodeStardog="ThesaurusInf-"$version".STARDOG.zip"
zip $inferredByCodeStardog ThesaurusInferred_forTS.owl ThesaurusInferred_forTS.rdf
zip ThesaurusInferred_forTS.both.zip ThesaurusInferred_forTS.owl ThesaurusInferred_forTS.rdf

echo "Creating CTRP zip filenames"
#Set zip filenames
inferredByCodeZip="ThesaurusInf_"$version".CTRP.zip"

echo "Zipping files for publication"
##Zip the files
zip $inferredByCodeZip ThesaurusInferred_forTS.owl
echo Zip file is $inferredByCodeZip
## wait for zipping to complete
sleep 10s

#echo "Connecting to CTRP AWS and uploading files"
#aws s3 cp $inferredByCodeZip  s3://stardog-upload-int/$inferredByCodeZip --sse=AES256 --profile ctrp

cp $inferredByCodeZip ThesaurusInferred_forTS.zip

echo "Placing file on FTP"
ftp -n $uploadHost <<ENDSCRIPT1
quote USER $ftpUser1
quote PASS $ftpPassword1
cd $uploadDir
binary
put ThesaurusInferred_forTS.zip
put ThesaurusInferred_forTS.both.zip
quit
ENDSCRIPT1

#echo "Placing file on AWS"
#login = $awsdevUser@awsdevServer
#echo $login
#ftp $awsdevUser@$awsdevServer <<ENDSCRIPT1
#cd $awsdevDir
#binary
#put ThesaurusInferred_forTS.zip
#quit
#ENDSCRIPT1

#echo "Placing file on AWS"
#login = $awsqaUser@awsqaServer
#echo $login
#ftp $awsqaUser@$awsqaServer <<ENDSCRIPT1
#cd $awsqaDir
#binary
#put ThesaurusInferred_forTS.zip
#quit
#ENDSCRIPT1

echo ""
echo "**********************"
echo "MASTER SCRIPT FINISHED"
