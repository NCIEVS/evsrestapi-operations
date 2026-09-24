# Scope

This directory contains active terminology converters and the shared OWL writer.

# Conversion Pipeline

Source-specific converters read external terminology inputs and write simple-format files. `owl_file_converter.py` reads those simple-format files and writes RDF/XML OWL.

The converters intentionally do not share a large framework. Follow the local style in the converter being changed, and add shared helpers only when they remove real duplication across converters.

# CLI Argument Pattern

Converters use `getopt`-based `process_args(argv)` functions and exit with clear messages when required inputs are missing. Keep shell wrapper options and Python CLI options in sync.

# Simple Format Writers

Use `simple_format_utils.get_output_files(output_directory)` for standard output filenames. Write pipe-delimited rows without headers, matching the model field order consumed by `load_file()` and `load_concepts()`.

# OWL Writer Pattern

`OwlConverter` loads concepts, attributes, parent-child rows, and optional relationships from a simple-format directory. It writes ontology metadata, annotation properties, object properties, classes, subclass relationships, and restrictions.

Attribute names are transformed with spaces replaced by underscores when written as OWL annotation elements. Attributes containing namespace-style colons are handled specially in metadata generation.

# Entry Points And Core Logic

- `hgnc.py`: converts HGNC TSV data and creates locus group/type hierarchy rows.
- `canmed.py`: converts paired HCPCS and NDC CSV exports into CanMED concept hierarchy and attributes.
- `med_rt.py`: converts MED-RT XML concepts, parent-child associations, and relationships.
- `umls_sem_net.py`: converts UMLS Semantic Network files into concepts, attributes, hierarchy, and relationships.
- `owl_file_converter.py`: converts simple-format files to OWL.
- `simple_format_utils.py`: centralizes standard simple-format output filenames.
