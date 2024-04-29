#!/bin/bash -f
#
# This script takes an terminology and an owl file for consideration of loading into
# stardog and checks required things about the file.
#
help=0
while [[ "$#" -gt 0 ]]; do case $1 in
    --help) help=1;;
    *) arr=( "${arr[@]}" "$1" );;
esac; shift; done

if [ ${#arr[@]} -ne 3 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--help] <terminology> <data file> <weekly flag>"
    echo "  e.g. $0 ncit ./Thesaurus.owl"
    exit 1
fi

terminology=${arr[0]}
file=${arr[1]}
weekly=${arr[2]}

echo "--------------------------------------------------"
echo "Starting ...`/bin/date`"
echo "--------------------------------------------------"
echo "terminology = $terminology"
echo "file = $file"
echo "weekly = $weekly"

if [[ ! -e $file ]]; then
    echo "ERROR: $file does not exist"
	exit 1
fi

if [[ $file = *zip ]]; then
    echo "    Unzip file"
    unzip -p $file "*ThesaurusInferred_forTS.owl" > /tmp/fx.$$
    if [[ $? -ne 0 ]]; then
        echo "ERROR: unable to unzip $file"
        exit 1
    fi
    file=/tmp/fx.$$
fi

error=0

get_ncit_last_char() {
  file_name=$(echo "$file" |  perl -pe 's/^.*\///; s/([^\.]+)\..{2,5}$/$1/;')
  echo "${file_name: -1}"
}

# NCI Thesaurus checks
if [[ $terminology == "ncit" ]]; then
  version=$(grep '<owl:versionInfo>' $file | perl -pe 's/.*<owl:versionInfo>//; s/<\/owl:versionInfo>//')
  ncit_last_char=${version: -1}
  # If the last character of the NCIT version is a, b or c and if the script is run as weekly, we want to fail
  if [[ "$ncit_last_char" =~ [^abc] && "$weekly" -eq 1 ]]; then
    echo "A non-weekly NCIT file is run as a weekly load. NCIT version:${version}"
    error=1
  fi
	echo "    Verify each owl:Class has an NHC0 property"
    perl -ne 'if (/<owl:Class /) { $x = 0; $code=$_;}
              if (/<owl:Class/) { $oc++;}
              if (/<NHC0>/ && $oc == 1) { $x = 1; }; 
              if (/<\/owl:Class/ && $oc == 1 && !$x) { print "$code"; }
              if (/<\/owl:Class/) { $oc--; }' $file > /tmp/x.$$
    ct=`cat /tmp/x.$$ | wc -l`
	if [[ $ct -ne 0 ]]; then
	    cat /tmp/x.$$ | sed 's/^/    /;'
        echo "ERROR: missing NHC0 (see above)"
		error=1
	fi

	echo "    Verify each owl:Class has an P108 property"
    perl -ne 'if (/<owl:Class /) { $x = 0; $code=$_;}
              if (/<owl:Class/) { $oc++;}
              if (/<P108>/ && $oc == 1) { $x = 1; }; 
              if (/<\/owl:Class/ && $oc == 1 && !$x) { print "$code"; }
              if (/<\/owl:Class/) { $oc--; }' $file > /tmp/x.$$
    ct=`cat /tmp/x.$$ | wc -l`
	if [[ $ct -ne 0 ]]; then
	    cat /tmp/x.$$ | sed 's/^/    /;'
        echo "ERROR: missing P108 (see above)"
		error=1
	fi

fi

# Cleanup
echo "  Cleanup...`/bin/date`"
/bin/rm -f /tmp/x.$$ /tmp/fx.$$

if [[ $error -ne 0 ]]; then 
    echo "Finished with errors"
	exit 1
fi

echo ""
echo "--------------------------------------------------"
echo "Finished ...`/bin/date`"
echo "--------------------------------------------------"
