import subprocess
from pathlib import Path

from terminology_converter.qa.qa_utils import (
    EmptyProperty,
    RetiredParentReference,
    find_empty_properties,
    find_retired_parent_references,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
STARDOG_QA = REPO_ROOT / "bin" / "stardog_qa.sh"
NCIT_URL = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl"


def write_ncit_owl_classes(path: Path, class_blocks: str) -> None:
    path.write_text(
        f"""<?xml version="1.0"?>
<rdf:RDF xmlns="{NCIT_URL}#"
         xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
         xmlns:owl="http://www.w3.org/2002/07/owl#"
         xmlns:xsd="http://www.w3.org/2001/XMLSchema#">
  <owl:Ontology rdf:about="{NCIT_URL}">
    <owl:versionInfo>26.04d</owl:versionInfo>
  </owl:Ontology>
{class_blocks}
</rdf:RDF>
""",
        encoding="utf-8",
    )


def write_ncit_owl(path: Path, class_body: str) -> None:
    write_ncit_owl_classes(
        path,
        f"""  <owl:Class rdf:about="{NCIT_URL}#C123">
{class_body}
  </owl:Class>
""",
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


def test_find_empty_properties_identifies_empty_class_property(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl(
        owl_file,
        """    <NHC0>C123</NHC0>
    <P108>Sample Concept</P108>
    <P90 rdf:datatype="http://www.w3.org/2001/XMLSchema#string"></P90>""",
    )

    assert find_empty_properties(owl_file) == [EmptyProperty("C123", "P90")]


def test_find_empty_properties_allows_populated_properties(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl(
        owl_file,
        """    <NHC0>C123</NHC0>
    <P108>Sample Concept</P108>
    <P90 rdf:datatype="http://www.w3.org/2001/XMLSchema#string">Synonym</P90>
    <rdfs:subClassOf rdf:resource="http://example.com/Parent"/>""",
    )

    assert find_empty_properties(owl_file) == []


def test_ncit_qa_fails_for_retired_parent_of_active_concept(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl_classes(
        owl_file,
        f"""  <owl:Class rdf:about="{NCIT_URL}#C27704">
    <NHC0>C27704</NHC0>
    <P108>Retired Parent Concept</P108>
    <owl:deprecated rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true</owl:deprecated>
  </owl:Class>
  <owl:Class rdf:about="{NCIT_URL}#C36347">
    <NHC0>C36347</NHC0>
    <P108>Active Child Concept</P108>
    <owl:deprecated rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">false</owl:deprecated>
    <rdfs:subClassOf rdf:resource="{NCIT_URL}#C27704"/>
  </owl:Class>
""",
    )

    result = run_stardog_qa(owl_file, tmp_path)

    assert result.returncode == 1
    assert "C36347: active concept has retired parent C27704" in result.stdout
    assert "ERROR: retired parents" in result.stdout


def test_find_retired_parent_references_identifies_active_child(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl_classes(
        owl_file,
        f"""  <owl:Class rdf:about="{NCIT_URL}#C27704">
    <NHC0>C27704</NHC0>
    <P108>Retired Parent Concept</P108>
    <owl:deprecated>true</owl:deprecated>
  </owl:Class>
  <owl:Class rdf:about="{NCIT_URL}#C36347">
    <NHC0>C36347</NHC0>
    <P108>Active Child Concept</P108>
    <rdfs:subClassOf rdf:resource="{NCIT_URL}#C27704"/>
  </owl:Class>
""",
    )

    assert find_retired_parent_references(owl_file) == [
        RetiredParentReference("C36347", "C27704", f"{NCIT_URL}#C36347", f"{NCIT_URL}#C27704")
    ]


def test_find_retired_parent_references_allows_retired_child(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl_classes(
        owl_file,
        f"""  <owl:Class rdf:about="{NCIT_URL}#C27704">
    <NHC0>C27704</NHC0>
    <P108>Retired Parent Concept</P108>
    <owl:deprecated>true</owl:deprecated>
  </owl:Class>
  <owl:Class rdf:about="{NCIT_URL}#C36347">
    <NHC0>C36347</NHC0>
    <P108>Retired Child Concept</P108>
    <owl:deprecated>true</owl:deprecated>
    <rdfs:subClassOf rdf:resource="{NCIT_URL}#C27704"/>
  </owl:Class>
""",
    )

    assert find_retired_parent_references(owl_file) == []


def test_find_retired_parent_references_supports_relative_parent_reference(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl_classes(
        owl_file,
        f"""  <owl:Class rdf:about="{NCIT_URL}#C27704">
    <NHC0>C27704</NHC0>
    <P108>Retired Parent Concept</P108>
    <owl:deprecated>true</owl:deprecated>
  </owl:Class>
  <owl:Class rdf:about="{NCIT_URL}#C36347">
    <NHC0>C36347</NHC0>
    <P108>Active Child Concept</P108>
    <rdfs:subClassOf rdf:resource="#C27704"/>
  </owl:Class>
""",
    )

    assert find_retired_parent_references(owl_file) == [
        RetiredParentReference("C36347", "C27704", f"{NCIT_URL}#C36347", "#C27704")
    ]


def test_find_retired_parent_references_ignores_external_parent_fragment(tmp_path):
    owl_file = tmp_path / "Thesaurus.owl"
    write_ncit_owl_classes(
        owl_file,
        f"""  <owl:Class rdf:about="{NCIT_URL}#C27704">
    <NHC0>C27704</NHC0>
    <P108>Retired Parent Concept</P108>
    <owl:deprecated>true</owl:deprecated>
  </owl:Class>
  <owl:Class rdf:about="{NCIT_URL}#C36347">
    <NHC0>C36347</NHC0>
    <P108>Active Child Concept</P108>
    <rdfs:subClassOf rdf:resource="http://example.com/external.owl#C27704"/>
  </owl:Class>
""",
    )

    assert find_retired_parent_references(owl_file) == []
