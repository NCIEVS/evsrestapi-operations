#!/bin/bash
set -e
echo The current asserted filename to be processed is $1

# Variables
mainDir=${PWD}
echo Main Directory $mainDir
dataDir="/local/content/vocab_processing_OWL2/ProcessingData"
downloadDir="/local/content/downloads"
echo Data Directory $dataDir
prefix="file://"
assertedFilename=EVS$1
memeDate=$(date +"%Y%m%d")
uploadHost="ncicbftp2.nci.nih.gov"
uploadDir="cacore/EVS/upload"
memeUploadDir="/evs/apelon/ForMEME"
ftpUser1=
ftpPassword1=
ftpUser2=
ftpPassword2=
awsdevUser=
awsdevPassword=
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

cp $downloadDir/$1 $dataDir/$assertedFilename

inferredFileName=`echo $assertedFilename | sed 's/^C[a-zA-Z]*/&Inf/'`
echo Inferred File Name $inferredFileName

thisVersion=`echo $1 | sed 's/^T[a-zA-Z]*-//' | sed 's/[0-9]*//' | sed 's/\.[^\.]*$//' | sed 's/\-//'`
echo This Version $thisVersion

assertedPath=$prefix$dataDir/$assertedFilename
inferredPath=$prefix$dataDir/$inferredFileName

echo $assertedPath
echo $inferredPath

#ProtegeKbQA
echo ----------------------------
echo PERFORMING PROTEGEKBQA on $assertedPath
cd ./ProtegeKbQA
QAOutput=$prefix$dataDir/$1_QAOutput.txt
echo The output file is $QAOutput
/usr/java8/bin/java -Xmx8000m -jar ./owlnciqa-2.0.0-jar-with-dependencies.jar -c config/nciowlqa.properties -i $assertedPath -o $QAOutput
cd /local/content/vocab_processing_OWL2
echo Checking for invalid associations
#grep -P "<A(\d+)>" $dataDir/$assertedFilename >> $QAOutput


# OWLScrubber/scripts
cd OWLScrubber/scripts
./Sed_Command_Script.sh $dataDir/$assertedFilename
sedFileName=$assertedFilename-Sed.owl
sedFilePath=$prefix$dataDir/$sedFileName
echo Sed file name $sedFileName
cd ../..


echo
echo "***************************"
echo 
echo Generate OWL Inferred file
echo
echo "***************************"
echo

cd ./GenerateOWLAPIInferred
/usr/java8/bin/java -Xmx15000m -jar ./GenerateOWLAPIInferred-1.0-jar-with-dependencies.jar $assertedPath
cd ..

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
sh runLVG.sh $assertedPath
LVGOutput=$assertedPath-lvg.owl
echo LVG FINISHED
echo LVG output $LVGOutput

#Scrub asserted for FTP and Flat
echo ------------------------------
echo RUNNING OWL SCRUBBER
cd OWLScrubber
FlatOutput=$assertedPath_Flat.txt
FtpOutput=$assertedPath_forFTP.owl
echo outputFile $FtpOutput
/usr/java8/bin/java -jar ./owlscrubber-2.1.0-jar-with-dependencies.jar -F $FlatOutput -C ./owlscrubber.properties -E -N $LVGOutput -O $FtpOutput

#classify with Pellet
echo -------------------------------
echo We should probably classify here.

echo -------------------------------
echo ASSERTED PROCESSING COMPLETE



#echo Making ByCode through Sed
#TEMPORARY
Sed the file to get rid of Term Source, etc
 cd OWLScrubber/scripts
 ./Sed_Command_Script_byCode.sh $dataDir/$sedFile
 cd ../../


cp $dataDir/$sedFile $dataDir/ThesaurusInferred_forTS.owl


echo "Creating variables for output filenames"
flatFile=$assertedFilename"_Flat.txt"
assertedByCode=$1"_forFTP.owl"
inferredMEME=$inferredFileName"-forMEME.owl"
echo $flatFile
echo $assertedByCode
echo $inferredMEME




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
#inferredByCodeStardog="ThesaurusInf-"$version".STARDOG.zip"
#zip $inferredByCodeStardog ThesaurusInferred_forTS.owl ThesaurusInferred_forTS.rdf
zip ThesaurusInferred_forTS.both.zip ThesaurusInferred_forTS.owl ThesaurusInferred_forTS.rdf

echo "Creating CTRP zip filenames"
#Set zip filenames
inferredByCodeZip="ThesaurusInf_"$version".CTRP.zip"

echo "Zipping files for publication"
##Zip the files
zip $inferredByCodeZip ThesaurusInferred_forTS.owl
echo Zip file is $inferredByCodeZip



echo ""
echo "**********************"
echo "MASTER EVS SCRIPT FINISHED"
