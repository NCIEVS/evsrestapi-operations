# Jena/Fuseki for local development

The image in `docker/fuseki` runs the Jena/Fuseki graph database that the loader scripts and
the EVSRESTAPI server query. It is for local development and tests only: servers use the
native Fuseki install, managed by `bin/jena.service`.

The local image packages **Jena/Fuseki 5.3.0** on **Java 17**, as declared in
`docker/fuseki/Dockerfile`. Its Java runtime is independent of the API and operations
applications, which use Java 25. The image tag below does not specify the version of a
native Fuseki installation on a server.

## Build and run a local docker image

From the root of this repository, run the following command to build the Jena image:

```bash
cd docker/fuseki
docker build -t evsrestapi/fuseki:5.3.0  .
```

### Running a Jena/Fuseki Container

Start the container with the following command. Set `dir` to a local directory of your choice
(for example `c:/data/fuseki` on Windows); the databases are kept there between runs.

```bash
dir=/path/to/data/fuseki
docker run -d --name=jena_evs --rm -p "127.0.0.1:3030:3030" -v "$dir":/opt/fuseki/run/databases evsrestapi/fuseki:5.3.0
```

Keep the port on `127.0.0.1` as shown. The image allows anonymous access to everything,
including SPARQL updates and creating or deleting datasets. Fuseki 5.3.0 also has two known
vulnerabilities in its admin functions (CVE-2025-49656 and CVE-2025-50151, fixed in Jena 5.5.0).
Publishing the port on all interfaces would let other machines on your network use them.

Fuseki gets an 8 GB heap. If Docker runs short of memory alongside OpenSearch, lower it by adding
`-e JAVA_OPTIONS=-Xmx4g` to the `docker run` command.

### Running a sparql query (assumes jena/fuseki running on localhost and curl and jq are installed)

Start by configuring your environment

```
GRAPH_DB_HOST=localhost
GRAPH_DB_PORT=3030
GRAPH_DB_USERNAME=admin
GRAPH_DB_PASSWORD=admin
GRAPH_DB_URL=http://${GRAPH_DB_HOST}:${GRAPH_DB_PORT}
GRAPH_DB=NCIT2
```

Next, put your query into a file.  Make sure to include prefixes and the correct graph name.

```
cat > query.txt << EOF
PREFIX :<http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#> 
PREFIX base:<http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>
PREFIX owl:<http://www.w3.org/2002/07/owl#>
PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:<http://www.w3.org/2001/XMLSchema#>
PREFIX dc:<http://purl.org/dc/elements/1.1/>
PREFIX oboInOwl:<http://www.geneontology.org/formats/oboInOwl#>
PREFIX xml:<http://www.w3.org/2001/XMLSchema#>
SELECT ?code
{ GRAPH <http://NCI_T_monthly> 
    { 
      ?x a owl:Class . 
      ?x :NHC0 ?code .
      ?x :P108 "Melanoma"
    }
}
ORDER BY ?code
EOF
```

Then, run the query.

```
q=`cat query.txt`
curl -v -g -u "${GRAPH_DB_USERNAME}:$GRAPH_DB_PASSWORD" "$GRAPH_DB_URL/NCIT2/query" --data-urlencode "query=$q" -H "Accept: application/sparql-results+json" | jq
```

