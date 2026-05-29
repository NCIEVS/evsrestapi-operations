import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Union
from xml.etree import ElementTree as ET


RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
VALUE_ATTRS = {
    f"{{{RDF_NS}}}about",
    f"{{{RDF_NS}}}resource",
    f"{{{RDF_NS}}}nodeID",
}


@dataclass(frozen=True)
class EmptyProperty:
    concept_code: str
    property_name: str

    def __str__(self) -> str:
        return f"{self.concept_code}: empty {self.property_name}"


def local_name(tag: str) -> str:
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[1]
    return tag.split(":", 1)[-1]


def node_id(element: ET.Element) -> str:
    for attr in VALUE_ATTRS:
        value = element.attrib.get(attr)
        if value:
            return value
    return "<unknown class>"


def concept_code(element: ET.Element) -> str:
    for child in element:
        if local_name(child.tag) == "NHC0" and child.text and child.text.strip():
            return child.text.strip()
    return node_id(element)


def is_empty_property(element: ET.Element) -> bool:
    if len(element) != 0:
        return False
    if element.text and element.text.strip():
        return False
    return not any(element.attrib.get(attr) for attr in VALUE_ATTRS)


def find_empty_properties(owl_file: Union[str, Path]) -> List[EmptyProperty]:
    empty_properties = []
    for _, element in ET.iterparse(owl_file, events=("end",)):
        if local_name(element.tag) != "Class":
            continue

        code = concept_code(element)
        for child in element:
            if is_empty_property(child):
                empty_properties.append(EmptyProperty(code, local_name(child.tag)))
        element.clear()
    return empty_properties


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1:
        print("Usage: qa_utils.py <owl-file>")
        return 2

    try:
        empty_properties = find_empty_properties(args[0])
    except ET.ParseError as exc:
        print(f"ERROR: unable to parse OWL XML: {exc}")
        return 2

    for empty_property in empty_properties:
        print(empty_property)
    return 0


if __name__ == "__main__":
    sys.exit(main())
