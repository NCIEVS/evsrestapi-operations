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

if [ ${#arr[@]} -ne 2 ] || [ $help -eq 1 ]; then
    echo "Usage: $0 [--help] <terminology> <data file>"
    echo "  e.g. $0 ncit ./Thesaurus.owl"
    exit 1
fi

terminology=${arr[0]}
file=${arr[1]}

echo "--------------------------------------------------"
echo "Starting ...`/bin/date`"
echo "--------------------------------------------------"
echo "terminology = $terminology"
echo "file = $file"

if [[ ! -e $file ]]; then
    echo "ERROR: $file does not exist"
	exit 1
fi

error=0

# NCI Thesaurus checks
if [[ $terminology == "ncit" ]]; then

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
/bin/rm -f /tmp/x.$$

if [[ $error -ne 0 ]]; then 
    echo "Finished with errors"
	exit 1
fi

echo ""
echo "--------------------------------------------------"
echo "Finished ...`/bin/date`"
echo "--------------------------------------------------"


