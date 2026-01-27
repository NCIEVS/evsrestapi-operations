#!/bin/bash -f

force=0
config=1
help=0
ncflag=""
logfile="bulk_stardog_load_$(date +%Y%m%d_%H%M%S).log"

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
if [[ "$DIR" == /cygdrive/* ]]; then DIR=$(echo "$DIR" | sed 's|^/cygdrive/\([a-zA-Z]\)/\(.*\)|\1:/\2|'); fi


while [[ "$#" -gt 0 ]]; do
  case $1 in
    --force) force=1 ;;
    --noconfig) config=0; ncflag="--noconfig" ;;
    --help) help=1 ;;
    *) ;;
  esac
  shift
done

if [[ $help -eq 1 ]]; then
  echo "Usage: $0 [--noconfig] [--force] [--help]"
  exit 0
fi

URLS=(
  "/local/content/downloads/ThesaurusInferred_forTS.zip"
  "https://current.geneontology.org/ontology/go.owl"
  "http://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt"
  "https://ftp.ebi.ac.uk/pub/databases/chebi/ontology/chebi.owl.gz"
  "https://evs.nci.nih.gov/ftp1/MED-RT/Core_MEDRT_DTS.zip"
  "https://seer.cancer.gov/oncologytoolbox/canmed/hcpcs/?&_export,https://seer.cancer.gov/oncologytoolbox/canmed/ndconc/?&_export"
  "https://wci1.s3.amazonaws.com/NCI/ctcae5.owl"
  "https://wci1.s3.amazonaws.com/NCI/ctcae6.owl"
  "https://wci1.s3.amazonaws.com/NCI/duo_Feb21.owl,https://wci1.s3.amazonaws.com/NCI/iao_Dec20_inferred.owl"
  "https://wci1.s3.amazonaws.com/NCI/obi_2022_07.owl"
  "https://wci1.s3.amazonaws.com/NCI/obib_2021-11.owl"
  "https://wci1.s3.amazonaws.com/NCI/NDFRT_Public_2018.02.05_Inferred.owl"
  "https://wci1.s3.amazonaws.com/NCI/npo-2011-12-08_inferred.owl"
  "https://wci1.s3.amazonaws.com/NCI/MGEDOntology.fix.owl"
  "https://wci1.s3.amazonaws.com/NCI/ma_07_27_2016.owl"
  "https://wci1.s3.amazonaws.com/NCI/umlssemnet.zip"
  "https://wci1.s3.amazonaws.com/NCI/zfa_2019_08_02.owl"
  "https://wci1.s3.amazonaws.com/NCI/202402.zip"
)

echo "Bulk Stardog Load Started: $(date)" | tee -a "$logfile"

for url in "${URLS[@]}"; do
  echo "Loading: $url" | tee -a "$logfile"
  "$DIR"/stardog_load.sh $ncflag $( [[ $force -eq 1 ]] && echo "--force" ) "$url" >>"$logfile" 2>&1
  if [[ $? -ne 0 ]]; then
    echo "  ERROR loading $url (see $logfile)" | tee -a "$logfile"
  else
    echo "  SUCCESS loading $url" | tee -a "$logfile"
  fi
done

echo "Bulk Stardog Load Complete: $(date)" | tee -a "$logfile"