# EVS REST API Terminology Metadata Configuration Guide

## Overview

This directory contains JSON configuration files that define how each terminology's RDF/OWL properties map to the EVS REST API data model. Each `{terminology}.json` file specifies which OWL annotation properties represent concepts' codes, names, synonyms, definitions, and other attributes.

## Architecture: Dual-Prefix Strategy

The system uses a complementary two-part approach for handling RDF namespace prefixes:

1. **Property Codes in Metadata** (e.g., `"code": "ncit:NHC0"`)
   - Declares which namespace a property belongs to
   - Provides semantic clarity about property ownership
   - Injected into SPARQL query templates as `#{codeCode}` → becomes `?x ncit:NHC0 ?code`

2. **sparqlPrefix Declarations** (e.g., `"sparqlPrefix": "PREFIX ncit:<...>"`)
   - Makes namespace shortcuts valid in SPARQL
   - Prepended to all SPARQL queries for the terminology
   - Resolves prefix abbreviations to full URIs

**Why both are needed:** Property codes declare the semantic relationship (which namespace), while sparqlPrefix makes those prefixes valid in SPARQL syntax.

---

## Three Configuration Patterns

### Pattern 1: Self-Contained Ontology

**When to use:** Your ontology defines all its own properties within its own namespace.

**Example:** CTCAE5 (`ctcae5.json`)
```json
{
  "uiLabel": "CTCAE 5",
  "code": "NCIt_Code",
  "preferredName": "Preferred_Name",
  "synonym": ["FULL_SYN"],
  "definition": ["DEFINITION", "ALT_DEFINITION"],
  "definitionSource": "def-source",
  "synonymSource": "term-source",
  "synonymTermType": "term-group"
  // NO sparqlPrefix - uses default graph prefix template
}
```

**Characteristics:**
- All property names are simple, unprefixed identifiers
- Properties are defined in the ontology's own OWL file
- No `sparqlPrefix` field needed (uses default `prefix.graph` template)
- Default prefix: `PREFIX :<ontology-source#> PREFIX base:<ontology-source#>`

**OWL Structure:**
```xml
<owl:AnnotationProperty rdf:about="http://ncicb.nci.nih.gov/xml/owl/EVS/ctcae5.owl#Preferred_Name"/>
<owl:AnnotationProperty rdf:about="http://ncicb.nci.nih.gov/xml/owl/EVS/ctcae5.owl#FULL_SYN"/>
```

---

### Pattern 2: External Namespace Dependency

**When to use:** Your ontology references properties from another ontology (e.g., NCIt Thesaurus).

**Example:** CTCAE6 (`ctcae6.json`)
```json
{
  "uiLabel": "CTCAE 6",
  "code": "ncit:NHC0",           // External: from NCIt Thesaurus namespace
  "preferredName": "ncit:P108",   // External: from NCIt Thesaurus namespace
  "synonym": ["P90", "P107", "P108"],     // Local: from ctcae6.owl namespace
  "synonymTermType": "P383",     // Local property
  "definition": ["P97", "P325"], // Local properties
  "sparqlPrefix": "PREFIX :<http://ncicb.nci.nih.gov/xml/owl/EVS/ctcae6.owl#> PREFIX base:<http://ncicb.nci.nih.gov/xml/owl/EVS/ctcae6.owl#> PREFIX ncit:<http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>"
}
```

**Characteristics:**
- **Mixed namespaces**: Some properties from external ontology, some from own ontology
- Properties from external namespace use prefix (e.g., `ncit:P108`)
- Properties from own namespace are unprefixed (e.g., `P90`)
- **Must include `sparqlPrefix`** declaring all namespaces used

**OWL Structure:**
```xml
<!-- External property imported from NCIt -->
<owl:AnnotationProperty rdf:about="http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P108">
  <ncit:P108>Preferred_Name</ncit:P108>
  ...
</owl:AnnotationProperty>

<!-- Local property defined in ctcae6.owl -->
<owl:AnnotationProperty rdf:about="http://ncicb.nci.nih.gov/xml/owl/EVS/ctcae6.owl#P90"/>
```

**Why CTCAE6 uses this pattern:**
- Reuses NCIt Thesaurus's standardized property definitions (P108, NHC0)
- Promotes data consistency across NCI terminologies
- Maintains local properties for CTCAE-specific attributes

---

### Pattern 3: Standard Vocabulary Integration

**When to use:** Your ontology uses standard W3C or OBO Foundation properties.

**Example:** ChEBI (`chebi.json`)
```json
{
  "uiLabel": "ChEBI",
  "code": "oboInOwl:id",         // OBO Foundation property
  "preferredName": "rdfs:label", // W3C RDFS property
  "synonym": ["oboInOwl:hasExactSynonym", "oboInOwl:hasRelatedSynonym"],
  "definition": ["obo:IAO_0000115"],
  "sparqlPrefix": "PREFIX :<http://purl.obolibrary.org/obo/chebi.owl#> PREFIX base:<http://purl.obolibrary.org/obo/chebi.owl#> PREFIX chebi:<http://purl.obolibrary.org/obo/chebi/> PREFIX CHEBI:<http://purl.obolibrary.org/obo/chebi/> PREFIX obo:<http://purl.obolibrary.org/obo> PREFIX oboInOwl:<http://www.geneontology.org/formats/oboInOwl#>"
}
```

**Characteristics:**
- Uses standard vocabularies (OBO, RDFS, OWL)
- All properties use namespace prefixes (oboInOwl:, rdfs:, obo:)
- Requires explicit prefix declarations for all standard namespaces
- Multi-level namespace structure (chebi:, CHEBI:, obo:, oboInOwl:)

---

## Decision Tree for Configuring New Terminology

### Step 1: Examine Your OWL File

Look at the namespace declarations in your OWL file:
```xml
<rdf:RDF xmlns="http://your-ontology.owl#"
         xmlns:ncit="http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#"
         xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#">
```

### Step 2: Identify Property Namespaces

For each property you need to configure (code, preferredName, synonym, etc.):

```
Is the property defined in YOUR ontology's namespace?
│
├─ YES → Use UNPREFIXED code
│         Example: "code": "NHC0"
│         Example: "preferredName": "Preferred_Name"
│
└─ NO → Property from another ontology or standard vocabulary?
          │
          ├─ Use PREFIXED code
          │   Example: "code": "ncit:NHC0" (from NCIt)
          │   Example: "preferredName": "rdfs:label" (from RDFS)
          │
          └─ Declare prefix in sparqlPrefix
              Example: "sparqlPrefix": "PREFIX ncit:<http://...> PREFIX rdfs:<http://...>"
```

### Step 3: Build sparqlPrefix Declaration

**Rule:** Include ALL prefixes referenced in your property codes.

**Template:**
```json
"sparqlPrefix": "PREFIX :<your-ontology#> PREFIX base:<your-ontology#> [PREFIX external:<external-namespace#>]*"
```

**Common prefixes:**
- Standard vocabularies (always available in `prefix.common`):
  - `owl:`, `rdf:`, `rdfs:`, `xsd:`, `dc:`, `oboInOwl:`, `xml:`
- Custom namespaces (must declare if used):
  - `ncit:` for NCIt Thesaurus properties
  - `obo:` for OBO Foundation
  - `chebi:`, `GO:`, `HGNC:` for specific ontologies

---

## Configuration Checklist

When creating a new `{terminology}.json` file:

### Required Fields
- [ ] `uiLabel` - Display name (e.g., "CTCAE 6")
- [ ] `code` - Property that contains concept code (with prefix if external)
- [ ] `preferredName` - Property for preferred term (with prefix if external)
- [ ] `hierarchy` - Boolean indicating if hierarchy exists

### Common Optional Fields
- [ ] `synonym` - Array of synonym properties
- [ ] `definition` - Array of definition properties
- [ ] `synonymSource`, `synonymTermType`, `synonymCode` - Qualifier properties for synonyms
- [ ] `definitionSource` - Qualifier property for definitions
- [ ] `conceptStatus` - Property indicating retirement/deprecation
- [ ] `retiredStatusValue` - Value indicating retired status
- [ ] `sparqlPrefix` - Custom prefix declarations (required if any property uses external namespace)

### Prefix Validation
- [ ] All prefixes used in property codes are declared in `sparqlPrefix`
- [ ] Local properties (from your ontology) have NO prefix
- [ ] External properties (from other ontologies) have appropriate prefix
- [ ] Standard vocabulary prefixes (rdfs:, owl:) are declared if used beyond defaults

---

## Why NOT to Move Prefixes to Query Templates

### The Alternative Considered

Some might think it's cleaner to hardcode prefixes in SPARQL query templates:

```sparql
# properties.ctcae6 (hypothetical)
?x ncit:NHC0 "#{conceptCode}" .     # Hardcoded ncit: prefix
?property ncit:P108 ?label .        # Hardcoded ncit: prefix
```

### Why This Approach Fails

1. **Query Explosion**: Need separate query variant for each terminology
   - Current: 40 reusable queries
   - Alternative: 240+ duplicate queries (40 × 6 terminologies)

2. **Mixed Namespace Problem**: CTCAE6 uses BOTH namespaces:
   - External: `ncit:NHC0` (from NCIt)
   - Local: `P90` (from ctcae6.owl)
   - Would need per-property prefix logic in every query

3. **Maintenance Burden**: Bug fixes require updating 6+ copies of each query

4. **Configuration Opacity**: Have to read SPARQL queries to understand property namespaces

5. **Violates Existing Pattern**: System has terminology-specific queries (`.ncit`, `.chebi`) but uses them ONLY for structural differences, NOT prefix differences

**Evidence:** Even `hierarchy.ncit` query still uses `#{codeCode}` from metadata!

### The Current Approach is Optimal

**Separation of Concerns:**
- **Metadata JSON**: WHAT properties to use (configuration)
- **SPARQL Queries**: HOW to retrieve data (query logic)
- **sparqlPrefix**: Makes prefixes valid (SPARQL syntax)

This separation enables query reuse, clear configuration, and maintainable code.

---

## Examples by Terminology

### NCIt (NCI Thesaurus)
```json
{
  "code": "NHC0",
  "preferredName": "P90"
  // No sparqlPrefix - uses default graph prefix
}
```
Self-contained, standard NCI namespace structure.

### CTCAE5
```json
{
  "code": "NCIt_Code",
  "preferredName": "Preferred_Name",
  "synonym": ["FULL_SYN"]
  // No sparqlPrefix - uses default graph prefix
}
```
Self-contained with custom property names.

### CTCAE6
```json
{
  "code": "ncit:NHC0",           // External
  "preferredName": "ncit:P108",   // External
  "synonym": ["P90", "P107"],     // Local
  "sparqlPrefix": "PREFIX :<ctcae6.owl#> PREFIX ncit:<Thesaurus.owl#>"
}
```
Mixed: References NCIt properties + defines own properties.

### ChEBI
```json
{
  "code": "oboInOwl:id",
  "preferredName": "rdfs:label",
  "sparqlPrefix": "PREFIX obo:<...> PREFIX oboInOwl:<...>"
}
```
Uses OBO and W3C standard vocabularies.

### GO (Gene Ontology)
```json
{
  "code": "oboInOwl:id",
  "preferredName": "rdfs:label",
  "hierarchyRoles": ["part_of"],
  "sparqlPrefix": "PREFIX obo1:<...> PREFIX GO:<...>"
}
```
OBO structure with role-based hierarchy.

### HGNC
```json
{
  "code": "hgnc_id",
  "preferredName": "symbol",
  "sparqlPrefix": "PREFIX :<HGNC.owl#> PREFIX HGNC:<HGNC.owl#>"
}
```
External ontology with custom namespace.

---

## Common Mistakes and Troubleshooting

### Mistake 1: Using prefix without declaring it
```json
// WRONG
{
  "code": "ncit:NHC0",
  // Missing sparqlPrefix!
}
```

**Fix:** Add sparqlPrefix declaration
```json
{
  "code": "ncit:NHC0",
  "sparqlPrefix": "PREFIX :<ctcae6.owl#> PREFIX base:<ctcae6.owl#> PREFIX ncit:<Thesaurus.owl#>"
}
```

### Mistake 2: Prefixing local properties
```json
// WRONG for CTCAE5
{
  "code": "ctcae5:NCIt_Code",  // Unnecessary prefix
  "preferredName": "ctcae5:Preferred_Name"
}
```

**Fix:** Remove prefix for local properties
```json
{
  "code": "NCIt_Code",
  "preferredName": "Preferred_Name"
}
```

### Mistake 3: Inconsistent prefix usage
```json
// WRONG
{
  "code": "ncit:NHC0",
  "preferredName": "P108",     // Should also be ncit:P108
  "sparqlPrefix": "PREFIX ncit:<...>"
}
```

**Fix:** Be consistent - if code is external, preferredName likely is too
```json
{
  "code": "ncit:NHC0",
  "preferredName": "ncit:P108",
  "sparqlPrefix": "PREFIX ncit:<...>"
}
```

### Mistake 4: Declaring unused prefixes
```json
// CONFUSING
{
  "code": "NHC0",
  "sparqlPrefix": "PREFIX ncit:<...>"  // ncit: not used in any property
}
```

**Fix:** Only declare prefixes you actually use
```json
{
  "code": "NHC0"
  // No sparqlPrefix needed
}
```

---

## Step-by-Step: Adding a New Terminology

### 1. Analyze the OWL File

Check the namespace declarations:
```xml
<rdf:RDF xmlns="http://your-ontology.owl#"
         xmlns:external="http://external-ontology.owl#">
```

Look at property definitions:
```xml
<!-- Local property -->
<owl:AnnotationProperty rdf:about="http://your-ontology.owl#MyProperty"/>

<!-- External property -->
<owl:AnnotationProperty rdf:about="http://external-ontology.owl#TheirProperty"/>
```

### 2. Determine Property Mappings

Identify which OWL properties map to EVS concepts:
- **Code property**: Usually `NHC0`, `NCIt_Code`, `oboInOwl:id`, etc.
- **Preferred name**: Usually `P90`, `Preferred_Name`, `rdfs:label`, etc.
- **Synonyms**: Varies widely
- **Definitions**: Varies widely

### 3. Apply Prefix Rules

For each property:
```
if (property defined in your-ontology.owl) {
  propertyCode = "PropertyName"  // No prefix
} else if (property from external ontology) {
  propertyCode = "prefix:PropertyName"  // With prefix
}
```

### 4. Build sparqlPrefix

Start with your ontology's namespace:
```json
"sparqlPrefix": "PREFIX :<http://your-ontology.owl#> PREFIX base:<http://your-ontology.owl#>"
```

Add external namespaces as needed:
```json
"sparqlPrefix": "PREFIX :<your.owl#> PREFIX base:<your.owl#> PREFIX external:<external.owl#>"
```

### 5. Create the JSON File

Name: `{terminology-lowercase}.json`

Minimal example:
```json
{
  "uiLabel": "Display Name",
  "code": "propertyForCode",
  "preferredName": "propertyForName",
  "hierarchy": true
}
```

Full example with external dependencies:
```json
{
  "uiLabel": "Display Name",
  "fhirUri": "http://hl7.org/fhir/terminology-id",
  "fhirPublisher": "Publisher Name",
  "code": "external:CodeProperty",
  "preferredName": "external:NameProperty",
  "synonym": ["LocalSynonym1", "LocalSynonym2"],
  "definition": ["LocalDefinition"],
  "hierarchy": true,
  "sparqlPrefix": "PREFIX :<your.owl#> PREFIX base:<your.owl#> PREFIX external:<external.owl#>"
}
```

### 6. Test the Configuration

Load the terminology and verify:
```bash
./gradlew bootRun
# Check logs for "get config for {terminology}"
# Verify SPARQL queries are constructed correctly
```

---

## Technical Details

### How Prefixes Flow Through the System

```
1. JSON Config Load (BaseLoaderService.java)
   └─> TerminologyMetadata object created
       ├─ code = "ncit:NHC0"
       ├─ preferredName = "ncit:P108"
       └─ sparqlPrefix = "PREFIX ncit:<...>"

2. SPARQL Query Construction (QueryBuilderServiceImpl.java)
   └─> constructPrefix(terminology)
       └─ Returns: sparqlPrefix + prefix.common
   └─> constructQuery(queryProp, terminology)
       └─ Substitutes #{codeCode} with "ncit:NHC0"
       └─ Substitutes #{preferredNameCode} with "ncit:P108"

3. Query Execution (SparqlQueryManagerServiceImpl.java)
   └─> fullQuery = prefix + "\n" + query
   └─> SPARQL engine resolves ncit:P108 to full URI
   └─> Returns results with full URIs

4. Response Processing (EVSUtils.java)
   └─> getQualifiedCodeFromUri() converts URIs back to qualified codes
       └─ http://.../Thesaurus.owl#P108 → ncit:P108
   └─> getCodeFromUri() strips prefixes from concept codes
       └─ http://.../ctcae6.owl#C12345 → C12345
```

### Why Generic Queries Work for All Terminologies

**Generic query template:**
```sparql
properties=SELECT ... {
  ?x #{codeCode} "#{conceptCode}" .
  OPTIONAL { ?property #{preferredNameCode} ?propertyLabel }
}
```

**Substitution for different terminologies:**
- **NCIt**: `?x NHC0 ?code . OPTIONAL { ?property P90 ?label }`
- **CTCAE6**: `?x ncit:NHC0 ?code . OPTIONAL { ?property ncit:P108 ?label }`
- **ChEBI**: `?x oboInOwl:id ?code . OPTIONAL { ?property rdfs:label ?label }`

Each resolves correctly because:
1. Metadata provides the right property codes (with or without prefixes)
2. sparqlPrefix makes those prefixes valid in SPARQL
3. One query template serves all use cases

### When to Use Terminology-Specific Queries

The system supports `.terminology` query variants (e.g., `hierarchy.ncit`, `roles.chebi`) but these should be used SPARINGLY and ONLY when:

1. **Query structure differs** (not just property names)
2. **Different OWL patterns** (e.g., ChEBI uses simpler role structure)
3. **Performance optimization** (e.g., NCIt hierarchy has stricter filters)

**Do NOT create terminology-specific queries just for prefix handling** - that's what metadata configuration is for.

---

## FAQ

### Q: Why does CTCAE6 need `ncit:` prefix but CTCAE5 doesn't?

**A:** Different OWL architectures:
- **CTCAE5**: Self-contained - defines all properties in ctcae5.owl namespace
- **CTCAE6**: Integrated - references NCIt Thesaurus properties for consistency

CTCAE6 uses `ncit:P108` to indicate "use the P108 property from NCIt Thesaurus namespace, not from ctcae6 namespace."

### Q: Can I just hardcode prefixes in the SPARQL queries instead?

**A:** No, this creates major problems:
- Requires 240+ duplicate queries (40 base × 6 terminologies)
- Can't handle mixed namespaces (CTCAE6 uses both local and external)
- Violates separation of concerns (config mixed with query logic)
- Makes maintenance much harder

Current approach is cleaner: one set of reusable queries, configuration in metadata.

### Q: What if a property exists in multiple namespaces?

**A:** Use the prefix to disambiguate:
- `ncit:P108` = Preferred_Name from NCIt Thesaurus
- `ctcae6:P108` = If ctcae6 had its own P108 (unlikely but possible)

This is precisely why prefixes are needed in the metadata.

### Q: Do I need to declare owl:, rdfs:, rdf: in sparqlPrefix?

**A:** No, these are included in `prefix.common` and always available. Only declare:
- Your ontology's namespace (`:` and `base:`)
- External namespaces you reference (ncit:, obo:, etc.)

### Q: What about properties without any namespace like "code"?

**A:** These are treated as local properties in your ontology's default namespace. The default `prefix.graph` template handles them.

---

## Reference: Complete Property Field List

### Core Properties
- `code` - Concept code property
- `preferredName` - Preferred term property
- `conceptStatus` - Property indicating active/retired status
- `retiredStatusValue` - Value that means "retired"

### Synonym Configuration
- `synonym` - Array of synonym properties
- `synonymSource` - Qualifier for synonym source
- `synonymTermType` - Qualifier for synonym term type
- `synonymCode` - Qualifier for synonym code
- `synonymSubSource` - Qualifier for synonym subsource

### Definition Configuration
- `definition` - Array of definition properties
- `definitionSource` - Qualifier for definition source

### Mapping Configuration
- `map` - Mapping property
- `mapRelation` - Mapping relationship type
- `mapTarget` - Mapping target code
- `mapTargetTermType` - Mapping target term type
- `mapTargetTerminology` - Mapping target terminology
- `mapTargetTerminologyVersion` - Mapping target version
- `relationshipToTarget` - Relationship to target concept

### Other Configuration
- `hierarchy` - Boolean, whether terminology has hierarchy
- `hierarchyRoles` - Array of properties used for role-based hierarchy
- `sparqlPrefix` - Custom SPARQL prefix declarations
- `detailsColumns` - UI configuration for detail display
- `fhirUri` - FHIR canonical URI
- `fhirPublisher` - FHIR publisher name

---

## Support and Resources

### Related Code Files
- `src/main/java/gov/nih/nci/evs/api/service/BaseLoaderService.java` - Loads metadata JSON
- `src/main/java/gov/nih/nci/evs/api/service/QueryBuilderServiceImpl.java` - Builds SPARQL queries
- `src/main/java/gov/nih/nci/evs/api/util/EVSUtils.java` - URI/prefix conversion utilities
- `src/main/resources/sparql-queries.properties` - SPARQL query templates

### Testing Your Configuration
- Unit tests: `src/test/java/gov/nih/nci/evs/api/controller/{Terminology}SampleTest.java`
- Integration tests: Load terminology and verify metadata endpoint
- SPARQL tests: Check query construction in logs

### Contact
For questions about terminology configuration, consult the development team or refer to existing configurations as examples.

---

**Last Updated:** 2025-11-25
**Version:** 1.0
