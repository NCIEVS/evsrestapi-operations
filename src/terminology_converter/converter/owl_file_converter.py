import csv
import getopt
import os
import sys
import xml.etree.ElementTree as ET
from typing import Union
import logging
from datetime import datetime

log = logging.getLogger(__name__)
THING_URI = "http://www.w3.org/2002/07/owl#Thing"

from terminology_converter.models.terminology import (
    Concept,
    Attribute,
    ParentChild,
    Relationship,
)

RDF_PREFIX = "rdf"
RDF_URL = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
OWL_PREFIX = "owl"
OWL_URL = "http://www.w3.org/2002/07/owl#"
RDFS_PREFIX = "rdfs"
RDFS_URL = "http://www.w3.org/2000/01/rdf-schema#"
XML_URL = "http://www.w3.org/XML/1998/namespace"
XSD_URL = "http://www.w3.org/2001/XMLSchema#"


def load_concepts(simple_files_directory: str) -> list[Concept]:
    concepts = []
    with open(f"{simple_files_directory}/concepts.txt") as concepts_file:
        concepts_file_reader = csv.reader(concepts_file, delimiter="|")
        for code, semantic_type, preferred_name, *synonyms in concepts_file_reader:
            concepts.append(
                Concept(
                    code=code,
                    semantic_type=semantic_type,
                    preferred_name=preferred_name,
                    synonyms=synonyms,
                )
            )
    return concepts


def load_file(
        simple_files_directory: str, file_name: str, class_name
) -> list[Union[Attribute, ParentChild, Relationship]]:
    objects = []
    str_path = f"{simple_files_directory}/{file_name}"
    if os.path.exists(str_path):
        with open(str_path) as file:
            file_reader = csv.reader(file, delimiter="|")
            for line in file_reader:
                objects.append(
                    class_name(
                        **{
                            key: line[i]
                            for i, key in enumerate(class_name.__fields__.keys())
                        }
                    )
                )
    else:
        log.warning(f"{str_path} does not exist")
    return objects


class OwlConverter:
    def __init__(
            self,
            base_url: str,
            version: str,
            simple_files_directory: str,
            output_directory: str,
            terminology: str,
    ):
        self.base_url: str = base_url
        self.version: str = version
        self.concepts: list[Concept] = load_concepts(simple_files_directory)
        self.concepts_by_code: dict[str, Concept] = {c.code: c for c in self.concepts}
        self.has_semantic_type: bool = any(
            concept.semantic_type for concept in self.concepts
        )
        self.attributes = {}
        attributes: list[Attribute] = load_file(
            simple_files_directory, "attributes.txt", Attribute
        )

        for attribute in attributes:
            self.attributes.setdefault(attribute.code, []).append(attribute)
        lst_parent_children: list[ParentChild] = load_file(
            simple_files_directory, "parChd.txt", ParentChild
        )
        self.parent_children = {}
        for parent_child in lst_parent_children:
            self.parent_children.setdefault(parent_child.child, []).append(parent_child)

        self.relationships: list[Relationship] = load_file(
            simple_files_directory, "relationships.txt", Relationship
        )
        self.output_directory = output_directory
        self.terminology = terminology

    def convert(self):
        root = ET.Element(
            "rdf:RDF",
            {
                "xmlns": self.base_url + "#",
                "xml:base": self.base_url,
                f"xmlns:{RDF_PREFIX}": RDF_URL,
                f"xmlns:{OWL_PREFIX}": OWL_URL,
                "xmlns:xml": XML_URL,
                "xmlns:xsd": XSD_URL,
                f"xmlns:{RDFS_PREFIX}": RDFS_URL,
                f"xmlns:{self.terminology.upper()}": self.base_url + "#"
            },
        )
        ontology = ET.Element(
            f"{OWL_PREFIX}:Ontology", {f"{RDF_PREFIX}:about": self.base_url}
        )
        version = ET.Element(f"{OWL_PREFIX}:versionInfo")
        version.text = self.version
        ontology.append(version)
        root.append(ontology)
        self.write_metadata(root)
        self.write_class(root)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ", level=0)
        tree.write(f"{self.output_directory}/{self.terminology}.owl")

    def write_metadata(self, root: ET.Element):
        self.write_annotation_properties(root)
        self.write_object_properties(root)

    def flatten_concatenation(self, matrix):
        flat_list = []
        for row in matrix:
            flat_list += row
        return flat_list

    def write_annotation_properties(self, root: ET.Element):
        lst_attributes = self.flatten_concatenation(self.attributes.values())
        attribute_types = set(map(lambda a: a.attribute_type, lst_attributes))
        annotation_properties = [
            "Code",
            "Preferred_Name",
            "Synonym",
            *[transform_attribute_type(attribute_type) for attribute_type in attribute_types if
              ":" not in attribute_type],
        ]
        annotation_properties.sort()
        if self.has_semantic_type:
            annotation_properties.insert(1, "Semantic_Type")
        for annotation_property in annotation_properties:
            annotation_property_element = self.create_element_with_label(
                "AnnotationProperty", annotation_property
            )
            root.append(annotation_property_element)

    def write_object_properties(self, root: ET.Element):
        relationship_types = set(map(lambda r: r.additional_type, self.relationships))
        for relationship_type in relationship_types:
            object_property_concept = self.concepts_by_code.get(relationship_type, None)
            if object_property_concept:
                object_property_element: ET.Element = self.create_element("ObjectProperty",
                                                                          object_property_concept.code)
                parent_children_for_code = self.parent_children.get(object_property_concept.code, [])
                attributes = self.attributes.get(object_property_concept.code, [])
                relationships = [
                    relationship
                    for relationship in self.relationships
                    if relationship.code == object_property_concept.code
                ]
                for parent_child in parent_children_for_code:
                    subclass_element: ET.Element = self.create_element_with_resource(
                        "subObjectPropertyOf", parent_child.parent, OWL_PREFIX
                    )
                    object_property_element.append(subclass_element)
                self.append_label_element(object_property_element, object_property_concept.preferred_name)
                self.append_class_element(object_property_element, "Code", object_property_concept.code)
                self.append_class_element(
                    object_property_element, "Semantic_Type", object_property_concept.semantic_type
                )
                self.append_class_element(
                    object_property_element, "Preferred_Name", object_property_concept.preferred_name
                )
                for synonym in object_property_concept.synonyms:
                    self.append_class_element(object_property_element, "Synonym", synonym)
                for attribute in attributes:
                    self.append_class_element(
                        object_property_element, attribute.attribute_type, attribute.value
                    )
                for relationship in relationships:
                    self.append_class_relationship(object_property_element, relationship)
            else:
                object_property_element = self.create_element_with_label(
                    "ObjectProperty", relationship_type
                )

            root.append(object_property_element)

    def write_class(self, root: ET.Element):
        for concept in self.concepts:
            print(f"Processing {concept}")
            class_element: ET.Element = self.create_element("Class", concept.code)
            parent_children_for_code = self.parent_children.get(concept.code, [])
            attributes = self.attributes.get(concept.code, [])
            relationships = [
                relationship
                for relationship in self.relationships
                if relationship.code == concept.code
            ]
            for parent_child in parent_children_for_code:
                subclass_element: ET.Element = self.create_element_with_resource(
                    "subClassOf", parent_child.parent, RDFS_PREFIX
                )
                class_element.append(subclass_element)
            self.append_class_element(class_element, "Code", concept.code)
            if concept.semantic_type:
                self.append_class_element(
                    class_element, "Semantic_Type", concept.semantic_type
                )
            if concept.preferred_name:
                self.append_class_element(
                    class_element, "Preferred_Name", concept.preferred_name
                )
            for synonym in concept.synonyms:
                if len(synonym) > 0:
                    self.append_class_element(class_element, "Synonym", synonym)
            for attribute in attributes:
                self.append_class_element(
                    class_element, transform_attribute_type(attribute.attribute_type), attribute.value
                )
            for relationship in relationships:
                self.append_class_relationship(class_element, relationship)
            root.append(class_element)

    def create_element(self, element_name: str, label: str):
        return ET.Element(
            f"{OWL_PREFIX}:{element_name}",
            {f"{RDF_PREFIX}:about": f"{self.base_url}#{label}"},
        )

    def create_element_with_resource(
            self, element_name: str, label: str, element_prefix: str = OWL_PREFIX
    ):
        return ET.Element(
            f"{element_prefix}:{element_name}",
            {f"{RDF_PREFIX}:resource": f"{self.base_url}#{label}" if not label == THING_URI else THING_URI},
        )

    def append_class_element(
            self, class_element: ET.Element, element_name: str, value: str
    ):
        code_element: ET.Element = ET.Element(element_name)
        code_element.text = value
        class_element.append(code_element)

    def append_class_relationship(
            self, class_element: ET.Element, relationship: Relationship
    ):
        subclass_element: ET.Element = ET.Element(f"{RDFS_PREFIX}:subClassOf")
        restriction_element: ET.Element = ET.Element(f"{OWL_PREFIX}:Restriction")
        on_property_element: ET.Element = self.create_element_with_resource(
            "onProperty", relationship.additional_type
        )
        some_values_from_element: ET.Element = self.create_element_with_resource(
            "someValuesFrom", relationship.target_code
        )
        restriction_element.append(on_property_element)
        restriction_element.append(some_values_from_element)
        subclass_element.append(restriction_element)
        class_element.append(subclass_element)

    def create_element_with_label(self, element_name: str, label: str):
        element: ET.Element = ET.Element(
            f"{OWL_PREFIX}:{element_name}",
            {f"{RDF_PREFIX}:about": f"{self.base_url}#{label}"},
        )
        self.append_label_element(element, label)
        return element

    def append_label_element(self, element: ET.Element, label: str):
        label_element = ET.Element(f"{RDFS_PREFIX}:label")
        label_element.text = label
        element.append(label_element)


def process_args(argv):
    terminology_url: str = ""
    version: str = ""
    input_directory: str = ""
    output_directory: str = ""
    opts, args = getopt.getopt(
        argv,
        "hu:v:i:o:t:",
        [
            "help",
            "terminology-url=",
            "version=",
            "input-directory",
            "output-directory=",
            "terminology=",
        ],
    )
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(
                """
                    Usage: 
                    owl_file_converter.py -u <terminology-url> -v <version> -i <input-file> -o <output-file>
                """
            )
            sys.exit()
        elif opt in ("-u", "--terminology-url"):
            terminology_url = arg
        elif opt in ("-v", "--version"):
            version = arg
        elif opt in ("-i", "--input-directory"):
            input_directory = arg
        elif opt in ("-o", "--output-directory"):
            output_directory = arg
        elif opt in ("-t", "--terminology"):
            terminology = arg
    if not terminology_url:
        print("Terminology URL not provided. Exiting")
        sys.exit(1)
    if not version:
        print("Version not provided. Exiting")
        sys.exit(1)
    if not input_directory:
        print("Input directory not provided. Exiting")
        sys.exit(1)
    if not output_directory:
        print("Output directory not provided. Exiting")
        sys.exit(1)
    return terminology_url, version, input_directory, output_directory, terminology


def transform_attribute_type(attribute_type: str) -> str:
    return attribute_type.replace(" ", "_")


if __name__ == "__main__":
    (
        terminology_url,
        version,
        input_directory,
        output_directory,
        terminology,
    ) = process_args(sys.argv[1:])
    OwlConverter(
        terminology_url, version, input_directory, output_directory, terminology
    ).convert()
