#!/bin/bash
echo The scrubbed asserted filename to be processed is $1
echo The hisory date is $suffix

#Variables
mainDir=${PWD}
echo Main Directory $mainDir
branchDir="/local/content/ProcessingData/branches/"
extractDir="/local/content/vocab_processing_OWL2/ExtractBranches/"
uploadDir="/cacore/EVS/NCI_Thesaurus/Branches"
neoplasmDir="/cacore/EVS/NCI_Thesaurus/Neoplasm"
uploadHost="ncicbftp2.nci.nih.gov"
ftpUser1='cacore'
ftpPassword1='Nr2013!!'
prefix="file://"
suffix="-formattedBranch-kept.owl"

# Start script
echo EXTRACT BRANCHES START RUN
echo "***********************"
echo 

echo "Working with assertedByCode: $1"
filePath=${1/file:\/\//}

cd ./ExtractBranches

sh ExtractBranches.sh -i $1 -r C12913
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Abnormal_Cell.owl"
mv BranchList.txt $branchDir"Abnormal_Cell.txt"

sh ExtractBranches.sh -i $1 -r C43431
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Activity.owl"
mv BranchList.txt $branchDir"Activity.txt"

sh ExtractBranches.sh -i $1 -r C12219
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Anatomic_Structure_System_or_Substance.owl"
mv BranchList.txt $branchDir"Anatomic_Structure_System_or_Substance.txt"

sh ExtractBranches.sh -i $1 -r C20633
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Biochemical_Pathway.owl"
mv BranchList.txt $branchDir"Biochemical_Pathway.txt"

sh ExtractBranches.sh -i $1 -r C17828
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Biological_Process.owl"
mv BranchList.txt $branchDir"Biological_Process.txt"

sh ExtractBranches.sh -i $1 -r C12218
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Chemotherapy_Regimen_or_Agent_Combination.owl"
mv BranchList.txt $branchDir"Chemotherapy_Regimen_or_Agent_Combination.txt"

sh ExtractBranches.sh -i $1 -r C62634
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Chemotherapy_Regimen.owl"
mv BranchList.txt $branchDir"Chemotherapy_Regimen.txt"

sh ExtractBranches.sh -i $1 -r C20181
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Conceptual_Entity.owl"
mv BranchList.txt $branchDir"Conceptual_Entity.txt"

sh ExtractBranches.sh -i $1 -r C20047
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Diagnostic_or_Prognostic_Factor.owl"
mv BranchList.txt $branchDir"Diagnostic_or_Prognostic_Factor.txt"

sh ExtractBranches.sh -i $1 -r C7057
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Disease_Disorder_or_Finding.owl"
mv BranchList.txt $branchDir"Disease_Disorder_or_Finding.txt"

sh ExtractBranches.sh -i $1 -r C1908
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Drug_Food_Chemical_or_Biomedical_Material.owl"
mv BranchList.txt $branchDir"Drug_Food_Chemical_or_Biomedical_Material.txt"

sh ExtractBranches.sh -i $1 -r C22188
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Experimental_Organism_Anatomical_Concept.owl"
mv BranchList.txt $branchDir"Experimental_Organism_Anatomical_Concept.txt"

sh ExtractBranches.sh -i $1 -r C22187
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Experimental_Organism_Diagnosis.owl"
mv BranchList.txt $branchDir"Experimental_Organism_Diagnosis.txt"

sh ExtractBranches.sh -i $1 -r C16612
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Gene.owl"
mv BranchList.txt $branchDir"Gene.txt"

sh ExtractBranches.sh -i $1 -r C26548
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Gene_Product.owl"
mv BranchList.txt $branchDir"Gene_Product.txt"

sh ExtractBranches.sh -i $1 -r C97325
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Manufactured_Object.owl"
mv BranchList.txt $branchDir"Manufactured_Object.txt"

sh ExtractBranches.sh -i $1 -r C3910
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Molecular_Abnormality.owl"
mv BranchList.txt $branchDir"Molecular_Abnormality.txt"

sh ExtractBranches.sh -i $1 -r C28389
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"NCI_Administrative_Concept.owl"
mv BranchList.txt $branchDir"NCI_Administrative_Concept.txt"

sh ExtractBranches.sh -i $1 -r C14250
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Organism.owl"
mv BranchList.txt $branchDir"Organism.txt"

sh ExtractBranches.sh -i $1 -r C20189
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Property_or_Attribute.owl"
mv BranchList.txt $branchDir"Property_or_Attribute.txt"

sh ExtractBranches.sh -i $1 -r C28428
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Retired_Concept.owl"
mv BranchList.txt $branchDir"Retired_Concept.txt"

sh ExtractBranches.sh -i $1 -r C1909
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Pharmacologic_Substance.owl"
mv BranchList.txt $branchDir"Pharmacologic_Substance.txt"

sh ExtractBranches.sh -i $1 -r C3262
perl formatBranch.pl -k $filePath BranchList.txt $branchDir"Neoplasm.owl"
mv BranchList.txt $branchDir"Neoplasm.txt"

cd $branchDir

rm -f *.zip
rm md5sum.txt
rm Neoplasm.zip.md5.txt

zip Abnormal_Cell.zip Abnormal_Cell.owl
#md5sum Abnormal_Cell.zip > Abnormal_Cell.zip.md5.txt
zip Activity.zip Activity.owl
#md5sum Activity.zip > Activity.zip.md5.txt
zip Anatomic_Structure_System_or_Substance.zip Anatomic_Structure_System_or_Substance.owl
#md5sum Anatomic_Structure_System_or_Substance.zip > Anatomic_Structure_System_or_Substance.zip.md5.txt
zip Biochemical_Pathway.zip Biochemical_Pathway.owl
#md5sum Biochemical_Pathway.zip > Biochemical_Pathway.zip.md5.txt
zip Biological_Process.zip Biological_Process.owl
#md5sum Biological_Process.zip > Biological_Process.zip.md5.txt
zip Chemotherapy_Regimen_or_Agent_Combination.zip Chemotherapy_Regimen_or_Agent_Combination.owl
#md5sum Chemotherapy_Regimen_or_Agent_Combination.zip > Chemotherapy_Regimen_or_Agent_Combination.zip.md5.txt
zip Chemotherapy_Regimen.zip Chemotherapy_Regimen.owl
#md5sum Chemotherapy_Regimen.zip > Chemotherapy_Regimen.zip.md5.txt
zip Conceptual_Entity.zip Conceptual_Entity.owl
#md5sum Conceptual_Entity.zip > Conceptual_Entity.zip.md5.txt
zip Diagnostic_or_Prognostic_Factor.zip Diagnostic_or_Prognostic_Factor.owl
#md5sum Diagnostic_or_Prognostic_Factor.zip > Diagnostic_or_Prognostic_Factor.zip.md5.txt
zip Disease_Disorder_or_Finding.zip Disease_Disorder_or_Finding.owl
#md5sum Disease_Disorder_or_Finding.zip > Disease_Disorder_or_Finding.zip.md5.txt
zip Drug_Food_Chemical_or_Biomedical_Material.zip Drug_Food_Chemical_or_Biomedical_Material.owl
#md5sum Drug_Food_Chemical_or_Biomedical_Material.zip > Drug_Food_Chemical_or_Biomedical_Material.zip.md5.txt
zip Experimental_Organism_Anatomical_Concept.zip Experimental_Organism_Anatomical_Concept.owl
#md5sum Experimental_Organism_Anatomical_Concept.zip > Experimental_Organism_Anatomical_Concept.zip.md5.txt
zip Experimental_Organism_Diagnosis.zip Experimental_Organism_Diagnosis.owl
#md5sum Experimental_Organism_Diagnosis.zip > 
zip Gene.zip Gene.owl
#md5sum Gene.zip > Gene.zip.md5.txt
zip Gene_Product.zip Gene_Product.owl
#md5sum Gene_Product.zip > Gene_Product.zip.md5.txt
zip Manufactured_Object.zip Manufactured_Object.owl
#md5sum Manufactured_Object.zip > Manufactured_Object.zip.md5.txt
zip Molecular_Abnormality.zip Molecular_Abnormality.owl
#md5sum Molecular_Abnormality.zip > Molecular_Abnormality.zip.md5.txt
zip NCI_Administrative_Concept.zip NCI_Administrative_Concept.owl
#md5sum NCI_Administrative_Concept.zip > NCI_Administrative_Concept.zip.md5.txt
zip Organism.zip Organism.owl
#md5sum Organism.zip > Organism.zip.md5.txt
zip Property_or_Attribute.zip Property_or_Attribute.owl
#md5sum Property_or_Attribute.zip > Property_or_Attribute.zip.md5.txt
zip Retired_Concept.zip Retired_Concept.owl
#md5sum Retired_Concept.zip > Retired_Concept.zip.md5.txt
zip Pharmacologic_Substance.zip Pharmacologic_Substance.owl
#md5sum Pharmacologic_Substance.zip > Pharmacologic_Substance.zip.md5.txt
zip Neoplasm.zip Neoplasm.owl
md5sum Neoplasm.zip > Neoplasm.zip.md5.txt
md5sum *.zip > md5sum.txt

echo "Connecting to the FTP and uploading files"
#Upload files to the ftp
ftp -n $uploadHost <<ENDSCRIPT1
quote USER $ftpUser1
quote PASS $ftpPassword1
cd $uploadDir
binary
delete Abnormal_Cell.zip
delete Activity.zip
delete Anatomic_Structure_System_or_Substance.zip
delete Biochemical_Pathway.zip
delete Biological_Process.zip
delete Chemotherapy_Regimen_or_Agent_Combination.zip
delete Chemotherapy_Regimen.zip
delete Conceptual_Entity.zip
delete Diagnostic_or_Prognostic_Factor.zip
delete Disease_Disorder_or_Finding.zip
delete Drug_Food_Chemical_or_Biomedical_Material.zip
delete Experimental_Organism_Anatomical_Concept.zip
delete Experimental_Organism_Diagnosis.zip
delete Gene.zip
delete Gene_Product.zip
delete Manufactured_Object.zip
delete Molecular_Abnormality.zip
delete NCI_Administrative_Concept.zip
delete Organism.zip
delete Property_or_Attribute.zip
delete Retired_Concept.zip
delete Pharmacologic_Substance.zip
delete Neoplasm.zip
delete md5sum.txt
put Abnormal_Cell.zip
put Activity.zip
put Anatomic_Structure_System_or_Substance.zip
put Biochemical_Pathway.zip
put Biological_Process.zip
put Chemotherapy_Regimen_or_Agent_Combination.zip
put Chemotherapy_Regimen.zip
put Conceptual_Entity.zip
put Diagnostic_or_Prognostic_Factor.zip
put Disease_Disorder_or_Finding.zip
put Drug_Food_Chemical_or_Biomedical_Material.zip
put Experimental_Organism_Anatomical_Concept.zip
put Experimental_Organism_Diagnosis.zip
put Gene.zip
put Gene_Product.zip
put Manufactured_Object.zip
put Molecular_Abnormality.zip
put NCI_Administrative_Concept.zip
put Organism.zip
put Property_or_Attribute.zip
put Retired_Concept.zip
put Pharmacologic_Substance.zip
put Neoplasm.zip
put md5sum.txt
cd $neoplasmDir
delete Neoplasm.zip
delete Neoplasm.zip.md5.txt
put Neoplasm.zip
put Neoplasm.zip.md5.txt
quit
ENDSCRIPT1

cd $mainDir
