import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union
from xml.etree import ElementTree as ET


RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDF_ABOUT = f"{{{RDF_NS}}}about"
RDF_RESOURCE = f"{{{RDF_NS}}}resource"
RDF_NODE_ID = f"{{{RDF_NS}}}nodeID"
VALUE_ATTRS = {
    RDF_ABOUT,
    RDF_RESOURCE,
    RDF_NODE_ID,
}


@dataclass(frozen=True)
class EmptyProperty:
    concept_code: str
    property_name: str

    def __str__(self) -> str:
        return f"{self.concept_code}: empty {self.property_name}"


@dataclass(frozen=True)
class RetiredParentReference:
    concept_code: str
    parent_code: str
    concept_uri: str
    parent_uri: str

    def __str__(self) -> str:
        return f"{self.concept_code}: active concept has retired parent {self.parent_code}"


@dataclass(frozen=True)
class ClassSummary:
    code: str
    uri: str
    deprecated: bool
    parent_refs: List[str]


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


def class_uri(element: ET.Element) -> str:
    return element.attrib.get(RDF_ABOUT) or element.attrib.get(RDF_NODE_ID) or node_id(element)


def is_deprecated_class(element: ET.Element) -> bool:
    for child in element:
        if local_name(child.tag) == "deprecated" and child.text:
            return child.text.strip().lower() == "true"
    return False


def parent_references(element: ET.Element) -> List[str]:
    refs = []
    for child in element:
        if local_name(child.tag) != "subClassOf":
            continue

        resource = child.attrib.get(RDF_RESOURCE)
        if resource:
            refs.append(resource)
            continue

        for nested_child in child:
            if local_name(nested_child.tag) == "Class":
                nested_resource = nested_child.attrib.get(RDF_ABOUT) or nested_child.attrib.get(RDF_RESOURCE)
                if nested_resource:
                    refs.append(nested_resource)
    return refs


def local_reference(reference: str) -> str:
    if not reference:
        return ""

    if "#" in reference:
        return reference.rsplit("#", 1)[1]
    return reference.rsplit("/", 1)[-1]


def is_relative_reference(reference: str) -> bool:
    return reference.startswith("#") or "://" not in reference


def load_class_summaries(owl_file: Union[str, Path]) -> List[ClassSummary]:
    summaries = []
    for _, element in ET.iterparse(owl_file, events=("end",)):
        if local_name(element.tag) == "Class":
            summaries.append(
                ClassSummary(
                    code=concept_code(element),
                    uri=class_uri(element),
                    deprecated=is_deprecated_class(element),
                    parent_refs=parent_references(element),
                )
            )
            element.clear()
    return summaries


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


def find_retired_parent_references(owl_file: Union[str, Path]) -> List[RetiredParentReference]:
    summaries = load_class_summaries(owl_file)
    summaries_by_exact_reference: Dict[str, ClassSummary] = {}
    summaries_by_local_reference: Dict[str, ClassSummary] = {}
    for summary in summaries:
        for key in [summary.uri, summary.code]:
            if key:
                summaries_by_exact_reference.setdefault(key, summary)
                summaries_by_local_reference.setdefault(local_reference(key), summary)

    retired_parent_references = []
    seen_references = set()
    for summary in summaries:
        if summary.deprecated:
            continue
        for parent_ref in summary.parent_refs:
            parent_summary = summaries_by_exact_reference.get(parent_ref)
            if not parent_summary and is_relative_reference(parent_ref):
                parent_summary = summaries_by_local_reference.get(local_reference(parent_ref))
            if not parent_summary or not parent_summary.deprecated:
                continue

            seen_key = (summary.code, parent_summary.code)
            if seen_key in seen_references:
                continue
            seen_references.add(seen_key)
            retired_parent_references.append(
                RetiredParentReference(
                    concept_code=summary.code,
                    parent_code=parent_summary.code,
                    concept_uri=summary.uri,
                    parent_uri=parent_ref,
                )
            )
    return retired_parent_references


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) == 1:
        check = "empty-properties"
        owl_file = args[0]
    elif len(args) == 2:
        check = args[0]
        owl_file = args[1]
    else:
        print("Usage: qa_utils.py [empty-properties|retired-parents|all] <owl-file>")
        return 2

    if check not in {"empty-properties", "retired-parents", "all"}:
        print("Usage: qa_utils.py [empty-properties|retired-parents|all] <owl-file>")
        return 2

    try:
        findings = []
        if check in {"empty-properties", "all"}:
            findings.extend(find_empty_properties(owl_file))
        if check in {"retired-parents", "all"}:
            findings.extend(find_retired_parent_references(owl_file))
    except ET.ParseError as exc:
        print(f"ERROR: unable to parse OWL XML: {exc}")
        return 2

    for finding in findings:
        print(finding)
    return 0


if __name__ == "__main__":
    sys.exit(main())
