import os


def get_output_files(output_directory: str):
    attributes_file = os.path.join(output_directory, "attributes.txt")
    concepts_file = os.path.join(output_directory, "concepts.txt")
    parent_child_file = os.path.join(output_directory, "parChd.txt")
    relationships_file = os.path.join(output_directory, "relationships.txt")
    return attributes_file, concepts_file, parent_child_file, relationships_file
