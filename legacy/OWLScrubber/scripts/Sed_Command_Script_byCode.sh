echo "File: $1"
sed -i s%"<P386 rdf:datatype=\"http://www.w3.org/2001/XMLSchema#string\"></P386>"%% $1
sed -i s%"<P385 rdf:datatype=\"http://www.w3.org/2001/XMLSchema#string\"></P385>"%% $1
sed -i s%"<P378 rdf:datatype=\"http://www.w3.org/2001/XMLSchema#string\"></P378>"%% $1
sed -i s%"<P378 rdf:datatype=\"http://www.w3.org/2001/XMLSchema#string\">NCI</P378>"%"<P378>NCI</P378>"% $1
echo "Replacing Annotations"  
sed -i s%\<term-group%\<P383% $1
sed -i s%\</term-group%\</P383% $1
sed -i s%\</term-source%\</P384% $1
sed -i s%\<term-source%\<P384% $1
#cp <file> <file-byCode.owl>

echo "Replacing labels and declarations"
sed -i 's%term-group">%P383">%' $1
sed -i 's%term-source">%P384">%' $1

echo "Testing replacements completed"
grep "Term Source" $1
grep "Term Type" $1
grep "term-source" $1
grep "term-group" $1
grep "XMLSchema#string" $1

 
