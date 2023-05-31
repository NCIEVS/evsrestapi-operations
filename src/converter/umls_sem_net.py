import csv
import os

SEMANTIC_RECORD_TYPE = "STY"
SEMANTIC_TREE_NUMBER = "STN"
RELATIONSHIP_TREE_NUMBER = "RTN"


class UmlsSemanticNetwork:
    def __init__(
            self, definition_file: str, relationship_file: str, output_directory: str
    ):
        self.definition_file = definition_file
        self.relationship_file = relationship_file
        (
            self.attribute_file,
            self.concepts_file,
            self.parent_child_file,
            self.relationships_file,
        ) = UmlsSemanticNetwork.get_output_files(output_directory)

    def convert(self):
        with open(self.definition_file) as df, open(self.relationship_file) as rf, open(
                self.attribute_file, "w"
        ) as af, open(self.concepts_file, "w") as cf, open(
            self.parent_child_file, "w"
        ) as pcf, open(
            self.relationships_file, "w"
        ) as rfo:
            definition_file_reader = csv.reader(df, delimiter="|")
            relationship_file_reader = csv.reader(rf, delimiter="|")
            concepts = []
            attributes = []
            parent_child_relationship = []
            parent_child_code = ""
            relationships = []
            concept_name_dict = {}
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
            for relationship_row in relationship_file_reader:
                left_code, relationship_code, right_code, _ = relationship_row
                if relationship_code == parent_child_code:
                    parent_child_relationship.append("|".join([right_code, left_code]))
                else:
                    relationships.append(
                        "|".join(
                            [
                                left_code,
                                "true",
                                "",
                                "",
                                concept_name_dict[relationship_code],
                                right_code,
                            ]
                        )
                    )
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

    @staticmethod
    def get_output_files(output_directory: str):
        attributes_file = os.path.join(output_directory, "attributes.txt")
        concepts_file = os.path.join(output_directory, "concepts.txt")
        parent_child_file = os.path.join(output_directory, "parChd.txt")
        relationships_file = os.path.join(output_directory, "relationships.txt")
        return attributes_file, concepts_file, parent_child_file, relationships_file


if __name__ == '__main__':
    UmlsSemanticNetwork(
        "/Users/squareroot/Documents/wci/loading-terminologies/UmlsSemNet/SRDEF",
        "/Users/squareroot/Documents/wci/loading-terminologies/UmlsSemNet/SRSTRE1",
        "/Users/squareroot/temp",
    ).convert()
