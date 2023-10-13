import csv
import os
import pathlib

from terminology_converter.converter.owl_file_converter import (
    RDF_URL,
    RDFS_URL,
)
import xml.etree.ElementTree as ET

from terminology_converter.converter.canmed import Canmed
from terminology_converter.converter.owl_file_converter import OwlConverter, OWL_URL

CANMED_URL = "http://seer.nci.nih.gov/CanMED.owl"
DEFAULT_NAMESPACE = f"{CANMED_URL}#"
DEFAULT_NAMESPACE_DICT: dict[str, str] = {"": f"{CANMED_URL}#"}
VERSION = "202309"
TERMINOLOGY = "canmed"


def test_convert_canmed(tmp_path):
    canmed: Canmed = Canmed(
        pathlib.Path(__file__).parent / "fixtures" / "canmed" / "hcpcs_results.csv",
        pathlib.Path(__file__).parent / "fixtures" / "canmed" / "ndconc_results.csv",
        tmp_path,
    )
    canmed.convert()
    assert os.path.exists(tmp_path / "attributes.txt")
    assert os.path.exists(tmp_path / "concepts.txt")
    assert os.path.exists(tmp_path / "parChd.txt")
    with open(tmp_path / "attributes.txt") as af, open(
            tmp_path / "concepts.txt"
    ) as cf, open(tmp_path / "parChd.txt") as pcf:
        af_reader = csv.reader(af, delimiter="|")
        cf_reader = csv.reader(cf, delimiter="|")
        pcf_reader = csv.reader(pcf, delimiter="|")

        assert_simple_format(af_reader, cf_reader, pcf_reader)
        owl_converter: OwlConverter = OwlConverter(
            CANMED_URL, VERSION, tmp_path, tmp_path, TERMINOLOGY
        )
        owl_converter.convert()
        assert os.path.exists(tmp_path / f"{TERMINOLOGY}.owl")

        tree = ET.parse(tmp_path / f"{TERMINOLOGY}.owl")
        root = tree.getroot()
        assert_owl_root_and_version(root)
        classes = root.findall("./owl:Class", {"owl": OWL_URL})
        assert_annotation_properties(root)
        sample_classes = [clz for clz in classes if
                          clz.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about").replace(f"{CANMED_URL}#",
                                                                                                "") in ["A9534"]]
        assert_owl_class(sample_classes[0])


def assert_simple_format(af_reader, cf_reader, pcf_reader):
    # 43709 lines in the file and 27 lines from the locus_group and locus_type fields
    cf_rows = list(cf_reader)
    assert_iterable_count(cf_rows, 16867)
    # assert that all NA HCPCS codes got converted
    assert len([cf_row for cf_row in cf_rows if cf_row[0] == "HCPCS_NA"]) == 0
    # assert that at least one NA got converted to Generic Name + Strength
    assert len([cf_row for cf_row in cf_rows if cf_row[0] == "HCPCS_CEDAZURIDINE_AND_DECITABINE_100MG_35MG"]) == 1
    # get some concepts that have different types of attribute and if we are capturing those attributesL
    attribute_samples = get_attribute_samples(af_reader)
    assert len(attribute_samples.get("HCPCS_RIBOCICLIB_200_MG")) == 7

    assert [
               "Brand Name", "FDA Approval Year", "HCPCS_Code", "Oral", "Status", "Strength", "owl:deprecated"
           ] == sorted(list(map(lambda a: a[1], attribute_samples.get("HCPCS_RIBOCICLIB_200_MG"))))
    assert len(attribute_samples.get("J9320")) == 8
    assert [
               "Brand Name", "CMS Effective Date", "FDA Approval Year", "HCPCS_Code", "Oral", "Status", "Strength",
               "owl:deprecated"
           ] == sorted(list(map(lambda a: a[1], attribute_samples.get("J9320"))))

    assert len(attribute_samples.get("NDC_55154-3915-05")) == 12
    assert [
               "Administration Route", "Administration Route", "Brand Name", "Description", "Discontinue_Date",
               "Effective_Date", "Generic Name", "NDC_Package_Code",
               "NDC_Product_Code", "Status", "Strength", "owl:deprecated"
           ] == sorted(list(map(lambda a: a[1], attribute_samples.get("NDC_55154-3915-05"))))

    assert len(attribute_samples.get("NDC_00069-4547")) == 10
    assert [
               "Administration Route", "Administration Route", "Administration Route", "Administration Route",
               "Administration Route", "Administration Route", "Administration Route", "Administration Route",
               "Brand Name", "Generic Name"
           ] == sorted(list(map(lambda a: a[1], attribute_samples.get("NDC_00069-4547"))))

    # assert hierarchy count of HCPCS
    pc_rows = list(pcf_reader)
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "HCPCS_CHEMOTHERAPY", pc_rows),
        23,
    )
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "HCPCS_ESTROGEN", pc_rows),
        6,
    )
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "HCPCS_ASPARAGINASE", pc_rows),
        3,
    )

    # assert hierarchy count of NDC
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "NDC_HORMONAL_THERAPY", pc_rows),
        15,
    )
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "NDC_ANDROGEN_RECEPTOR_INHIBITOR", pc_rows),
        3,
    )
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "NDC_5HT3_RECEPTOR_ANTAGONIST", pc_rows),
        17,
    )
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "NDC_PREDNISONE", pc_rows),
        487,
    )
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "NDC_68462-0106", pc_rows),
        2,
    )


def get_attribute_samples(af_reader):
    attribute_samples = {}
    for concept, attribute_type, value in af_reader:
        attribute = (concept, attribute_type, value)
        if concept == "HCPCS_RIBOCICLIB_200_MG" or concept == "J9320" or concept == "NDC_55154-3915-05" or concept == "NDC_00069-4547":
            attributes = attribute_samples.get(concept, [])
            attributes.append(attribute)
            attribute_samples[concept] = attributes
    return attribute_samples


def assert_iterable_count(i, expected):
    actual = sum(1 for e in i)
    assert actual == expected


def assert_owl_root_and_version(root: ET.Element):
    assert root.tag == f"{{{RDF_URL}}}RDF"
    assert list(root[0].attrib.values())[0] == CANMED_URL
    assert root[0][0].text == VERSION


def assert_annotation_properties(root: ET.Element):
    annotation_properties = root.findall("./owl:AnnotationProperty", {"owl": OWL_URL})
    expected_attributes = [
        "administration_route", "brand_name", "cms_discontinuation_date", "cms_effective_date", "code",
        "description", "discontinue_date", "effective_date", "fda_approval_year", "fda_discontinuation_year",
        "generic_name", "hcpcs_code", "ndc_package_code", "ndc_product_code", "oral", "preferred_name", "status",
        "strength", "synonym"
    ]
    assert len(annotation_properties) == len(expected_attributes)
    assert expected_attributes == sorted(list(map(lambda ap: ap[0].text.lower(), annotation_properties)))


def assert_owl_class(first_class: ET.Element):
    assert first_class.findtext("Code", namespaces=DEFAULT_NAMESPACE_DICT) == "A9534"
    assert first_class.findtext("Preferred_Name", namespaces=DEFAULT_NAMESPACE_DICT) == "Tositumomab per MC"
    assert first_class.findtext("FDA_Approval_Year", namespaces=DEFAULT_NAMESPACE_DICT) == "2003"
    brands: list[ET.Element] = first_class.findall("Brand_Name", namespaces=DEFAULT_NAMESPACE_DICT)
    assert sorted(list(map(lambda brand: brand.text, brands))) == [" Iodine i-131 Tositumomab", " therapeutic",
                                                                   "Bexxar"]
    assert first_class.findtext("HCPCS_Code", namespaces=DEFAULT_NAMESPACE_DICT) == "A9534"
    assert first_class.findtext("Oral", namespaces=DEFAULT_NAMESPACE_DICT) == "No"
    # assert first_class.findtext("deprecated", namespaces={"owl": OWL_URL}) == "false"
    assert first_class.findtext("FDA_Discontinuation_Year", namespaces=DEFAULT_NAMESPACE_DICT) == "2014"
    assert first_class.findtext("CMS_Effective_Date", namespaces=DEFAULT_NAMESPACE_DICT) == "07/01/2003 00:00:00"
    assert first_class.findtext("Status", namespaces=DEFAULT_NAMESPACE_DICT) == "In Use"

    parent_elements: list[ET.Element] = first_class.findall(
        "./rdfs:subClassOf[@rdf:resource]", {"rdfs": RDFS_URL, "rdf": RDF_URL}
    )
    assert len(parent_elements) == 1
    parents = [
        parent_element.get(f"{{{RDF_URL}}}resource")
        for parent_element in parent_elements
    ]
    assert f"{CANMED_URL}#HCPCS_TOSITUMOMAB" in parents
