import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STARDOG_QA = REPO_ROOT / "bin" / "stardog_qa.sh"


def write_ncit_owl(path: Path, class_body: str) -> None:
    path.write_text(
        f"""<?xml version="1.0"?>
<rdf:RDF xmlns="http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#"
         xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:owl="http://www.w3.org/2002/07/owl#"
         xmlns:xsd="http://www.w3.org/2001/XMLSchema#">
  <owl:Ontology rdf:about="http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl">
    <owl:versionInfo>26.04d</owl:versionInfo>
  </owl:Ontology>
  <owl:Class rdf:about="http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C123">
{class_body}
  </owl:Class>
</rdf:RDF>
""",
        encoding="utf-8",
    )


def run_stardog_qa(owl_file: Path, input_directory: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(STARDOG_QA), "ncit", str(owl_file), "0", str(input_directory)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_ncit_qa_fails_for_empty_property(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl(
        owl_file,
        """    <NHC0>C123</NHC0>
    <P108>Sample Concept</P108>
    <P90 rdf:datatype="http://www.w3.org/2001/XMLSchema#string"></P90>""",
    )

    result = run_stardog_qa(owl_file, tmp_path)

    assert result.returncode == 1
    assert "C123: empty P90" in result.stdout
    assert "ERROR: empty properties" in result.stdout


def test_ncit_qa_allows_populated_properties(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl(
        owl_file,
        """    <NHC0>C123</NHC0>
    <P108>Sample Concept</P108>
    <P90 rdf:datatype="http://www.w3.org/2001/XMLSchema#string">Synonym</P90>""",
    )

    result = run_stardog_qa(owl_file, tmp_path)

    assert result.returncode == 0
    assert "ERROR: empty properties" not in result.stdout
