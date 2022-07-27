#!/bin/bash
set -e
# echo The current asserted filename to be processed is $1

# Variables
mainDir=${PWD}
echo Main Directory $mainDir
dataDir="/local/content/vocab_processing_OWL2/ProcessingData"
echo Data Directory $dataDir
prefix="file://"
assertedFilename=CTRP$1
memeDate=$(date +"%Y%m%d")
uploadHost="ncicbftp2.nci.nih.gov"
uploadDir="cacore/EVS/upload"
ftpUser1=
ftpPassword1=
awsdevUser=
awsdevPassword=
awsdevServer="ncias-d2175-c.nci.nih.gov"
awsdevDir="/local/content/downloads"
awsqaServer="ncidb-q294-c.nci.nih.gov"
awsqaDir="/local/content/downloads"


echo "Placing file on FTP"
sftp -n $uploadHost <<ENDSCRIPT1
quote USER $ftpUser1
quote PASS $ftpPassword1
cd $uploadDir
binary
put ThesaurusInferred_forTS.zip
#put ThesaurusInferred_forTS.both.zip
quit
ENDSCRIPT1

echo "Placing file on AWS"
login = $awsdevUser@awsdevServer
echo $login
ftp $awsdevUser@$awsdevServer <<ENDSCRIPT1
cd $awsdevDir
binary
put ThesaurusInferred_forTS.zip
quit
ENDSCRIPT1

echo "Placing file on AWS"
login = $awsqaUser@awsqaServer
echo $login
ftp $awsqaUser@$awsqaServer <<ENDSCRIPT1
cd $awsqaDir
binary
put ThesaurusInferred_forTS.zip
quit
ENDSCRIPT1

echo ""
echo "**********************"
echo "Upload ThesaurusInferred_forTS.zip FINISHED"

