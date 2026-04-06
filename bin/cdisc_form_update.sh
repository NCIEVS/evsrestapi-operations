# This script will take the file with the new codes in a .txt file as input

FILE="${1}"
CODELISTS="temp/$$-cdisc-codelist"
SUBSETS="temp/$$-cdisc-subsets"
CDISC_FORM_COPY="cdisc-form.$$.json"

# Reformat the new codes such that all semi-colons are replaced with /n; remove whitespace around hyphens
sed "s/; /\n/g;s/&/&/;s/\s*-\s*/-/g" $FILE >> $CODELISTS.txt

# Get just unique values (Should be just the subsets)
cut -d- -f 1 $CODELISTS.txt | uniq > $SUBSETS.txt

# Set the codelist and subset txts to be JSON format
cat $CODELISTS.txt | jq --raw-input . | jq --slurp . >> $CODELISTS.json
cat $SUBSETS.txt | jq --raw-input . | jq --slurp . >> $SUBSETS.json

# Remove text files
rm $CODELISTS.txt $SUBSETS.txt

# Copy over current cdisc-form.json from ./../config/metadata; have a copy with the current PID
cp ./../config/metadata/cdisc-form.json ./temp/$CDISC_FORM_COPY
cp ./../config/metadata/cdisc-form.json ./temp/original-cdisc-form-$$.json

# Replace subset and codelist section in the copy
jq '(.sections[].fields[] | select(.name == "subset")).options = input | (.sections[].fields[] | select(.name == "codelist")).options = input' "./temp/$CDISC_FORM_COPY" "$SUBSETS.json" "$CODELISTS.json" > ./temp/$$-$CDISC_FORM_COPY

# Copy new form into original file
cp ./temp/$$-$CDISC_FORM_COPY ./temp/$CDISC_FORM_COPY
rm ./temp/$$-$CDISC_FORM_COPY

cp ./temp/$CDISC_FORM_COPY ./../config/metadata/cdisc-form.json

echo "Completed reformatting of codelist and subsets based on $FILE."