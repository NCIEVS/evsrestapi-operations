# owl_sampling_test.py Notes

This file explains what each test in `owl_sampling_test.py` is protecting.  The
tests exercise `bin/owl_sampling.py` directly because the sampler is an
operations/content-QA script, not an importable product package.

## Test Loader

`_load_owl_sampling_script()` loads `bin/owl_sampling.py` by file path with
`importlib.util.spec_from_file_location`.

This lets pytest call `generate_samples()` directly while the script stays in
`bin/`, where content QA users expect it.

If this loader fails, first check whether `bin/owl_sampling.py` was moved,
renamed, or changed so it can no longer be loaded as normal Python code.

## Shared Synthetic Fixture

`SYNTHETIC_OWL` (loaded from `sample_test_files/synthetic.owl`) is a small
OWL/RDF file made for tests.  It puts many edge cases in one place so the
golden test stays fast and stable:

- namespace handling for default, `rdf`, `rdfs`, `owl`, `ncit`, and `obo`
- object properties with configured codes
- a datatype property in a restriction, which should be skipped
- normal classes with configured `Code` properties
- direct subclass hierarchy using `rdfs:subClassOf rdf:resource`
- subclass restrictions using `owl:onProperty` and `owl:someValuesFrom`
- equivalent-class restrictions under `owl:intersectionOf`
- equivalent-class parent evidence using nested `rdf:Description`
- configured direct properties such as `ncit:P108`
- OBO-style direct properties such as `IAO_0000115`
- multiline text and XML entity decoding
- `owl:disjointWith` resource values
- `owl:deprecated false`, which should not be emitted
- `owl:deprecated true`, which should be emitted
- a no-code deprecated class, which should be skipped
- duplicate synonym qualifier checks, which should be de-duped
- multiple qualifier values for unique qualifier sampling

`SYNTHETIC_CONFIG` (loaded from `sample_test_files/synthetic.json`) is the
metadata JSON for that small OWL file:

- `code`: concept code property
- `preferredName`: configured preferred name property
- `synonym`: synonym properties used to find duplicate qualifier checks
- `definition`: definition properties
- `synonymTermType`: metadata key that should produce unique qualifier samples
- `conceptStatus`: status/deprecation key
- `hierarchy`: marks the terminology as hierarchical

## test_generate_samples_from_synthetic_owl

This is the main exact-output test.  It passes the `synthetic.owl` and
`synthetic.json` files from `sample_test_files/` to `generate_samples()`, then
asserts the exact TSV row sequence matches
`sample_test_files/synthetic_expected.txt`.

It protects these behaviors:

- direct property sampling and first-seen property ordering
- namespace-aware key spelling, including `ncit:P108` and OBO local names
- multiline text normalization into one TSV-compatible line
- XML entity decoding, such as `&amp;` becoming `&`
- resource-valued direct properties resolving to target concept codes
- `owl:deprecated false` being ignored
- `owl:deprecated true` being sampled
- no-code classes being excluded from sample rows
- datatype-property restrictions being skipped
- duplicate role assertions being de-duped across subclass/equivalent contexts
- non-duplicate equivalent-class role assertions being retained
- duplicate synonym qualifier checks being de-duped
- unique qualifier values, such as `TermType=PT` and `TermType=SY`, both being
  sampled
- direct subclass parent/child style rows
- equivalent-class parent/child style rows
- `max-children`
- `parent-count*` rows for the parent counts found in the fixture
- roots
- output file contents matching returned rows
- report counts for rows, classes, sampleable classes, and datatype properties

If this test fails, it usually means one of these changed:

- the TSV columns
- the row order
- the chosen key spelling
- one of the main sample categories

## test_report_lists_disabled_sample_families

This test runs the shared synthetic OWL as `mged`.

MGED has terminology-specific policies that disable a few row families.  The
test does not care about the sample rows themselves.  It checks the JSON report
and verifies that the disabled families are listed there.

It protects the `--report` behavior.  If the sampler skips a row family, the
report should explain why.

If this fails, the sampler may still be skipping rows, but reviewers may not be
able to see why.

## test_duo_restrictions_are_not_policy_skipped

This test runs the shared synthetic OWL as `duo`.

DUO used to be part of the restriction skip policy.  We later confirmed that
EVSRESTAPI returns the real DUO restriction sample as a role, so DUO should not
be skipped.

The test checks two things:

- a normal restriction row is still written for DUO
- the JSON report does not list `restrictions` as a disabled sample family

If this fails, DUO may have lost role coverage.  Before adding DUO back to the
skip list, regenerate the real DUO sample file and run `DuoSampleTest`.

## test_generate_samples_accepts_bom_metadata_json

This test writes the metadata JSON with a UTF-8 BOM prefix and verifies that
sample generation still succeeds.

It protects `TerminologyConfig.load(..., encoding="utf-8-sig")`.

If this fails, metadata files exported with a BOM may stop loading even when the
JSON content is valid.

## test_generate_samples_skips_owl_builtin_classes_with_uri_code_fallback

This test uses a config with no explicit code property.  That means normal
classes can use the URI fragment as the code.  The OWL includes:

- `owl:Thing`
- one real fallback-coded root class

The expected rows include only the real class, not `owl:Thing`.

It protects this rule: built-in OWL classes such as `owl:Thing` and
`owl:Nothing` must not become sample concepts or roots.

If this fails, root output may include OWL built-ins, especially for
terminologies that use URI fragments as concept codes.

## test_generate_samples_canonicalizes_builtin_namespace_prefixes

This test uses unusual prefixes:

- `r:` for RDF
- `o:` for OWL

The expected output still uses the standard sample key `owl:deprecated`.

It protects namespace handling in `QNameResolver`.  The sampler should produce
`rdf:`, `rdfs:`, `owl:`, `xml:`, and `xsd:` keys even when the OWL source file
uses different prefixes.

If this fails, the Java sample tests may miss expected keys because a source OWL
used a legal but unexpected prefix.

## test_generate_samples_indexes_object_property_rdf_type_records

This test models an MGED-style property declaration.

The OWL uses `owl:FunctionalProperty` as the top-level tag, then adds:

```xml
<rdf:type rdf:resource="...owl#ObjectProperty"/>
```

The sampler must still treat that record as an object property and use its
configured code in restriction rows.

It protects role key resolution for OWLs that do not use plain
`owl:ObjectProperty` tags.

If this fails, restriction rows may use raw URI fragments such as `has_owner`
instead of the API-visible role code such as `MO_278`.

## test_generate_samples_shortens_obo_hash_role_uris_to_api_role_name

This test uses an OBO role URI with a hash in the middle:

```text
http://purl.obolibrary.org/obo/cl#lacks_part
```

The expected sample key uses `lacks_part`, not the full `cl#lacks_part` shape.

It protects a small URI-normalization rule used by OBO-family files.

If this fails, Java role checks can look for a role key that EVSRESTAPI never
uses.

## test_equivalent_class_uses_only_top_level_named_parent

This test builds an `owl:equivalentClass` expression with two named classes:

- `Parent`, which is the top-level named class in the intersection
- `NestedNotParent`, which appears deeper inside a restriction

Only `Parent` becomes hierarchy evidence.  `NestedNotParent` is part of
the logical definition, but it is not a parent of the child concept.

It protects OBI-style equivalent-class parsing.  Without this rule, the sampler
can over-count children by treating nested role targets as parents.

If this fails, `max-children`, `parent-count`, or `parent-style2` rows may be
wrong for OWLs with complex logical definitions.

## test_subclass_intersection_uses_top_level_named_parent

This test builds a `rdfs:subClassOf` block that contains an anonymous
`owl:Class` with an `owl:intersectionOf`.

The top-level `rdf:Description` inside that intersection is a real parent.  A
resource deeper inside a restriction is not.

It protects OBIB-style subclass parsing.  Some real parent edges are written in
this anonymous class-expression form instead of the simple
`rdfs:subClassOf rdf:resource="..."` form.

If this fails, the sampler can under-count children and miss parents that
EVSRESTAPI will return after loading.

## test_hierarchy_role_restrictions_count_as_hierarchy_not_roles

This test creates a `part_of some Parent` restriction and marks `part_of` as a
metadata `hierarchyRoles` entry.

That restriction should count as hierarchy evidence:

- the children should not become roots
- the parent should get a `max-children` row
- one child should get a `parent-count1` row
- a fixture with two real top-level parents should get a `parent-count2` row

It should not become a role sample, because EVSRESTAPI loads hierarchy roles as
parent/child links rather than normal concept roles.

If this fails, MA-style hierarchy can either explode into false roots or produce
role rows that the Java tests cannot validate.

## test_scaffold_parents_suppress_roots_without_becoming_samples

This test models an MGED package class with a scaffold parent:

```xml
<owl:Class rdf:about="#MGEDCoreOntology"/>
...
<rdfs:subClassOf>
  <owl:Class rdf:about="#MGEDCoreOntology"/>
</rdfs:subClassOf>
```

`MGEDCoreOntology` is a helper node.  It helps organize the hierarchy, but it
should not become a sample concept or a max-child parent.

The child class should not become a root.  The scaffold parent is enough to
show that the child has a parent after EVSRESTAPI loads MGED.

It protects the MGED root behavior.  Without this rule, package classes look
like local roots in the sampler and then fail the Java root check because the
API correctly returns their scaffold parents.

If this fails, MGED can either regain many false root rows or start sampling
helper nodes as normal concepts.

## test_generate_samples_skips_blank_configured_code_values

This test creates a class with a configured code property whose text collapses
to empty:

```xml
<Code>   </Code>
```

The class also has another property, but the expected sample row list is empty.

It protects the "skip no-code classes" policy.  A blank configured code is not a
real code.  For ordinary terminologies with configured code properties, the
sampler should not fall back to the URI fragment.

If this fails, blank code entries can produce misleading samples for concepts
that EVSRESTAPI may not load as normal concepts.

## test_generate_samples_allows_configured_hierarchy_fallback_terminologies

This test models an HGNC-style hierarchy:

- a code-less hierarchy parent class
- a normal coded child class
- `owl:Thing`, which must still be skipped

The test passes `terminology="hgnc"`.  HGNC is in
`HIERARCHY_FALLBACK_CODE_TERMINOLOGIES`.

It protects a narrow exception: known terminologies may sample real hierarchy
nodes by URI-fragment code even when metadata names a code property.

The expected rows verify:

- the fallback-coded hierarchy parent can be sampled
- the coded child points to that parent
- the unusual legacy `child-style1` row layout is preserved
- max-child and parent-count rows work with fallback-coded parents
- the fallback-coded parent can appear as a root
- `owl:Thing` is still excluded

If this fails, HGNC-like release files can lose parent relationships, which
often shows up as many incorrect root rows.

## test_resource_qualifier_values_match_loader_label_shape

This test models a ChEBI-style axiom qualifier where the qualifier value is a
resource URI.

The sampler should write the local resource code, such as `BRAND_NAME`, because
that is the shape the loader exposes to the Java tests.

It protects qualifier values that are resources instead of plain text.

If this fails, qualifier rows may contain full URIs when the API returns a
short code.

## test_text_values_keep_repeated_spaces_but_skip_fragile_definition_source_qualifier

This test uses a definition with two spaces between sentences.

The direct definition row should keep the meaningful repeated spaces while also
collapsing the multiline XML text into one TSV-compatible line.

The matching definition-source qualifier is skipped because older NCIt-like
definitions with repeated spaces can be normalized differently by the loader.
The direct definition still gives coverage.

If this fails, text normalization may either damage direct property values or
create fragile qualifier rows.

## test_definition_source_qualifier_without_repeated_spaces_is_sampled

This is the companion test for the previous one.

It uses a simple one-line definition without repeated spaces.  In that case,
the definition-source qualifier should be sampled.

It protects the narrowness of the repeated-space exception.  The sampler should
skip only the fragile case, not all definition-source qualifiers.

## test_equivalent_class_hierarchy_is_skipped_for_known_logical_definition_owls

This test makes one child with two direct parents and three extra classes inside
an `owl:equivalentClass` `owl:unionOf` expression.  It also adds two more
children that point at the same equivalent-class member, so the fixture can test
`max-children` separately from `parent-count*`.

It runs the same OWL twice:

- as a normal synthetic terminology
- as `npo`

The normal run should write `parent-count5`, because it treats equivalent-class
members as hierarchy evidence.  The `npo` run should write `parent-count2`,
because NPO-style equivalent-class union/intersection members are logical
definitions, not API-visible direct parent links.  The `npo` run should still
write a `max-children` row for the shared equivalent-class member, because the
API may expose those members as child links even when they are not direct
parents.

If this fails, the sampler may be either adding false parent links for NPO-like
OWL files or skipping valid equivalent-class hierarchy for terminologies that
still use that pattern as API-visible hierarchy.

## test_real_owl_smoke_samples

This is a local smoke test for representative OWL files configured through
`UNIT_TEST_DATA_DIR`.  It checks the main behavior, not every exact row.

It only runs when both environment variables are set:

```powershell
$env:EVS_RUN_LOCAL_OWL_SMOKE='1'
$env:UNIT_TEST_DATA_DIR='D:\WCI\UnitTestData'
```

Each case generates samples to `tmp_path`, then checks:

- output file exists
- at least one row was generated
- no row value contains a tab, which would break the TSV contract
- required high-value keys are present

The cases are:

- `go`: expects `rdfs:label`, `root`, and `parent-count1`
- `canmed`: expects `Preferred_Name`, `root`, and `parent-count1`
- `mged`: expects `class_source` and `parent-count1`
- `ctcae6`: expects `ncit:P108` and `parent-count1`
- `ncit`: expects `P108`, `P310`, `root`, and `parent-count1`

These are not exact-output tests.  They catch large parsing failures, missing
categories, namespace problems, and malformed TSV output on real release files.
They do not assert exact row counts because terminology release files change.

If one of these fails, check these first:

- does the local OWL path still exist?
- did the metadata JSON change?
- did the sampler stop producing one of the required sample categories?

## When Adding Tests

Prefer a small synthetic OWL fixture in `sample_test_files/` for one edge case.
Real OWL smoke tests help, but they are slower and depend on external files in
`UNIT_TEST_DATA_DIR`.

Use exact TSV assertions when the row format or row order matters.  Use key or
category assertions when real-file examples are allowed to vary.
