import csv
import getopt
import os
import sys

from terminology_converter.converter.simple_format_utils import get_output_files

SEMANTIC_RECORD_TYPE = "STY"
SEMANTIC_TREE_NUMBER = "STN"
RELATIONSHIP_TREE_NUMBER = "RTN"


class UmlsSemanticNetwork:
    def __init__(
            self, definition_file: str, inferred_relationship_file: str, stated_relationship_file: str,
            output_directory: str
    ):
        self.definition_file = definition_file
        self.inferred_relationship_file = inferred_relationship_file
        self.stated_relationship_file = stated_relationship_file
        (
            self.attribute_file,
            self.concepts_file,
            self.parent_child_file,
            self.relationships_file,
        ) = get_output_files(output_directory)

    def convert(self):
        with open(self.definition_file, encoding='utf-8-sig') as def_file, open(self.inferred_relationship_file,
                                                                                encoding='utf-8-sig') as inf_rel_file, open(
                self.stated_relationship_file, encoding='utf-8-sig') as sta_ref_file, open(
            self.attribute_file, "w"
        ) as af, open(self.concepts_file, "w") as cf, open(
            self.parent_child_file, "w"
        ) as pcf, open(
            self.relationships_file, "w"
        ) as rfo:
            definition_file_reader = csv.reader(def_file, delimiter="|")
            inferred_relationship_file_reader = csv.reader(inf_rel_file, delimiter="|")
            stated_relationship_file_reader = csv.reader(sta_ref_file, delimiter="|")
            concepts = []
            attributes = []
            parent_child_relationship = []
            parent_child_code = ""
            relationships = []
            concept_name_dict = {}
            concept_id_dict = {}
            for definition_row in definition_file_reader:
                (
                    record_type,
                    unique_identifier,
                    name,
                    tree_number,
                    definition,
                    examples,
                    usage_note,
                    non_human_flag,
                    abbreviation,
                    relation_inverse,
                    _,
                ) = definition_row
                concepts.append(
                    "|".join([unique_identifier, record_type, name, abbreviation])
                )
                concept_name_dict[unique_identifier] = name
                concept_id_dict[name] = unique_identifier
                if UmlsSemanticNetwork.has_value(tree_number):
                    attributes.append(
                        "|".join(
                            [
                                unique_identifier,
                                UmlsSemanticNetwork.get_tree_number_label(record_type),
                                tree_number,
                            ]
                        )
                    )
                if UmlsSemanticNetwork.has_value(definition):
                    attributes.append("|".join([unique_identifier, "DEF", definition]))
                if UmlsSemanticNetwork.has_value(examples):
                    attributes.append("|".join([unique_identifier, "EX", examples]))
                if UmlsSemanticNetwork.has_value(usage_note):
                    attributes.append("|".join([unique_identifier, "UN", usage_note]))
                if UmlsSemanticNetwork.has_value(non_human_flag):
                    attributes.append(
                        "|".join([unique_identifier, "NH", non_human_flag])
                    )
                if UmlsSemanticNetwork.has_value(relation_inverse):
                    attributes.append(
                        "|".join([unique_identifier, "RI", relation_inverse])
                    )
                if name == "isa":
                    parent_child_code = unique_identifier
            for relationship_row in inferred_relationship_file_reader:
                left_code, relationship_code, right_code, _ = relationship_row
                # Ignore isa relationships. We will use the stated relationship file to determine that
                if relationship_code != parent_child_code:
                    relationships.append(
                        "|".join(
                            [
                                left_code,
                                "true",
                                "",
                                "",
                                relationship_code,
                                right_code,
                            ]
                        )
                    )
            for relationship_row in stated_relationship_file_reader:
                left_code, relationship_code, right_code = relationship_row[:3]
                if relationship_code == "isa" and right_code and left_code:
                    parent_child_relationship.append("|".join([concept_id_dict[right_code], concept_id_dict[left_code]]))
            af.write("\n".join(attributes))
            cf.writelines("\n".join(concepts))
            pcf.writelines("\n".join(parent_child_relationship))
            rfo.writelines("\n".join(relationships))

    @staticmethod
    def is_semantic_type(record_type: str) -> bool:
        return record_type == SEMANTIC_RECORD_TYPE

    @staticmethod
    def get_tree_number_label(record_type: str) -> str:
        return (
            SEMANTIC_TREE_NUMBER
            if UmlsSemanticNetwork.is_semantic_type(record_type)
            else RELATIONSHIP_TREE_NUMBER
        )

    @staticmethod
    def has_value(value: str) -> bool:
        return value and not "NULL" == value


def process_args(argv):
    def_file: str = ""
    inf_rel_file: str = ""
    sta_rel_file: str = ""
    out_directory: str = ""
    opts, args = getopt.getopt(
        argv,
        "hd:i:s:o:",
        ["help", "definition-file=", "inferred-relationship-file=", "output-directory="],
    )
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(
                """
                    Usage: 
                    umls_sem_net.py -d <definition-file> -r <relationship-file> -o <output-file>
                """
            )
            sys.exit()
        elif opt in ("-d", "--definition-file"):
            def_file = arg
        elif opt in ("-i", "--inferred-relationship-file"):
            inf_rel_file = arg
        elif opt in ("-s", "--stated-relationship-file"):
            sta_rel_file = arg
        elif opt in ("-o", "--output-directory"):
            out_directory = arg
    if not def_file:
        print("Definition file not provided. Exiting")
        sys.exit(1)
    if not inf_rel_file:
        print("Inferred relationship file not provided. Exiting")
        sys.exit(1)
    if not sta_rel_file:
        print("Stated relationship file not provided. Exiting")
        sys.exit(1)
    if not out_directory:
        print("Output directory not provided. Exiting")
        sys.exit(1)
    return def_file, inf_rel_file, sta_rel_file, out_directory


if __name__ == "__main__":
    df, irf, srf, od = process_args(sys.argv[1:])
    UmlsSemanticNetwork(
        df,
        irf,
        srf,
        od,
    ).convert()
