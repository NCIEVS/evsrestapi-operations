import csv
import os
import pathlib

from src.converter.umls_sem_net import UmlsSemanticNetwork


def test_convert(tmp_path):
    usn: UmlsSemanticNetwork = UmlsSemanticNetwork(pathlib.Path(__file__).parent / "fixtures" / "SRDEF",
                                                   pathlib.Path(__file__).parent / "fixtures" / "SRSTRE1", tmp_path)
    usn.convert()
    assert os.path.exists(tmp_path / "attributes.txt")
    assert os.path.exists(tmp_path / "concepts.txt")
    assert os.path.exists(tmp_path / "parChd.txt")
    assert os.path.exists(tmp_path / "relationships.txt")
    with open(tmp_path / "attributes.txt") as af, open(tmp_path / "concepts.txt") as cf, open(
            tmp_path / "parChd.txt") as pcf, open(tmp_path / "relationships.txt") as rf:
        af_reader = csv.reader(af, delimiter="|")
        cf_reader = csv.reader(cf, delimiter="|")
        pcf_reader = csv.reader(pcf, delimiter="|")
        rf_reader = csv.reader(rf, delimiter="|")

        assert_iterable_count(cf_reader, 181)

        # get some concepts that have different types of attribute and if we are capturing those attributesL
        attribute_samples = get_attribute_samples(af_reader)
        assert len(attribute_samples.get("T001")) == 2
        assert ["STN", "DEF"] == list(map(lambda a: a[1], attribute_samples.get("T001")))
        assert len(attribute_samples.get("T017")) == 4
        assert ["STN", "DEF", "UN", "NH"] == list(map(lambda a: a[1], attribute_samples.get("T017")))
        assert len(attribute_samples.get("T132")) == 3
        assert ["RTN", "DEF", "RI"] == list(map(lambda a: a[1], attribute_samples.get("T132")))

        # assert number of children for T001
        assert_iterable_count(filter(lambda pc_row: pc_row[0] == "T001", pcf_reader), 14)

        t001_relationships = list(filter(lambda r_row: r_row[0] == "T001", rf_reader))
        assert_iterable_count(filter(lambda r_row: r_row[4] == "interacts_with", t001_relationships), 15)
        assert_iterable_count(filter(lambda r_row: r_row[4] == "issue_in", t001_relationships), 2)


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
