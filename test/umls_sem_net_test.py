import csv
import os
import pathlib
import xml.etree.ElementTree as ET

from src.terminology_converter.converter.umls_sem_net import UmlsSemanticNetwork
from terminology_converter.converter.owl_file_converter import (
    OwlConverter,
    RDF_URL,
    OWL_URL,
    RDFS_URL,
)

UMLS_SEM_NET_URL = "http://www.nlm.nih.gov/research/umls/umlssemnet.owl"
DEFAULT_NAMESPACE = f"{UMLS_SEM_NET_URL}#"
DEFAULT_NAMESPACE_DICT: dict[str, str] = {"": f"{UMLS_SEM_NET_URL}#"}
VERSION = "2023AA"
TERMINOLOGY = "umlssemnet"


def test_convert_umls(tmp_path):
    usn: UmlsSemanticNetwork = UmlsSemanticNetwork(
        pathlib.Path(__file__).parent / "fixtures" / "umlssemnet" / "SRDEF",
        pathlib.Path(__file__).parent / "fixtures" / "umlssemnet" / "SRSTRE1",
        pathlib.Path(__file__).parent / "fixtures" / "umlssemnet" / "SRSTR",
        tmp_path,
    )
    usn.convert()
    assert os.path.exists(tmp_path / "attributes.txt")
    assert os.path.exists(tmp_path / "concepts.txt")
    assert os.path.exists(tmp_path / "parChd.txt")
    assert os.path.exists(tmp_path / "relationships.txt")
    with open(tmp_path / "attributes.txt") as af, open(
            tmp_path / "concepts.txt"
    ) as cf, open(tmp_path / "parChd.txt") as pcf, open(
        tmp_path / "relationships.txt"
    ) as rf:
        af_reader = csv.reader(af, delimiter="|")
        cf_reader = csv.reader(cf, delimiter="|")
        pcf_reader = csv.reader(pcf, delimiter="|")
        rf_reader = csv.reader(rf, delimiter="|")

        assert_simple_format(af_reader, cf_reader, pcf_reader, rf_reader)

        owl_converter: OwlConverter = OwlConverter(
            UMLS_SEM_NET_URL, VERSION, tmp_path, tmp_path, TERMINOLOGY
        )
        owl_converter.convert()
        assert os.path.exists(tmp_path / f"{TERMINOLOGY}.owl")

        tree = ET.parse(tmp_path / "umlssemnet.owl")
        root = tree.getroot()
        assert_owl_root_and_version(root)
        classes = root.findall("./owl:Class", {"owl": OWL_URL})
        assert_annotation_properties(root)
        assert_owl_class(classes[0])
        assert_object_properties(root)


def assert_simple_format(af_reader, cf_reader, pcf_reader, rf_reader):
    assert_iterable_count(cf_reader, 181)

    # get some concepts that have different types of attribute and if we are capturing those attributes
    attribute_samples = get_attribute_samples(af_reader)
    assert len(attribute_samples.get("T001")) == 2
    assert ["STN", "DEF"] == list(map(lambda a: a[1], attribute_samples.get("T001")))
    assert len(attribute_samples.get("T017")) == 4
    assert ["STN", "DEF", "UN", "NH"] == list(
        map(lambda a: a[1], attribute_samples.get("T017"))
    )
    assert len(attribute_samples.get("T132")) == 3
    assert ["RTN", "DEF", "RI"] == list(
        map(lambda a: a[1], attribute_samples.get("T132"))
    )

    # assert number of children for T001
    assert_iterable_count(filter(lambda pc_row: pc_row[0] == "T001", pcf_reader), 4)

    t001_relationships = list(filter(lambda r_row: r_row[0] == "T001", rf_reader))
    assert_iterable_count(
        filter(lambda r_row: r_row[4] == "interacts_with", t001_relationships), 15
    )
    assert_iterable_count(
        filter(lambda r_row: r_row[4] == "issue_in", t001_relationships), 2
    )


def assert_owl_root_and_version(root: ET.Element):
    assert root.tag == f"{{{RDF_URL}}}RDF"
    assert list(root[0].attrib.values())[0] == UMLS_SEM_NET_URL
    assert root[0][0].text == VERSION


def assert_annotation_properties(root: ET.Element):
    annotation_properties = root.findall("./owl:AnnotationProperty", {"owl": OWL_URL})
    assert len(annotation_properties) == 10
    assert [
               "Code",
               "Semantic_Type",
               "DEF",
               "NH",
               "Preferred_Name",
               "RI",
               "RTN",
               "STN",
               "Synonym",
               "UN",
           ] == list(map(lambda ap: ap[0].text, annotation_properties))


def assert_object_properties(root: ET.Element):
    object_property_labels = root.findall("./owl:ObjectProperty/rdfs:label", {"owl": OWL_URL, "rdfs": RDFS_URL})
    assert len(object_property_labels) == 48
    expected_relationship_types = {
        "affects",
        "developmental_form_of",
        "indicates",
        "associated_with",
        "practices",
        "tributary_of",
        "prevents",
        "part_of",
        "branch_of",
        "evaluation_of",
        "performs",
        "occurs_in",
        "carries_out",
        "contains",
        "process_of",
        "derivative_of",
        "degree_of",
        "consists_of",
        "manifestation_of",
        "diagnoses",
        "location_of",
        "ingredient_of",
        "property_of",
        "manages",
        "uses",
        "interacts_with",
        "co-occurs_with",
        "precedes",
        "measurement_of",
        "exhibits",
        "connected_to",
        "interconnects",
        "conceptually_related_to",
        "measures",
        "assesses_effect_of",
        "result_of",
        "complicates",
        "issue_in",
        "method_of",
        "treats",
        "traverses",
        "adjacent_to",
        "causes",
        "analyzes",
        "disrupts",
        "surrounds",
        "produces",
        "conceptual_part_of",
    }
    assert sorted(expected_relationship_types) == sorted(
        set(map(lambda op: op.text, object_property_labels))
    )
    object_properties = root.findall("./owl:ObjectProperty",
                                     {"owl": OWL_URL})
    for object_property in object_properties:
        code = get_default_ns_element_text(object_property, "Code")
        if code == "T151":
            assert object_property.findtext("rdfs:label", namespaces={"rdfs": RDFS_URL}) == "affects"
            assert object_property.attrib[f"{{{RDF_URL}}}about"] == append_url("T151")
            sub_object_property_of = object_property.find("./owl:subObjectPropertyOf", {"owl": OWL_URL})
            assert sub_object_property_of.attrib[f"{{{RDF_URL}}}resource"] == append_url("T139")
            assert get_default_ns_element_text(object_property, "Semantic_Type") == "RL"
            assert get_default_ns_element_text(object_property, "Preferred_Name") == "affects"
            assert get_default_ns_element_text(object_property, "Synonym") == "AF"
            assert get_default_ns_element_text(object_property, "RTN") == "R3.1"
            assert "Produces a direct effect on" in get_default_ns_element_text(object_property, "DEF")
            assert get_default_ns_element_text(object_property, "RI") == "affected_by"


def assert_owl_class(first_class: ET.Element):
    assert first_class.findtext("Code", namespaces=DEFAULT_NAMESPACE_DICT) == "T001"
    assert (
            first_class.findtext("Semantic_Type", namespaces=DEFAULT_NAMESPACE_DICT)
            == "STY"
    )
    assert (
            first_class.findtext("Preferred_Name", namespaces=DEFAULT_NAMESPACE_DICT)
            == "Organism"
    )
    assert first_class.findtext("Synonym", namespaces=DEFAULT_NAMESPACE_DICT) == "orgm"
    assert first_class.findtext("STN", namespaces=DEFAULT_NAMESPACE_DICT) == "A1.1"
    assert (
            first_class.findtext("DEF", namespaces={"": DEFAULT_NAMESPACE})
            == "Generally, a living individual, including all plants and animals."
    )

    parent_elements: list[ET.Element] = first_class.findall(
        "./rdfs:subClassOf[@rdf:resource]", {"rdfs": RDFS_URL, "rdf": RDF_URL}
    )
    assert len(parent_elements) == 1
    parents = [
        parent_element.get(f"{{{RDF_URL}}}resource")
        for parent_element in parent_elements
    ]
    assert f"{UMLS_SEM_NET_URL}#T072" in parents

    relationship_elements: list[ET.Element] = first_class.findall(
        "./rdfs:subClassOf/owl:Restriction", {"rdfs": RDFS_URL, "owl": OWL_URL}
    )
    relationships = {}
    for relationship_element in relationship_elements:
        relationships.setdefault(
            relationship_element[0].get(f"{{{RDF_URL}}}resource"), []
        ).append(relationship_element[1].get(f"{{{RDF_URL}}}resource"))
    assert len(relationships) == 2
    expected_interacts_with = list(
        map(
            lambda eiw: f"{UMLS_SEM_NET_URL}#{eiw}",
            [
                "T001",
                "T002",
                "T004",
                "T005",
                "T007",
                "T008",
                "T010",
                "T011",
                "T012",
                "T013",
                "T014",
                "T015",
                "T016",
                "T194",
                "T204",
            ],
        )
    )
    assert relationships.get(append_url("interacts_with")) == expected_interacts_with


def get_attribute_samples(af_reader):
    attribute_samples = {}
    for concept, attribute_type, value in af_reader:
        attribute = (concept, attribute_type, value)
        if concept == "T001" or concept == "T017" or concept == "T132":
            attributes = attribute_samples.get(concept, [])
            attributes.append(attribute)
            attribute_samples[concept] = attributes
    return attribute_samples


def assert_iterable_count(i, expected):
    actual = sum(1 for e in i)
    assert actual == expected


def append_url(value: str) -> str:
    return f"{UMLS_SEM_NET_URL}#{value}"


def get_default_ns_element_text(parent_element: ET.Element, child_element_name) -> str:
    return parent_element.findtext(child_element_name, namespaces=DEFAULT_NAMESPACE_DICT)
