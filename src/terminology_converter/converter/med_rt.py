import getopt
import sys
import lxml.etree as ET

from terminology_converter.converter.simple_format_utils import get_output_files


class MedRt:
    def __init__(self, definition_file: str, output_directory: str):
        self.definition_file = definition_file
        (
            self.attribute_file,
            self.concepts_file,
            self.parent_child_file,
            self.relationships_file
        ) = get_output_files(output_directory)

    def convert(self):
        with open(self.definition_file) as df, open(
                self.attribute_file, "w"
        ) as af, open(self.concepts_file, "w") as cf, open(
            self.parent_child_file, "w"
        ) as pcf, open(
            self.relationships_file, "w"
        ) as rfo:
            definition_file_root: ET = ET.parse(df)
            concept_elements: list[ET] = definition_file_root.findall("./concept")
            concepts = list()
            parent_child = list()
            relationships = list()
            attributes = list()
            concept_name_dict = dict()
            for concept in concept_elements:
                property_elements: list[ET] = concept.findall("./property")
                synonym_elements: list[ET] = concept.findall("./synonym")
                association_elements: list[ET] = concept.findall("./association")
                name = concept.findtext("name")
                status = concept.findtext("status")
                code = get_code(property_elements)
                concepts.append(
                    "|".join(
                        [code, "", "", ""]
                    )
                )
                append_attribute(attributes, code, synonym_elements, property_elements, name, status)
                concept_name_dict[name] = code
                handle_association_elements(association_elements, parent_child, relationships)
            parent_child = fix_parent_child(concept_name_dict, parent_child)
            relationships = fix_relationships(concept_name_dict, relationships)
            cf.write("\n".join(concepts))
            af.write("\n".join(attributes))
            pcf.write(
                "\n".join(parent_child)
            )
            rfo.write(
                "\n".join(relationships)
            )


def get_code(property_elements: list[ET]) -> str:
    return [property_element for property_element in property_elements if
            property_element.findtext("name") == "NUI"][
        0].findtext("value")


def handle_association_elements(association_elements: list[ET], parent_child: list[str], relationships: list[str]):
    for association_element in association_elements:
        if association_element.findtext("from_namespace") == "MED-RT" and association_element.findtext(
                "to_namespace") == "MED-RT":
            from_name = association_element.findtext("from_name")
            to_name = association_element.findtext("to_name")
            association_name = association_element.findtext("name")
            if association_name == "Parent Of":
                parent_child.append("|".join([from_name, to_name]))
            elif association_name == "Child Of":
                continue
            else:
                relationships.append(
                    "|".join(
                        [
                            from_name,
                            "true",
                            "",
                            "",
                            association_name,
                            to_name,
                        ]
                    )
                )


def append_attribute(attributes: list[str], code, synonym_elements: list[ET], property_elements: list[ET], name: str,
                     status: str):
    [
        attributes.append(
            "|".join(
                [
                    code,
                    synonym_element.findtext("name"),
                    synonym_element.findtext("to_name"),
                ]
            )
        ) for synonym_element in synonym_elements
    ]
    [
        attributes.append(
            "|".join(
                [
                    code,
                    property_element.findtext("name"),
                    property_element.findtext("value"),
                ]
            )
        ) for property_element in property_elements
    ]
    attributes.append(
        "|".join(
            [
                code,
                "Concept_Name",
                name,
            ]
        )
    )
    attributes.append(
        "|".join(
            [
                code,
                "Status",
                status,
            ]
        )
    )


def fix_parent_child(concept_name_dict: dict, parent_child: list[str]):
    converted_list = list()
    for row in parent_child:
        parts = row.split("|")
        converted_list.append("|".join([concept_name_dict[parts[0]], concept_name_dict[parts[1]]]))
    return converted_list


def fix_relationships(concept_name_dict: dict, relationships: list[str]):
    converted_list = list()
    for row in relationships:
        parts = row.split("|")
        converted_row = parts.copy()
        converted_row[0] = concept_name_dict[parts[0]]
        converted_row[5] = concept_name_dict[parts[5]]
        converted_list.append("|".join(converted_row))
    return converted_list


def process_args(argv):
    def_file: str = ""
    out: str = ""
    opts, args = getopt.getopt(
        argv,
        "hd:o:",
        ["help", "definition-file=", "output-directory="],
    )
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(
                """
                    Usage: 
                    med_rt.py -d <definition-file> -o <output-file>
                """
            )
            sys.exit()
        elif opt in ("-d", "--definition-file"):
            def_file = arg
        elif opt in ("-o", "--output-directory"):
            out = arg
    if not def_file:
        print("Definition file not provided. Exiting")
        sys.exit(1)
    if not out:
        print("Output directory not provided. Exiting")
        sys.exit(1)
    return def_file, out


if __name__ == "__main__":
    dfile, o = process_args(sys.argv[1:])
    MedRt(
        dfile,
        o,
    ).convert()
