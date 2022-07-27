filename=`echo $1 | sed 's/file:\/\///'`
infilename=/local/content/vocab_processing_OWL2/ProcessingData/in.owl
outfilename=/local/content/vocab_processing_OWL2/ProcessingData/lvgout.owl
savefilename=$filename"-lvg.owl"
cp $filename $infilename
#./lvg2015/bin/lvg -f:q0 -i:special.txt -o:ospecial.txt -F:2
./lvg2015/bin/lvg -f:q0 -s:"\t" -F:2 -i:$infilename -o:$outfilename
mv $outfilename $savefilename
rm $infilename
