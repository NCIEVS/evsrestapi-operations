import csv
import dataclasses
import getopt
import re
import sys
from typing import TextIO, Callable

from terminology_converter.converter.simple_format_utils import get_output_files

# HCPCS constants
HCPCS_CODE = "HCPCS"
GENERIC_NAME = "Generic Name"
BRAND_NAME = "Brand Name"
STRENGTH = "Strength"
CATEGORY = "SEER*Rx Category"
MAJOR_DRUG_CLASS = "Major Drug Class"
MINOR_DRUG_CLASS = "Minor Drug Class"
ORAL = "Oral (Y/N)"

NON_ATTRIBUTE_HEADERS = [GENERIC_NAME, CATEGORY, MINOR_DRUG_CLASS, MAJOR_DRUG_CLASS]

# NDC constants
NDC_PACKAGE = "NDC-11 (Package)"
NDC_PRODUCT = "NDC-9 (Product)"
PACKAGE_EFFECTIVE_DATE = "Package Effective Date"
PACKAGE_DISCONTINUATION_DATE = "Package Discontinuation Date"
NDC_MAJOR_DRUG_CLASS = "Major Class"
NDC_MINOR_DRUG_CLASS = "Minor Class"
ADMINISTRATION_ROUTE = "Administration Route"

NDC_NON_ATTRIBUTE_HEADERS = [CATEGORY, NDC_MINOR_DRUG_CLASS, NDC_MAJOR_DRUG_CLASS]
NDC_PRODUCT_ATTRIBUTES = [GENERIC_NAME, BRAND_NAME, NDC_PRODUCT, ADMINISTRATION_ROUTE]

HCPCS_ROOT_CLASS = "HCPCS"
NDC_ROOT_CLASS = "NDC"


class CanmedData:
    concepts: set[str]
    products: set[str]
    attributes: set[str]
    parent_child_relationship: set[str]
    generic_code_classes: set[str]
    minor_drug_classes: set[str]
    major_drug_classes: set[str]
    categories: set[str]

    def __init__(self):
        self.concepts = set()
        self.attributes = set()
        self.parent_child_relationship = set()
        self.generic_code_classes = set()
        self.minor_drug_classes = set()
        self.major_drug_classes = set()
        self.categories = set()
        self.products = set()


class Canmed:
    def __init__(self, hcpcs_file: str, ndconc_file: str, output_directory: str):
        self.hcpcs_file = hcpcs_file
        self.ndconc_file = ndconc_file
        (
            self.attribute_file,
            self.concepts_file,
            self.parent_child_file,
            self.relationships_file
        ) = get_output_files(output_directory)

    def convert(self):
        with open(self.hcpcs_file) as hf, open(self.ndconc_file) as nf:
            hcpcs_file_reader: list[str] = csv.reader(hf, delimiter=",")
            ndconc_file_reader: list[str] = csv.reader(nf, delimiter=",")
            hcpcs_data = Canmed._handle_hcpcs_file(hcpcs_file_reader)
            ndconc_data = Canmed._handle_ndc_file(ndconc_file_reader)
            self.write_files(hcpcs_data, ndconc_data)

    def write_files(self, hcpcs_data: CanmedData, ndconc_data: CanmedData):
        with open(
                self.attribute_file, "w"
        ) as af, open(self.concepts_file, "w") as cf, open(
            self.parent_child_file, "w"
        ) as pcf:
            parent_concepts = [
                "|".join([generic_code_class, "", "", ""]) for generic_code_class in
                [*ndconc_data.products, *hcpcs_data.generic_code_classes, *ndconc_data.generic_code_classes,
                 *hcpcs_data.minor_drug_classes, *ndconc_data.minor_drug_classes, *hcpcs_data.major_drug_classes,
                 *ndconc_data.major_drug_classes, *hcpcs_data.categories, *ndconc_data.categories]
            ]
            af.write("\n".join([*hcpcs_data.attributes, *ndconc_data.attributes]))
            pcf.write(
                "\n".join([*hcpcs_data.parent_child_relationship, *ndconc_data.parent_child_relationship])
            )
            cf.write(
                "\n".join({*hcpcs_data.concepts, *ndconc_data.concepts, *parent_concepts})
            )

    @staticmethod
    def _handle_hcpcs_file(hf: TextIO) -> CanmedData:
        data = CanmedData()
        for index, definition_row in enumerate(hf):
            if index == 0:
                headers = definition_row
            else:
                code = definition_row[headers.index("HCPCS")]
                generic_name = definition_row[headers.index(GENERIC_NAME)]
                print(f"index:{index}. code:{code}")
                name = Canmed.get_name(generic_name,
                                       definition_row[headers.index("Strength")])
                if code == "NA" or code == "Not yet assigned":
                    code = Canmed.get_generic_code("HCPCS", name)
                data.concepts.add(
                    "|".join(
                        [code, "", name, ""]
                    )
                )
                Canmed.populate_parent_child(definition_row, headers, data, code, None, GENERIC_NAME, MINOR_DRUG_CLASS,
                                             MAJOR_DRUG_CLASS,
                                             HCPCS_ROOT_CLASS)
                Canmed.populate_attributes(definition_row, headers, data, code, Canmed.get_hcpcs_attribute_name,
                                           NON_ATTRIBUTE_HEADERS)
        return data

    @staticmethod
    def _handle_ndc_file(nf: TextIO) -> CanmedData:
        data = CanmedData()
        for index, definition_row in enumerate(nf):
            if index == 0:
                headers = definition_row
            else:
                code = definition_row[headers.index(NDC_PACKAGE)]
                product_code = Canmed.get_generic_code_non_standardized(NDC_ROOT_CLASS,
                                                                        definition_row[headers.index(NDC_PRODUCT)])
                code = Canmed.get_generic_code_non_standardized(NDC_ROOT_CLASS, code)
                generic_name = definition_row[headers.index(GENERIC_NAME)]

                print(f"index:{index}. code:{code}")
                name = Canmed.get_name(generic_name,
                                       definition_row[headers.index("Strength")])
                data.concepts.add(
                    "|".join(
                        [code, "", name, ""]
                    )
                )
                Canmed.populate_parent_child(definition_row, headers, data, code, NDC_PRODUCT, GENERIC_NAME,
                                             NDC_MINOR_DRUG_CLASS,
                                             NDC_MAJOR_DRUG_CLASS, NDC_ROOT_CLASS)
                Canmed.populate_attributes(definition_row, headers, data, code, Canmed.get_ndc_attribute_name,
                                           NDC_NON_ATTRIBUTE_HEADERS, product_code)
        return data

    @staticmethod
    def get_name(generic_name: str, strength: str) -> str:
        return " ".join([generic_name, strength])

    @staticmethod
    def get_hcpcs_attribute_name(header: str) -> str:
        if header == HCPCS_CODE:
            return "HCPCS_Code"
        if header == ORAL:
            return "Oral"
        return header

    @staticmethod
    def get_ndc_attribute_name(header: str) -> str:
        if header == NDC_PACKAGE:
            return "NDC_Package_Code"
        if header == NDC_PRODUCT:
            return "NDC_Product_Code"
        if header == PACKAGE_EFFECTIVE_DATE:
            return "Effective_Date"
        if header == PACKAGE_DISCONTINUATION_DATE:
            return "Discontinue_Date"
        return header

    @staticmethod
    def get_generic_code(code_type: str, code: str) -> str:
        return f"{code_type}_{Canmed.get_standardized_code(code)}"

    @staticmethod
    def get_generic_code_non_standardized(code_type: str, code: str) -> str:
        return f"{code_type}_{code}"

    @staticmethod
    def get_standardized_code(name: str):
        first = re.sub('[^0-9a-zA-Z./]+', '_', name).upper()
        return first.replace("/", "-")

    @staticmethod
    def populate_parent_child(definition_row, headers, data, code: str, product_header: str, generic_name_header: str,
                              minor_drug_class_header: str,
                              major_drug_class_header: str, code_type: str):
        product_code = ""
        if product_header:
            product_code = Canmed.get_generic_code_non_standardized(code_type, definition_row[headers.index(product_header)])
            data.products.add(product_code)
            data.parent_child_relationship.add(
                "|".join([product_code, code])
            )
        generic_name = definition_row[headers.index(generic_name_header)]
        generic_code = Canmed.get_generic_code(code_type, generic_name)
        data.generic_code_classes.add(generic_code)
        data.parent_child_relationship.add(
            "|".join([generic_code, product_code if product_header else code])
        )
        minor_drug_code = ""
        major_drug_code = ""
        minor_drug_class = definition_row[headers.index(minor_drug_class_header)]
        if minor_drug_class:
            minor_drug_code = Canmed.get_generic_code(code_type, minor_drug_class)
            data.minor_drug_classes.add(minor_drug_code)
            data.parent_child_relationship.add(
                "|".join([minor_drug_code, generic_code])
            )
        major_drug_class = definition_row[headers.index(major_drug_class_header)]
        if major_drug_class:
            major_drug_code = Canmed.get_generic_code(code_type, major_drug_class)
            data.major_drug_classes.add(major_drug_code)
        category = definition_row[headers.index("SEER*Rx Category")]
        if category:
            category_code = Canmed.get_generic_code(code_type, category)
            data.categories.add(category_code)
            if major_drug_class:
                data.parent_child_relationship.add(
                    "|".join([category_code, major_drug_code])
                )
                if minor_drug_class:
                    data.parent_child_relationship.add(
                        "|".join([major_drug_code, minor_drug_code])
                    )
                    data.parent_child_relationship.add(
                        "|".join([minor_drug_code, generic_code])
                    )
                else:
                    data.parent_child_relationship.add(
                        "|".join([major_drug_code, generic_code])
                    )
            else:
                if minor_drug_class:
                    data.parent_child_relationship.add(
                        "|".join([category_code, minor_drug_code])
                    )
                else:
                    data.parent_child_relationship.add(
                        "|".join([category_code, generic_code])
                    )
            data.parent_child_relationship.add(
                "|".join([code_type, category_code])
            )

    @staticmethod
    def populate_attributes(definition_row, headers, data, code: str, attribute_mapper: Callable,
                            non_attribute_headers: list[str], ndc_product_code: str = None):
        for header in [header for header in headers if header not in non_attribute_headers]:
            column_value = definition_row[headers.index(header)]
            attribute_name = attribute_mapper(header)
            if column_value:
                if header == "Status":
                    if column_value == "No Longer Used":
                        deprecated = "true"
                    else:
                        deprecated = "false"
                    data.attributes.add(
                        "|".join(
                            [
                                code,
                                "owl:deprecated",
                                deprecated,
                            ]
                        )
                    )
                # Any column other than Description a comma means multiple instances
                column_values = column_value.split(",") if attribute_name != "Description" else [column_value]
                [
                    data.attributes.add(
                        "|".join(
                            [
                                code,
                                attribute_name,
                                cv,
                            ]
                        )
                    )
                    for cv in column_values
                ]
                # Adding attributes for NDC Product Code
                if ndc_product_code and attribute_name in NDC_PRODUCT_ATTRIBUTES:
                    [
                        data.attributes.add(
                            "|".join(
                                [
                                    ndc_product_code,
                                    attribute_name,
                                    cv,
                                ]
                            )
                        )
                        for cv in column_values
                    ]


def process_args(argv):
    hcpcs_def_file: str = ""
    ndconc_def_file: str = ""
    out: str = ""
    opts, args = getopt.getopt(
        argv,
        "hd:n:o:",
        ["help", "hcpcs-definition-file=", "ndconc-definition-file=", "output-directory="],
    )
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(
                """
                    Usage: 
                    med_rt.py -d <hcpcs-definition-file> -n <ndconc-definition-file> -o <output-file>
                """
            )
            sys.exit()
        elif opt in ("-d", "--hcpcs-definition-file"):
            hcpcs_def_file = arg
        elif opt in ("-n", "--ndconc-definition-file"):
            ndconc_def_file = arg
        elif opt in ("-o", "--output-directory"):
            out = arg
    if not hcpcs_def_file:
        print("HCPCS Definition file not provided. Exiting")
        sys.exit(1)
    if not ndconc_def_file:
        print("NDC Definition file not provided. Exiting")
        sys.exit(1)
    if not out:
        print("Output directory not provided. Exiting")
        sys.exit(1)
    return hcpcs_def_file, ndconc_def_file, out


if __name__ == "__main__":
    dfile, nfile, o = process_args(sys.argv[1:])
    Canmed(
        dfile,
        nfile,
        o,
    ).convert()
