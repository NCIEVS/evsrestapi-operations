echo The current asserted filename to be processed is $1


# Variables
currentYear=2019
mainDir=${PWD}
echo Main Directory $mainDir
dataDir="/local/content/ProcessingData"
echo Data Directory $dataDir
uploadHost="ncicbftp2.nci.nih.gov"
uploadDir="evs/nci/Vocabularies/Baselines/$currentYear"
ftpUser2=
ftpPassword2=
assertedFilename=$1

echo "The current year is $currentYear"
echo "Zipping files for publication"
#Zip the files
cd $dataDir
assertedByCodeZip="$1.zip"
zip $assertedByCodeZip $1

dateFolder=`echo $1 | sed 's/^T[a-zA-Z]*-//' | sed 's/-.*//'`
baselineDir=$uploadDir/$dateFolder

echo "Connecting to the FTP and uploading files to $baselineDir"
#Upload files to the ftp
ftp -n $uploadHost <<ENDSCRIPT1
quote USER $ftpUser2
quote PASS $ftpPassword2
cd $uploadDir
binary
mkdir $dateFolder
cd $dateFolder
put $assertedByCodeZip
quit
ENDSCRIPT1

