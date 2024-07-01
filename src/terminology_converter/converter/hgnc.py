import csv
import getopt
import os
import sys

from terminology_converter.converter.simple_format_utils import get_output_files

THING_URI = "http://www.w3.org/2002/07/owl#Thing"


class Hgnc:
    def __init__(self, definition_file: str, output_directory: str):
        self.definition_file = definition_file
        (
            self.attribute_file,
            self.concepts_file,
            self.parent_child_file,
            _
        ) = get_output_files(output_directory)

    def convert(self):
        with open(self.definition_file, encoding='utf-8-sig') as df, open(
            self.attribute_file, "w"
        ) as af, open(self.concepts_file, "w") as cf, open(
            self.parent_child_file, "w"
        ) as pcf:
            definition_file_reader: list[str] = csv.reader(df, delimiter="\t")
            concepts = []
            attributes = []
            parent_child_relationship = []
            locus_types = set()
            locus_groups = set()
            concept_name_dict = {}
            for index, definition_row in enumerate(definition_file_reader):
                if index == 0:
                    headers = definition_row
                else:
                    hgnc_id = Hgnc.get_hgnc_id(definition_row[headers.index("hgnc_id")])
                    print(f"index:{index}. hgnc_id:{hgnc_id}")
                    name = definition_row[headers.index("name")]
                    concepts.append(
                        "|".join(
                            [hgnc_id, "", name, definition_row[headers.index("symbol")]]
                        )
                    )
                    concept_name_dict[hgnc_id] = name
                    for header in headers:
                        column_value = definition_row[headers.index(header)]
                        if column_value:
                            column_values = column_value.split("|")
                            if header == "locus_type":
                                locus_type = Hgnc.get_locus_type_or_group(column_value)
                                parent_child_relationship.append(
                                    "|".join([locus_type, hgnc_id])
                                )
                                locus_types.add(column_value)
                            if header == "locus_group":
                                locus_group = Hgnc.get_locus_type_or_group(column_value)
                                locus_groups.add(f"{locus_group}_group")
                            [
                                attributes.append(
                                    "|".join(
                                        [
                                            hgnc_id,
                                            header,
                                            cv,
                                        ]
                                    )
                                )
                                for cv in column_values
                            ]
            locus_type_concepts = [
                "|".join([Hgnc.get_locus_type_or_group(locus_type), "", "", ""]) for locus_type in locus_types
            ]
            locus_group_concepts = [
                "|".join([Hgnc.get_locus_type_or_group(locus_group), "", "", ""]) for locus_group in locus_groups
            ]
            locus_group_parent_child = [
                "|".join([THING_URI, Hgnc.get_locus_type_or_group(locus_group)]) for locus_group in locus_groups
            ]
            af.write("\n".join(attributes))
            pcf.write(
                "\n".join([*parent_child_relationship, *locus_group_parent_child])
            )
            cf.write(
                "\n".join([*concepts, *locus_group_concepts, *locus_type_concepts])
            )

    @staticmethod
    def get_locus_type_or_group(column_value: str) -> str:
        return column_value.replace(", ", "_").replace(" ", "_")

    @staticmethod
    def get_hgnc_id(column_value: str) -> str:
        return column_value.replace(":", "_")


def process_args(argv):
    definition_file: str = ""
    output_directory: str = ""
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
                    hgnc.py -d <definition-file> -o <output-file>
                """
            )
            sys.exit()
        elif opt in ("-d", "--definition-file"):
            definition_file = arg
        elif opt in ("-o", "--output-directory"):
            output_directory = arg
    if not definition_file:
        print("Definition file not provided. Exiting")
        sys.exit(1)
    if not output_directory:
        print("Output directory not provided. Exiting")
        sys.exit(1)
    return definition_file, output_directory


if __name__ == "__main__":
    definition_file, output_directory = process_args(sys.argv[1:])
    Hgnc(
        definition_file,
        output_directory,
    ).convert()
