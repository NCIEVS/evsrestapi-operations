# OWL Sampling Tutorial

## What The Script Does

`owl_sampling.py` generates small TSV sample files from EVS terminology OWL
release files.  EVSRESTAPI Java tests use those sample files after a terminology
load.  The tests call the REST API and check that the loaded content comes back
correctly.

The sampler does not copy the whole OWL file.  It writes sample rows for things
the Java tests should check: properties, roles, qualifiers, parents, children,
deprecated concepts, and roots.

The script lives in:

```text
bin/owl_sampling.py
```

The file contains both the command-line entrypoint and the internal classes used
by pytest.  It is an operations/content-QA script, not a package API.

## Output Format

The output file is UTF-8 TSV with no header.  Every row has either three or four
columns:

```text
uri<TAB>code<TAB>key
uri<TAB>code<TAB>key<TAB>value
```

The Java tests read the columns like this:

- `uri`: the concept URI from the OWL file.
- `code`: the EVSRESTAPI concept code to query.
- `key`: what the test should check, such as `P108`, `root`,
  `parent-style1`, or `qualifier-P90~P383~PT`.
- `value`: the expected property, role target, qualifier value, parent code,
  child code, or count when the row type needs one.

Do not add a header row or change the column order unless the Java sample-file
parser changes too.

## How Rows Are Used By EVSRESTAPI Tests

The sample file is grouped by the `code` column.  For each sampled concept,
`ConceptSampleTester` asks EVSRESTAPI for the full concept:

```text
/api/v1/concept/{terminology}/{code}?include=full
```

Then the row `key` tells the tester what part of that response to inspect.
Examples:

- property keys verify loaded concept properties, labels, synonyms, definitions,
  maps, associations, or status values on the full concept response
- restriction keys verify role metadata and role target entries
- qualifier keys verify qualified synonym, definition, map, or property metadata
- `parent-style*` and `child-style*` verify parent and child relationships on
  the full concept response
- `parent-count*`, `max-children`, and `root` verify hierarchy counts and root
  behavior

The same sample map also gives the Java tests examples for metadata endpoints
such as:

```text
/api/v1/metadata/{terminology}/properties
/api/v1/metadata/{terminology}/roles
/api/v1/metadata/{terminology}/qualifiers
/api/v1/metadata/{terminology}/associations
```

Hierarchy rows also give the Java tests examples for roots, paths, and subtree
calls:

```text
/api/v1/concept/{terminology}/roots
/api/v1/concept/{terminology}/{code}/pathsToRoot
/api/v1/concept/{terminology}/{code}/pathsFromRoot
/api/v1/concept/{terminology}/{code}/subtree
```

The sampler covers behavior categories instead of every OWL line.  A row is kept
when the Java tests can check that concept and value after loading.

## Basic Usage

From the `evsrestapi-operations` repository root:

```powershell
python bin\owl_sampling.py D:\WCI\UnitTestData\GO\GO.20250601.owl config\metadata\go.json
```

By default, the output is written to:

```text
<metadata-json-stem>-samples.txt
```

For the command above, that is:

```text
go-samples.txt
```

## Optional Flags

Use `--output` to choose the sample file path:

```powershell
python bin\owl_sampling.py D:\WCI\UnitTestData\GO\GO.20250601.owl config\metadata\go.json --output C:\tmp\go-samples.txt
```

Use `--terminology` when the terminology name should not come from the metadata
filename:

```powershell
python bin\owl_sampling.py D:\WCI\UnitTestData\NCIT\ThesaurusInferred_monthly.owl config\metadata\ncit.json --terminology ncit --output C:\tmp\ncit-samples.txt
```

Use the EVSRESTAPI terminology name, such as `ncit`, `go`, or `obib`, unless
you are doing a deliberate experiment.  Some sampler policies are keyed by this
name.  A made-up value can accidentally turn those policies off.

Use `--report` to write a small JSON summary:

```powershell
python bin\owl_sampling.py D:\WCI\UnitTestData\CTCAE\ctcae6.owl config\metadata\ctcae6.json --output C:\tmp\ctcae6-samples.txt --report C:\tmp\ctcae6-report.json
```

The report includes simple counts, such as total rows, classes, sampleable
classes, property types, deprecated classes, parent relationships, and axiom
samples.  It also includes `disabledSampleFamilies`.  That field lists any row
families the script skipped for that terminology, along with the reason.  Check
that list when reviewing a generated file.

## How The Sampler Reads OWL

The sampler reads the OWL with `lxml.etree.iterparse`.  It makes two passes
through the file.

Pass 1 builds lookup tables:

- Class URI to concept code.
- Object property URI to property code.
- Annotation property URI to property code.
- Datatype property URI/key lookups.
- Sampleable class URI set.
- Deprecated class URI set.

Pass 2 collects sample rows:

- Direct concept properties.
- Restriction/role rows.
- Parent and child hierarchy evidence.
- Axiom qualifier rows.
- Root rows.

The two-pass design matters because many OWL values point to URIs.  A role
target can appear before the target class is defined.  The sampler first learns
all URI-to-code mappings, then uses those mappings when it writes rows.

The parser clears each completed top-level RDF element as it goes, so large OWL
files such as NCIt and HGNC can be processed without loading the full XML tree
into memory.

## Code Resolution

The sampler resolves a concept code in this order:

1. The configured code property from the terminology metadata JSON.
2. `rdf:ID`, if that is the configured code source.
3. The local part of `rdf:about`, if `rdf:about` is the configured code source.
4. URI-fragment fallback, such as `http://example.org#C123` -> `C123`.

If the metadata JSON names a code property, a class normally must have that
property before the sampler uses it.  This avoids sampling helper classes that
are in the OWL file but are not normal API concepts.

There is one explicit exception for a terminology that has real hierarchy
concepts without a code property:

- `hgnc`

OWL built-ins such as `owl:Thing` and `owl:Nothing` are never sampleable roots.

## Key Normalization

XML namespaces are normalized with `QNameResolver`.  In plain terms, this turns
long XML names into the short names used by the sample files.

Examples:

- `{rdf namespace}ID` becomes `rdf:ID`.
- `{rdfs namespace}label` becomes `rdfs:label`.
- NCIt properties can stay as `ncit:P108` when that is the namespace prefix in
  the OWL.
- OBO properties from `http://purl.obolibrary.org/obo/` are emitted as local
  names such as `IAO_0000115`, matching the historical sample files.

The metadata JSON also tells the sampler which spelling to prefer.  For example,
if the OWL says `ncit:P108` but metadata says `P108`, the sampler can still
understand that they refer to the same property.

## What Gets Sampled

### Direct Concept Properties

Direct child elements of a sampled `owl:Class` usually become property samples.
The sampler skips structural OWL tags and the configured code property.

Examples:

```text
http://example.org#C1<TAB>C1<TAB>P108<TAB>Preferred Name
http://example.org#C1<TAB>C1<TAB>rdfs:label<TAB>Concept label
```

Text values are collapsed to one line.  XML entities are decoded, so `&amp;`
becomes `&`.

Resource values are resolved to codes when the URI index knows the target.

In EVSRESTAPI, these rows usually test values on the full `Concept` response.
Depending on metadata, the value may appear in `properties`, `synonyms`,
`definitions`, `maps`, labels, or status fields.

### Deprecated Concepts And Status Values

`owl:deprecated true` is sampled.  `owl:deprecated false` is ignored.

NCIt concept status (`P310`) keeps multiple rows.  The Java tests need examples
of more than one status value, not just the first one found.

### Disjoint-With Links

`owl:disjointWith` is sampled as a direct property with its target resource
resolved to a code where possible.

### Restrictions And Roles

Restrictions under `rdfs:subClassOf` or `owl:equivalentClass` become role
samples.  These rows say "this concept should have this role pointing to that
target concept."

```text
uri<TAB>code<TAB>rdfs:subClassOf/owl:Restriction~roleCode<TAB>targetCode
uri<TAB>code<TAB>owl:equivalentClass/owl:Restriction~roleCode<TAB>targetCode
```

The sampler skips:

- Datatype-property restrictions, because they point to literal values instead
  of concepts.
- Roles listed as `hierarchyRoles` in metadata, because those load as hierarchy
  links instead of normal roles.
- Restriction-heavy terminologies where EVSRESTAPI does not expose the OWL
  restrictions as API roles.  The Java tests treat every restriction row as an
  API role check, so those rows would be false failures.
- Duplicate role rows that would test the same concept, role, and target.

DUO is the exception.  It has a sampled `DUO_0000010` restriction, and
EVSRESTAPI returns that restriction as a role, so the sampler keeps DUO
restriction rows.

In EVSRESTAPI, these rows check two things: the role exists in metadata, and the
sampled concept returns the expected role target.

### Axiom Qualifiers

OWL axioms can add metadata to a property value.  The sampler writes qualifier
keys in this form:

```text
qualifier-<annotatedProperty>~<qualifierProperty>
qualifier-<annotatedProperty>~<qualifierProperty>~<qualifierValue>
```

The second form is used when each qualifier value needs its own row, such as
synonym term type or synonym source.

Example:

```text
uri<TAB>code<TAB>qualifier-P90~P383~PT<TAB>Synonym Value~PT
```

Complex axiom targets are skipped because the Java tests look up simple values,
not nested OWL structures.

The sampler also removes duplicate qualifier checks.  This matters when two TSV
rows look different but would test the same thing in Java.

In EVSRESTAPI, qualifiers are metadata attached to a returned value.  For
example, a synonym can have a term type or source, a definition can have a
source, and a map can have relation or target metadata.  These rows check that
metadata survived loading and indexing.

### Parent And Child Styles

The sampler records examples of two hierarchy styles:

- `parent-style1` and `child-style1` for direct `rdfs:subClassOf` parents.
- `parent-style2` and `child-style2` for equivalent-class intersections that
  contain `rdf:Description` parents.

The `child-style*` rows have a historical layout:

```text
child-uri<TAB>parent-code<TAB>child-style1<TAB>child-code
```

This is legacy layout.  The Java tests use the row code as the parent concept to
query, then check that the child is present.

### Max Children

`max-children` records the parent concept with the largest observed active child
list:

```text
parent-uri<TAB>parent-code<TAB>max-children<TAB>child-count
```

Only sampleable parent concepts can win this row.  The sampler may still record
imported or built-in parents for root checks, but it does not use those parents
for exact child-count rows because the Java test needs to query the parent
concept directly.

`max-children` has its own child list inside the sampler.  This is separate from
the parent-count list.  That split matters for NPO, OBI, and OBIB: their
`owl:equivalentClass` members are not counted as direct parents, but they can
still count as children when EVSRESTAPI exposes them in a concept's child list.

### Parent Counts

The sampler writes one example for each parent count it sees:

```text
child-uri<TAB>child-code<TAB>parent-count1
child-uri<TAB>child-code<TAB>parent-count2
child-uri<TAB>child-code<TAB>parent-count3
```

The number at the end is the number of parents found in OWL evidence used by
the sampler.  These rows give the Java tests non-root concepts for hierarchy
calls and check that EVSRESTAPI keeps multi-parent concepts connected.

Most terminologies get one row for every distinct parent count.  Some OWLs use
`owl:equivalentClass` `owl:unionOf` or `owl:intersectionOf` members as logical
definitions rather than API-visible direct parent links.  For those
terminologies, `parent-count*`, `parent-style2`, and `child-style2` use the
clear direct parents from `rdfs:subClassOf`.  `max-children` may still count
those equivalent-class members as child evidence when that matches the API's
loaded child list.

### Roots

Every sampled class with no recorded parent becomes a `root` row unless it is a
deprecated class, object property, annotation property, or configured helper
node.

```text
root-uri<TAB>root-code<TAB>root
```

Root rows do more than check the concept itself.  They also give the Java tests
examples for `/roots`, `/pathsToRoot`, `/pathsFromRoot`, and `/subtree`.

The sampler records explicit parent references even when the parent class is
imported or built in, such as `owl:Thing`.  Those parent references prevent
false root rows.  They do not create `max-children` rows unless the parent is
also a sampleable class in the OWL file.

## Terminology-Specific Policies

If a terminology needs a special rule, prefer adding a named policy near the top
of `bin/owl_sampling.py`.  Avoid hiding one-off rules deep inside parsing loops.

Keep policies rare and specific.  They prevent false Java sample rows, and they
should not hide content QA.

For example, a restriction row always means "the API should return this as a
Concept role."  Some OBO-style OWLs use restrictions for ontology modeling or
imports that EVSRESTAPI does not expose as Concept roles.  Sampling those rows
would test the wrong API behavior.  The terminology can still be tested through
direct properties, qualifiers, deprecated flags, search examples, and hierarchy
rows that match the API.

Root rows follow the same rule.  When the OWL has an explicit parent URI, the
sampler keeps that edge for root and parent-count checks even if the parent
class is not sampleable from the same file.  This lets DUO, OBI, and OBIB keep
low-count hierarchy samples without writing false root rows.

Current policies:

- `HIERARCHY_SCAFFOLD_LOCALS_BY_TERMINOLOGY`: class names that help build the
  hierarchy but should not become sample rows themselves.  MGED is the current
  example.
- `HIERARCHY_FALLBACK_CODE_TERMINOLOGIES`: terminologies that may sample
  classes using URI-fragment fallback codes, even though metadata has a code
  property.  The current example is `hgnc`.
- `SKIP_RESTRICTION_SAMPLE_TERMINOLOGIES`: terminologies where OWL restrictions
  do not make reliable API role samples.  The current examples are `mged`,
  `npo`, `obi`, and `obib`.
- `SKIP_EQUIVALENT_CLASS_HIERARCHY_TERMINOLOGIES`: terminologies where
  equivalent-class union/intersection members are logical definitions, not
  API-visible direct parent links.  The current examples are `npo`, `obi`, and
  `obib`.  These members can still help `max-children` when the API exposes
  them as children.
- `SKIP_DIRECT_PROPERTY_KEYS_BY_TERMINOLOGY`: direct property keys that are
  parsed from OWL but are not exposed with the same meaning in EVSRESTAPI.
- `OWL_BUILTIN_CLASS_URIS`: built-in OWL classes that should never become
  sample concepts.

### Current Policy Examples

These examples show why each policy exists.  They do not list every affected
row.

#### `HIERARCHY_SCAFFOLD_LOCALS_BY_TERMINOLOGY`

- `mged`: `BioMaterialPackage` points to `MGEDCoreOntology` as a parent.
  `MGEDCoreOntology` is a package/scaffold class, not a normal concept sample.
  The sampler keeps that edge so `BioMaterialPackage` does not look like a root,
  but it does not write a sample row for `MGEDCoreOntology` itself.

#### `HIERARCHY_FALLBACK_CODE_TERMINOLOGIES`

- `hgnc`: `HGNC_5` has the parent `gene_with_protein_product`.  That parent has
  no configured `hgnc_id` value, but it is a real API concept.  URI-fragment
  fallback lets the sampler write hierarchy rows such as
  `HGNC:5 parent-style1 gene_with_protein_product` and root rows for hierarchy
  classes like `gene_with_protein_product`.

#### `SKIP_RESTRICTION_SAMPLE_TERMINOLOGIES`

- `mged`: without this policy, the sampler writes rows such as
  `MO_9 rdfs:subClassOf/owl:Restriction~MO_233 MO_30` for `StrainOrLine`.
  MGED uses many of these restrictions as ontology modeling details.  The Java
  tester reads the row as an API role assertion, which is not reliable for MGED.
- `npo`: without this policy, rows such as
  `NPO_1988 rdfs:subClassOf/owl:Restriction~has_part NPO_1989` are sampled.
  NPO has many restriction rows that do not come back as matching API roles; in
  Java checks these show up as `Wrong role` sampling errors.
- `obi`: without this policy, rows such as
  `APOLLO_SV_00000032 owl:equivalentClass/owl:Restriction~OBI_0000312`
  `APOLLO_SV_00000033` are sampled.  OBI uses many equivalent-class
  restrictions as logical definitions, not as plain concept roles.
- `obib`: without this policy, rows such as
  `CHEBI_42191 rdfs:subClassOf/owl:Restriction~RO_0000087 OBIB_0000022` are
  sampled.  OBIB imports and reuses OBI-style logical restrictions, so the Java
  API-role check is too strict for these rows.

#### `SKIP_EQUIVALENT_CLASS_HIERARCHY_TERMINOLOGIES`

- `npo`: if equivalent-class members are counted as parents, `NPO_656` produces
  a `parent-count22` row.  That is not the direct parent count EVSRESTAPI returns
  for the concept, so it creates a false hierarchy failure.
- `obi`: if equivalent-class members are counted as parents, `OBI_0100026`
  produces a `parent-count5` row.  Those extra parents come from logical class
  expressions, not from the API-visible direct parent list.
- `obib`: if equivalent-class members are counted as parents, `OBI_0000639`
  produces a `parent-count3` row.  OBIB should use direct subclass parents for
  parent counts, while equivalent-class members can still help `max-children`.

#### `SKIP_DIRECT_PROPERTY_KEYS_BY_TERMINOLOGY`

- `mged` / `synonym`: without this policy, the sampler writes
  `MO_513 synonym d` for the `days` concept.  The Java sample test reports this
  as `Wrong synonym d of MO_513`, so this OWL value is not a reliable Concept
  synonym sample.
- `npo` / `synonym`: without this policy, the sampler writes
  `NPO_100 synonym cylindrical`.  EVSRESTAPI returns that value under
  `properties` as `npo:synonym`, while the Java sample row key `synonym` checks
  synonym objects.  The row checks the wrong API field.
- `npo` / `rdfs:comment`: without this policy, the sampler writes a long TEM
  microscope comment for `NPO_1430`.  The Java sample test reports it as an
  incorrectly labelled comment, because that OWL comment is not exposed as the
  direct `rdfs:comment` property shape the row asks for.

#### `OWL_BUILTIN_CLASS_URIS`

This policy is global, not terminology-specific.

- Example: OWLs can contain `owl:Thing` or `owl:Nothing` class records.  Those
  are OWL language built-ins, not EVSRESTAPI concepts.  The sampler always keeps
  them out of sample concepts and root rows.

When adding a new policy, also add a small pytest fixture that shows the edge
case.  That makes the reason for the special rule clear later.

## Regenerating Sample Files

Generate to a temporary directory first:

```powershell
python bin\owl_sampling.py D:\WCI\UnitTestData\GO\GO.20250601.owl config\metadata\go.json --output C:\tmp\owl-sampling\go-samples.txt --report C:\tmp\owl-sampling\go-report.json
```

Compare line counts, byte counts, malformed row counts, and duplicate rows
against the checked-in fixtures under:

```text
D:\WCI\Repos\evsrestapi\src\test\resources\samples
```

Exact row equality is not required when the OWL release version changed.  But
the output should usually be in the same ballpark and cover the same sample
categories.

When the regenerated file is expected to differ, run the affected EVSRESTAPI
Java sample tests before replacing checked-in fixtures.

## Running Tests

Run the synthetic unit tests:

```powershell
python -m pytest test\owl_sampling_test.py -q
```

Run local real-file smoke tests when `D:\WCI\UnitTestData` is available:

```powershell
$env:EVS_RUN_LOCAL_OWL_SMOKE='1'
$env:UNIT_TEST_DATA_DIR='D:\WCI\UnitTestData'
python -m pytest test\owl_sampling_test.py -q
```

Run the whole operations test suite:

```powershell
$env:PYTHONPATH='.:src'
poetry run pytest
```

Run EVSRESTAPI Java sample tests after regenerating real sample files.  These
need the local test OpenSearch data available on port `9201`; otherwise every
API call fails before the sample rows are tested.  Manual workflow:

1. Generate samples to `C:\tmp`.
2. Back up the matching checked-in file under
   `D:\WCI\Repos\evsrestapi\src\test\resources\samples`.
3. Copy the generated file into that samples directory.
4. Run the matching `*SampleTest` class.
5. Restore the checked-in sample file even if the test fails.

When reading Java test results, separate sample-row failures from unrelated
static test failures.  Parent/child sampler problems usually show up as messages
like `has 2 parents, stated number 5`, `has 204 children, stated number 105`, or
`SAMPLING ERRORS FOUND`.

## Troubleshooting

If root counts suddenly become huge, check whether parent classes were skipped
as no-code classes.  A terminology may need an explicit fallback-code policy if
those parent classes are real API concepts.

If a restriction row looks wrong, check whether the role is an object property,
a datatype property, or a configured `hierarchyRoles` entry.

If qualifier rows seem duplicated, compare the rows against what
`ConceptSampleTester` actually checks.  TSV keys can differ even when the Java
test would check the same thing.

If a property key has the wrong prefix, check the OWL namespace map and the
metadata JSON spelling.  Fix namespace translation in `QNameResolver` or
`TerminologyConfig.preferred_key`, not with string parsing in the collector.

If XML parsing fails, treat the source OWL as invalid first.
The parser fails on malformed XML so it does not produce partial sample files.
