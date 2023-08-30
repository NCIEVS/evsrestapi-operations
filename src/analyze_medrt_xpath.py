import csv
from dataclasses import dataclass
import re
from re import Pattern

CONCEPT_NAMESPACE_REGEX = re.compile("\/terminology\[\d*\]/concept\[\d*\]/namespace\[\d*\]=")
CONCEPT_STATUS_REGEX = re.compile("\/terminology\[\d*\]/concept\[\d*\]/status\[\d*\]=")
SYNONYM_NAMESPACE_REGEX = re.compile("\/terminology\[\d*\]/concept\[\d*\]/synonym\[\d*\]/namespace\[\d*\]=")
SYNONYM_TO_NAMESPACE_REGEX = re.compile("\/terminology\[\d*\]/concept\[\d*\]/synonym\[\d*\]/to_namespace\[\d*\]=")
SYNONYM_NAME_REGEX = re.compile("\/terminology\[\d*\]/concept\[\d*\]/synonym\[\d*\]/name\[\d*\]=")
PROPERTY_REGEX = re.compile("\/terminology\[\d*\]/concept\[\d*\]/property\[\d*\]")
PROPERTY_CONTENT_REGEX = re.compile("\/terminology\[\d*\]/concept\[\d*\]/property\[\d*\]/content\[\d*\]")
PROPERTY_NAME_REGEX = re.compile("\/terminology\[\d*\]/concept\[\d*\]/property\[\d*\]/name\[\d*\]")


@dataclass(eq=True, frozen=True)
class ConceptProperty:
    name: str
    content: str


def append_if_matched(values: set, pattern: Pattern) -> bool:
    if pattern.match(row[0]):
        values.add(get_value(row))
        return True
    return False


def get_value(row: tuple) -> str:
    return row[0].split("=")[1]


with open("/Users/squareroot/Documents/wci/loading-terminologies/MED-RT/Core_MEDRT_DTS/xpaths.txt") as af:
    reader = csv.reader(af)
    concept_namespace_values = set()
    concept_status_values = set()
    synonym_namespace_values = set()
    synonym_to_namespace_values = set()
    synonym_name_values = set()
    properties = set()
    for row in reader:
        value = get_value(row)
        if append_if_matched(concept_namespace_values, CONCEPT_NAMESPACE_REGEX):
            continue
        if append_if_matched(concept_status_values, CONCEPT_STATUS_REGEX):
            continue
        if append_if_matched(synonym_namespace_values, SYNONYM_NAMESPACE_REGEX):
            continue
        if append_if_matched(synonym_name_values, SYNONYM_NAME_REGEX):
            continue
        if append_if_matched(synonym_to_namespace_values, SYNONYM_TO_NAMESPACE_REGEX):
            continue
        if PROPERTY_CONTENT_REGEX.match(row[0]):
            property_content = value
        if PROPERTY_NAME_REGEX.match(row[0]):
            property_name = value
            properties.add(ConceptProperty(property_name, property_content))
    print(f"Concept namespace values: {concept_namespace_values}")
    print(f"Concept status values: {concept_status_values}")
    print(f"Synonym namespace values: {synonym_namespace_values}")
    print(f"Synonym name values: {synonym_name_values}")
    print(f"Synonym to_namespace values: {synonym_to_namespace_values}")
    print(f"Properties: {properties}")
