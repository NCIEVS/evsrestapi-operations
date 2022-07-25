
uploadHost="ncicbftp2.nci.nih.gov"
uploadDir="cacore/EVS/NCI_Thesaurus/upload"
ftpUser1='cacore'
ftpPassword1='Nr2013!!'

cd ../ProcessingData
ftp -n $uploadHost <<ENDSCRIPT1
quote USER $ftpUser1
quote PASS $ftpPassword1
cd $uploadDir
binary
put ThesaurusInferred_forTS.zip
quit
ENDSCRIPT1
