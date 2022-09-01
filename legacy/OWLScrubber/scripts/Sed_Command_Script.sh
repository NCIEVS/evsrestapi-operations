echo "File: $1"
cp $1 $1-noSed.owl

#cat <file> | grep "<P386 rdf:datatype=\"http://www.w3.org/2001/XMLSchema#string\"></P386>"
#cat <file> | grep "<P385 rdf:datatype=\"http://www.w3.org/2001/XMLSchema#string\"></P385>"
sed -i s%"<P386 rdf:datatype=\"http://www.w3.org/2001/XMLSchema#string\"></P386>"%% $1
sed -i s%"<P385 rdf:datatype=\"http://www.w3.org/2001/XMLSchema#string\"></P385>"%% $1

#cat <file> | grep -A10 -B10 "term-source"
#cat <file> | grep -A10 -B10 "term-group”
echo "Replacing Annotations"  
sed -i s%\<term-group%\<P383% $1
sed -i s%\</term-group%\</P383% $1
sed -i s%\</term-source%\</P384% $1
sed -i s%\<term-source%\<P384% $1
#cat <file> | grep -A10 -B10 "term-source"
#cat <file> | grep -A10 -B10 "term-group”
#cp <file> <file-byCode.owl>

#cat <file> | grep "Term Source"
#cat <file> | grep "Term Type"
echo "Replacing labels and declarations"
sed -i 's%term-group">%P383">%' $1
sed -i 's%term-source">%P384">%' $1
sed -i 's%label>Term Source%label>term-source%' $1
sed -i 's%label>Term Type%label>term-group%' $1
sed -i 's%label>Source Code%label>source-code%' $1
sed -i 's%label>Subsource Name%label>subsource-name%' $1
sed -i 's%label>Definition Source%label>def-source%' $1
sed -i 's%label>attribution%label>attr%' $1
#cp <file> <file-forLexEVS.owl>
echo "Testing replacements completed"
grep "Term Source" $1
grep "Term Type" $1
grep "term-source" $1
grep "term-group" $1

sed -i s%"xmlns:Thesaurus=%xmlns:ncit=%" $1
head $1

 
