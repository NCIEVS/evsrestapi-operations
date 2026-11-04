# Scope

This directory contains checked-in EVS mapping data files used by mapset workflows.

# Mapping File Format

Mapping files are tab-delimited text files with `Source Code` and `Target Code` columns. Preserve the header, delimiter, code casing, and source/target orientation.

# Naming And Versioning

Filenames encode source terminology, target terminology, and extraction/version date. Keep filenames aligned with the mapset metadata in `config/metadata/mapsetMetadata.txt`.

# Core Files

- `NCIt_to_HGNC_Mapping_Apr2026.txt`
- `NCIt_to_ChEBI_Mapping_Aug2024.txt`
- `GO_to_NCIt_Mapping_February2020.txt`
- `ICD10_to_MedDRA_Mapping_July2023.txt`
- `MA_to_NCIt_Mapping_November2011.txt`
- `PDQ_2016_07_31_TO_NCI_2016_10E_201607.txt`
