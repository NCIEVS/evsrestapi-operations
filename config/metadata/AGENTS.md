# Scope

This directory contains terminology metadata JSON files, HTML welcome/description snippets, mapset metadata, and metadata-specific ignored source configuration.

# Metadata Schema Patterns

- Terminology JSON files define UI labels, FHIR metadata, code/preferred-name fields, synonym/definition/map properties, hierarchy behavior, details columns, and optional SPARQL prefixes.
- Property names and values are operational contracts. Preserve exact spelling, case, prefixes, and null values unless the consuming loader/indexer behavior is updated.
- Some values are injected into SPARQL or used to parse RDF results; do not normalize or prettify them without checking the downstream query behavior.

# Mapping Metadata

`mapsetMetadata.txt` connects checked-in or remote mapping data to mapset names, versions, welcome text, loader class names, and source/target terminology versions.

Mapping welcome text lives in `mapping-*.html` files. Keep those filenames aligned with the `welcomeText` column in `mapsetMetadata.txt`.

# JSON/HTML Pairing

Many terminologies have both `<terminology>.json` and `<terminology>.html`. The JSON is structured machine-readable configuration; the HTML is display text. Update the pair only when the terminology release or display metadata requires both changes.

# Core Files

- `ncit.json`: primary NCI Thesaurus metadata and source/term-type maps.
- `mapsetMetadata.txt`: mapset registry consumed by mapping workflows.
- `ignore-source.txt`: metadata-level ignored source list used by graph listing logic.
