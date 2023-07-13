import csv
import os
import pathlib
from terminology_converter.converter.hgnc import Hgnc
from terminology_converter.converter.owl_file_converter import (
    OwlConverter,
    RDF_URL,
    OWL_URL,
    RDFS_URL,
)
import xml.etree.ElementTree as ET

HGNC_URL = "http://ncicb.nci.nih.gov/genenames.org/HGNC.owl"
DEFAULT_NAMESPACE = f"{HGNC_URL}#"
DEFAULT_NAMESPACE_DICT: dict[str, str] = {"": f"{HGNC_URL}#"}
VERSION = "202307"
TERMINOLOGY = "hgnc"


def test_convert_hgnc(tmp_path):
    hgnc: Hgnc = Hgnc(
        pathlib.Path(__file__).parent / "fixtures" / "hgnc" / "hgnc_complete_set.txt",
        tmp_path,
    )
    hgnc.convert()
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
            HGNC_URL, VERSION, tmp_path, tmp_path, TERMINOLOGY
        )
        owl_converter.convert()
        assert os.path.exists(tmp_path / f"{TERMINOLOGY}.owl")

        tree = ET.parse(tmp_path / "hgnc.owl")
        root = tree.getroot()
        assert_owl_root_and_version(root)
        classes = root.findall("./owl:Class", {"owl": OWL_URL})
        assert_annotation_properties(root)
        # assert_owl_class(classes[0])
        # assert_object_properties(root)


def assert_simple_format(af_reader, cf_reader, pcf_reader):
    # 43709 lines in the file and 27 lines from the locus_group and locus_type fields
    assert_iterable_count(cf_reader, 43709 + 27)

    # get some concepts that have different types of attribute and if we are capturing those attributesL
    attribute_samples = get_attribute_samples(af_reader)
    assert len(attribute_samples.get("HGNC_50")) == 34

    assert [
        "agr",
        "alias_symbol",
        "ccds_id",
        "ccds_id",
        "ccds_id",
        "ccds_id",
        "date_approved_reserved",
        "date_modified",
        "date_name_changed",
        "ena",
        "ensembl_gene_id",
        "entrez_id",
        "gene_group",
        "gene_group_id",
        "hgnc_id",
        "iuphar",
        "location",
        "location_sortable",
        "locus_group",
        "locus_type",
        "mane_select",
        "mane_select",
        "mgd_id",
        "name",
        "omim_id",
        "prev_name",
        "pubmed_id",
        "refseq_accession",
        "rgd_id",
        "status",
        "symbol",
        "ucsc_id",
        "uniprot_ids",
        "vega_id",
    ] == sorted(list(map(lambda a: a[1], attribute_samples.get("HGNC_50"))))
    assert len(attribute_samples.get("HGNC_500")) == 49
    assert [
        "agr",
        "alias_name",
        "alias_name",
        "alias_name",
        "alias_name",
        "alias_symbol",
        "alias_symbol",
        "alias_symbol",
        "alias_symbol",
        "alias_symbol",
        "ccds_id",
        "cd",
        "date_approved_reserved",
        "date_modified",
        "date_name_changed",
        "ena",
        "ensembl_gene_id",
        "entrez_id",
        "enzyme_id",
        "gene_group",
        "gene_group",
        "gene_group",
        "gene_group_id",
        "gene_group_id",
        "gene_group_id",
        "hgnc_id",
        "iuphar",
        "location",
        "location_sortable",
        "locus_group",
        "locus_type",
        "mane_select",
        "mane_select",
        "merops",
        "mgd_id",
        "name",
        "omim_id",
        "prev_name",
        "prev_symbol",
        "prev_symbol",
        "pubmed_id",
        "pubmed_id",
        "refseq_accession",
        "rgd_id",
        "status",
        "symbol",
        "ucsc_id",
        "uniprot_ids",
        "vega_id",
    ] == sorted(list(map(lambda a: a[1], attribute_samples.get("HGNC_500"))))
    assert len(attribute_samples.get("HGNC_5000")) == 33
    assert [
        "agr",
        "ccds_id",
        "date_approved_reserved",
        "date_modified",
        "date_name_changed",
        "date_symbol_changed",
        "ensembl_gene_id",
        "entrez_id",
        "gene_group",
        "gene_group",
        "gene_group_id",
        "gene_group_id",
        "hgnc_id",
        "location",
        "location_sortable",
        "locus_group",
        "locus_type",
        "mane_select",
        "mane_select",
        "mgd_id",
        "name",
        "omim_id",
        "prev_name",
        "prev_name",
        "prev_symbol",
        "pubmed_id",
        "refseq_accession",
        "rgd_id",
        "status",
        "symbol",
        "ucsc_id",
        "uniprot_ids",
        "vega_id",
    ] == sorted(list(map(lambda a: a[1], attribute_samples.get("HGNC_5000"))))

    # assert number of children for T001
    assert_iterable_count(
        filter(lambda pc_row: pc_row[0] == "gene_with_protein_product", pcf_reader),
        19270,
    )


def get_attribute_samples(af_reader):
    attribute_samples = {}
    for concept, attribute_type, value in af_reader:
        attribute = (concept, attribute_type, value)
        if concept == "HGNC_50" or concept == "HGNC_500" or concept == "HGNC_5000":
            attributes = attribute_samples.get(concept, [])
            attributes.append(attribute)
            attribute_samples[concept] = attributes
    return attribute_samples


def assert_iterable_count(i, expected):
    actual = sum(1 for e in i)
    assert actual == expected


def assert_owl_root_and_version(root: ET.Element):
    assert root.tag == f"{{{RDF_URL}}}RDF"
    assert list(root[0].attrib.values())[0] == HGNC_URL
    assert root[0][0].text == VERSION


def assert_annotation_properties(root: ET.Element):
    annotation_properties = root.findall("./owl:AnnotationProperty", {"owl": OWL_URL})
    assert len(annotation_properties) == 54
    assert [
        "agr",
        "alias_name",
        "alias_symbol",
        "bioparadigms_slc",
        "ccds_id",
        "cd",
        "code",
        "cosmic",
        "date_approved_reserved",
        "date_modified",
        "date_name_changed",
        "date_symbol_changed",
        "ena",
        "ensembl_gene_id",
        "entrez_id",
        "enzyme_id",
        "gencc",
        "gene_group",
        "gene_group_id",
        "gtrnadb",
        "hgnc_id",
        "homeodb",
        "horde_id",
        "imgt",
        "iuphar",
        "lncipedia",
        "lncrnadb",
        "location",
        "location_sortable",
        "locus_group",
        "locus_type",
        "lsdb",
        "mamit-trnadb",
        "mane_select",
        "merops",
        "mgd_id",
        "mirbase",
        "name",
        "omim_id",
        "orphanet",
        "preferred_name",
        "prev_name",
        "prev_symbol",
        "pseudogene.org",
        "pubmed_id",
        "refseq_accession",
        "rgd_id",
        "snornabase",
        "status",
        "symbol",
        "synonym",
        "ucsc_id",
        "uniprot_ids",
        "vega_id",
    ] == sorted(list(map(lambda ap: ap[0].text.lower(), annotation_properties)))


def assert_owl_class(first_class: ET.Element):
    assert len(first_class.findall("*")) == 31
    assert (
        first_class.attrib.get(f"{{{RDF_URL}}}about") == f"{DEFAULT_NAMESPACE}HGNC_100"
    )
    assert (
        first_class[0].attrib.get(f"{{{RDF_URL}}}resource")
        == f"{DEFAULT_NAMESPACE}gene_with_protein_product"
    )
    assert first_class.findtext("Code", namespaces=DEFAULT_NAMESPACE_DICT) == "HGNC_100"
    assert (
        first_class.findtext("Semantic_Type", namespaces=DEFAULT_NAMESPACE_DICT) == ""
    )
    assert (
        first_class.findtext("Preferred_Name", namespaces=DEFAULT_NAMESPACE_DICT)
        == "acid sensing ion channel subunit 1"
    )
    assert first_class.findtext("Synonym", namespaces=DEFAULT_NAMESPACE_DICT) == "ASIC1"
    assert first_class.findtext("agr", namespaces=DEFAULT_NAMESPACE_DICT) == "HGNC:5"
    assert (
        first_class.findtext("ccds_id", namespaces=DEFAULT_NAMESPACE_DICT)
        == "CCDS12976"
    )
    assert (
        first_class.findtext(
            "date_approved_reserved", namespaces=DEFAULT_NAMESPACE_DICT
        )
        == "1989-06-30"
    )
    assert (
        first_class.findtext("date_modified", namespaces=DEFAULT_NAMESPACE_DICT)
        == "2023-01-20"
    )
    assert (
        first_class.findtext("ensembl_gene_id", namespaces=DEFAULT_NAMESPACE_DICT)
        == "ENSG00000121410"
    )
    assert first_class.findtext("entrez_id", namespaces=DEFAULT_NAMESPACE_DICT) == "1"
    assert (
        first_class.findtext("gene_group", namespaces=DEFAULT_NAMESPACE_DICT)
        == "Immunoglobulin like domain containing"
    )
    assert (
        first_class.findtext("gene_group_id", namespaces=DEFAULT_NAMESPACE_DICT)
        == "594"
    )
    assert (
        first_class.findtext("hgnc_id", namespaces=DEFAULT_NAMESPACE_DICT) == "HGNC:5"
    )
    assert (
        first_class.findtext("location", namespaces=DEFAULT_NAMESPACE_DICT)
        == "19q13.43"
    )
    assert (
        first_class.findtext("location_sortable", namespaces=DEFAULT_NAMESPACE_DICT)
        == "19q13.43"
    )
    assert (
        first_class.findtext("locus_group", namespaces=DEFAULT_NAMESPACE_DICT)
        == "protein-coding gene"
    )
    assert (
        first_class.findtext("locus_type", namespaces=DEFAULT_NAMESPACE_DICT)
        == "gene with protein product"
    )
    assert (
        first_class.findtext("mane_select", namespaces=DEFAULT_NAMESPACE_DICT)
        == "ENST00000263100.8"
    )
    assert (
        first_class.findtext("mane_select", namespaces=DEFAULT_NAMESPACE_DICT)
        == "NM_130786.4"
    )
    assert (
        first_class.findtext("merops", namespaces=DEFAULT_NAMESPACE_DICT) == "I43.950"
    )
    assert (
        first_class.findtext("mgd_id", namespaces=DEFAULT_NAMESPACE_DICT)
        == "MGI:2152878"
    )
    assert (
        first_class.findtext("name", namespaces=DEFAULT_NAMESPACE_DICT)
        == "alpha-1-B glycoprotein"
    )
    assert (
        first_class.findtext("omim_id", namespaces=DEFAULT_NAMESPACE_DICT) == "138670"
    )
    assert (
        first_class.findtext("pubmed_id", namespaces=DEFAULT_NAMESPACE_DICT)
        == "2591067"
    )
    assert (
        first_class.findtext("refseq_accession", namespaces=DEFAULT_NAMESPACE_DICT)
        == "NM_130786"
    )
    assert (
        first_class.findtext("rgd_id", namespaces=DEFAULT_NAMESPACE_DICT) == "RGD:69417"
    )
    assert (
        first_class.findtext("status", namespaces=DEFAULT_NAMESPACE_DICT) == "Approved"
    )
    assert first_class.findtext("symbol", namespaces=DEFAULT_NAMESPACE_DICT) == "A1BG"
    assert (
        first_class.findtext("ucsc_id", namespaces=DEFAULT_NAMESPACE_DICT)
        == "uc002qsd.5"
    )
    assert (
        first_class.findtext("uniprot_ids", namespaces=DEFAULT_NAMESPACE_DICT)
        == "P04217"
    )
    assert (
        first_class.findtext("vega_id", namespaces=DEFAULT_NAMESPACE_DICT)
        == "OTTHUMG00000183507"
    )
