import csv
import getopt
import sys
import xml.etree.ElementTree as ET
from typing import Union

from terminology_converter.models.terminology import (
    Concept,
    Attribute,
    ParentChild,
    Relationship,
)

RDF_PREFIX = "rdf"
OWL_PREFIX = "owl"
RDFS_PREFIX = "rdfs"


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
    with open(f"{simple_files_directory}/{file_name}") as file:
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
    return objects


class OwlConverter:
    def __init__(
        self,
        base_url: str,
        version: str,
        simple_files_directory: str,
        output_directory: str,
    ):
        self.base_url: str = base_url
        self.version: str = version
        self.concepts: list[Concept] = load_concepts(simple_files_directory)
        self.attributes: list[Attribute] = load_file(
            simple_files_directory, "attributes.txt", Attribute
        )
        self.parent_children: list[ParentChild] = load_file(
            simple_files_directory, "parChd.txt", ParentChild
        )
        self.relationships: list[Relationship] = load_file(
            simple_files_directory, "relationships.txt", Relationship
        )
        self.output_directory = output_directory

    def convert(self):
        root = ET.Element(
            "rdf:RDF",
            {
                "xmlns": self.base_url,
                f"xmlns:{RDF_PREFIX}": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                f"xmlns:{OWL_PREFIX}": "http://www.w3.org/2002/07/owl#",
                "xmlns:xml": "http://www.w3.org/XML/1998/namespace",
                "xmlns:xsd": "http://www.w3.org/2001/XMLSchema#",
                f"xmlns:{RDFS_PREFIX}": "http://www.w3.org/2000/01/rdf-schema#",
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
        tree.write(f"{self.output_directory}/umls.owl")

    def write_metadata(self, root: ET.Element):
        self.write_annotation_properties(root)
        self.write_object_properties(root)

    def write_annotation_properties(self, root: ET.Element):
        attribute_types = set(map(lambda a: a.attribute_type, self.attributes))
        annotation_properties = [
            "Code",
            "Semantic_Type",
            "Preferred_Name",
            "Synonym",
            *attribute_types,
        ]
        for annotation_property in annotation_properties:
            annotation_property_element = self.create_element_with_label(
                "AnnotationProperty", annotation_property
            )
            root.append(annotation_property_element)

    def write_object_properties(self, root: ET.Element):
        relationship_types = set(map(lambda r: r.additional_type, self.relationships))
        for relationship_type in relationship_types:
            object_property_element = self.create_element_with_label(
                "ObjectProperty", relationship_type
            )
            root.append(object_property_element)

    def write_class(self, root: ET.Element):
        for concept in self.concepts:
            class_element: ET.Element = self.create_element("Class", concept.code)
            parents = set(
                map(
                    lambda pc: pc.parent,
                    [
                        parent_child
                        for parent_child in self.parent_children
                        if parent_child.child == concept.code
                    ],
                )
            )
            attributes = [
                attribute
                for attribute in self.attributes
                if attribute.code == concept.code
            ]
            relationships = [
                relationship
                for relationship in self.relationships
                if relationship.code == concept.code
            ]
            for parent in parents:
                subclass_element: ET.Element = self.create_element_with_resource(
                    "subClassOf", parent, RDFS_PREFIX
                )
                class_element.append(subclass_element)
            self.append_class_element(class_element, "Code", concept.code)
            self.append_class_element(
                class_element, "Semantic_Type", concept.semantic_type
            )
            self.append_class_element(
                class_element, "Preferred_Name", concept.preferred_name
            )
            for synonym in concept.synonyms:
                self.append_class_element(class_element, "Synonym", synonym)
            for attribute in attributes:
                self.append_class_element(
                    class_element, attribute.attribute_type, attribute.value
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
            {f"{RDF_PREFIX}:resource": f"{self.base_url}#{label}"},
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
        label_element = ET.Element(f"{RDFS_PREFIX}:label")
        label_element.text = label
        element.append(label_element)
        return element


def process_args(argv):
    terminology_url: str = ""
    version: str = ""
    input_directory: str = ""
    output_directory: str = ""
    opts, args = getopt.getopt(
        argv,
        "hu:v:i:o:",
        [
            "help",
            "terminology-url=",
            "version=",
            "input-directory",
            "output-directory=",
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
    return terminology_url, version, input_directory, output_directory


if __name__ == "__main__":
    terminology_url, version, input_directory, output_directory = process_args(
        sys.argv[1:]
    )
    OwlConverter(
        terminology_url,
        version,
        input_directory,
        output_directory,
    ).convert()
