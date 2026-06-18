#!/usr/bin/env python
"""Generate small EVSRESTAPI sample TSV files from OWL/RDF terminologies.

The generated rows are consumed by ``SampleTest`` and ``ConceptSampleTester`` in
the EVSRESTAPI test suite.  The goal is not to copy the whole OWL file.  The
goal is to find good examples that prove the loaded terminology can return
properties, roles, qualifiers, hierarchy data, and roots through the API.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any, Iterable, Optional

from lxml import etree as ET


RDF_URL = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_URL = "http://www.w3.org/2000/01/rdf-schema#"
OWL_URL = "http://www.w3.org/2002/07/owl#"
XML_URL = "http://www.w3.org/XML/1998/namespace"
XSD_URL = "http://www.w3.org/2001/XMLSchema#"
OBO_URL = "http://purl.obolibrary.org/obo/"

CANONICAL_NAMESPACE_PREFIXES = {
    RDF_URL: "rdf",
    RDFS_URL: "rdfs",
    OWL_URL: "owl",
    XML_URL: "xml",
    XSD_URL: "xsd",
}

RDF_ABOUT = f"{{{RDF_URL}}}about"
RDF_ID = f"{{{RDF_URL}}}ID"
RDF_RESOURCE = f"{{{RDF_URL}}}resource"
RDF_NODE_ID = f"{{{RDF_URL}}}nodeID"
XML_BASE = f"{{{XML_URL}}}base"

# These tags describe OWL structure.  They are not normal concept properties.
# Other parts of this script handle them as hierarchy or restriction rows.
STRUCTURAL_DIRECT_PROPERTIES = {
    "rdfs:subClassOf",
    "owl:equivalentClass",
    "owl:intersectionOf",
    "owl:unionOf",
    "rdf:type",
}

# Some OWL files have grouping classes that help build the hierarchy but should
# not become test examples themselves.  MGED's three top-level grouping classes
# are the known case.
HIERARCHY_SCAFFOLD_LOCALS_BY_TERMINOLOGY = {
    "mged": {"MGEDOntology", "MGEDCoreOntology", "MGEDExtendedOntology"},
}

# Normal rule: if the metadata JSON says codes come from a property, a class
# must have that property before we sample it.  These terminologies are
# exceptions because some real hierarchy concepts only have codes in the URI
# fragment, like ``#gene_with_protein_product``.
HIERARCHY_FALLBACK_CODE_TERMINOLOGIES = {
    "ctcae5",
    "hgnc",
}

# Why do we have per-terminology skip lists?
#
# This script does not write a general OWL audit report.  It writes test rows
# for EVSRESTAPI's Java sample tests.  A row is useful only when the Java test
# can ask the API a matching question.  Some OWLs contain import scaffolding,
# modeling restrictions, or local hierarchy hints that the EVSRESTAPI loader
# intentionally does not expose in the same shape.  Sampling those rows would
# not prove content quality; it would produce known false failures.
#
# These skips are intentionally narrow:
#
# - They disable one row family, not the whole terminology.
# - Direct properties, qualifiers, deprecated flags, and stable hierarchy rows
#   still get sampled when they are API-visible.
# - The disabled row families are reported by --report so the policy is visible
#   during QA.
#
# If one of these sets changes, regenerate the sample file and run the matching
# Java SampleTest class.  The reason should be "this OWL data is not exposed by
# EVSRESTAPI in the way the Java row type tests it", not "the row is annoying".

# DUO, MGED, NPO, OBI, and OBIB use OWL restrictions heavily for modeling and
# imported ontology structure.  The Java tester treats every restriction sample
# as "this concept has this API role target".  In these terminologies many of
# those restrictions are not loaded as Concept roles, so the row would fail even
# though the loader handled the source file as designed.
SKIP_RESTRICTION_SAMPLE_TERMINOLOGIES = {
    "duo",
    "mged",
    "npo",
    "obi",
    "obib",
}

# This hook is here for future OWLs where local/inferred hierarchy gaps make
# root rows unreliable.  Keep it empty until a generated root row fails the Java
# SampleTest and the parent cannot be inferred from the source OWL.
#
# Do not add a terminology here until generated root rows have been tried
# against the Java SampleTest.  The sampler records explicit parent references
# even when the parent class is imported or configured as hierarchy scaffold, so
# this list should stay small.
SKIP_ROOT_SAMPLE_TERMINOLOGIES: set[str] = set()

# NPO has equivalent-class hierarchy patterns that do not map cleanly to the
# Java tester's "style2" parent/child check after loading.
SKIP_PARENT_STYLE2_SAMPLE_TERMINOLOGIES = {
    "npo",
}

# Most terminologies should get one `parent-count*` row for every distinct
# parent count in the OWL.  These limits are only for OWLs where the extra
# high-count rows were proven to be loader/modeling false failures in the Java
# SampleTest:
#
# - NPO has many OWL modeling parents that collapse to 2 or 4 API parents.
# - OBI and OBIB have imported/modeling parents that are not exposed as API
#   parents for the sampled concepts.
#
# Keep the low, API-visible parent-count rows.  Only trim the noisy counts above
# the highest value that the Java tests can verify for that terminology.
MAX_PARENT_COUNT_BY_TERMINOLOGY = {
    "npo": 4,
    "obi": 1,
    "obib": 1,
}

# These keys are present in the OWL, but the EVSRESTAPI loader maps or filters
# them differently from a plain Concept property.  Keeping them out of the TSV
# avoids asking the Java tests to look for a direct property that is exposed
# through another API field or not exposed at all.
SKIP_DIRECT_PROPERTY_KEYS_BY_TERMINOLOGY = {
    "mged": {"synonym"},
    "npo": {"rdfs:comment", "synonym"},
}

# Some older OWLs put imported definition text in rdfs:comment.  EVSRESTAPI
# loaders may normalize those into definitions instead of comment properties,
# which makes a comment sample fail even though the text was parsed correctly.
COMMENT_VALUES_LOADED_AS_DEFINITIONS = (
    "[NCI_Thesaurus definition]:",
)

# Never sample OWL's built-in classes as terminology roots.
OWL_BUILTIN_CLASS_URIS = {
    f"{OWL_URL}Thing",
    f"{OWL_URL}Nothing",
}

# Metadata JSON fields that can point to real API-visible properties.  Keep
# this list in one place so future metadata fields are easy to add.
SCALAR_METADATA_PROPERTY_KEYS = (
    "code",
    "conceptStatus",
    "preferredName",
    "synonymTermType",
    "synonymSource",
    "synonymCode",
    "synonymSubSource",
    "definitionSource",
    "map",
    "mapRelation",
    "mapTarget",
    "mapTargetTermType",
    "mapTargetTerminology",
    "mapTargetTerminologyVersion",
    "relationshipToTarget",
    "subsetLink",
)

LIST_METADATA_PROPERTY_KEYS = (
    "synonym",
    "definition",
    "subsetMember",
    "subset",
)

SYNONYM_METADATA_KEYS = (
    "synonymTermType",
    "synonymSource",
    "synonymCode",
    "synonymSubSource",
)

MAP_METADATA_KEYS = (
    "mapRelation",
    "mapTarget",
    "mapTargetTermType",
    "mapTargetTerminology",
    "mapTargetTerminologyVersion",
    "relationshipToTarget",
)


def _local_part(value: Optional[str]) -> Optional[str]:
    """Return the final useful part of a QName-like string or URI."""

    if value is None:
        return None
    if "#" in value:
        return value.rsplit("#", 1)[-1]
    if "/" in value:
        return value.rstrip("/").rsplit("/", 1)[-1]
    if ":" in value:
        return value.rsplit(":", 1)[-1]
    return value


def _clean_text(value: Optional[str]) -> str:
    """Make XML text safe for one TSV row."""

    if not value:
        return ""
    # The Java sample checks sometimes compare text values exactly against the
    # values returned by EVSRESTAPI.  The loader keeps normal repeated spaces
    # inside values, so do not use ``split()`` here.  Only collapse whitespace
    # that would break the TSV row itself, such as line breaks or tabs.
    return re.sub(r"[ \t\r\n]*[\t\r\n][ \t\r\n]*", " ", value).strip()


def _append_fragment(base_uri: str, fragment: str) -> str:
    if not base_uri:
        return fragment
    if base_uri.endswith("#") or base_uri.endswith("/"):
        return f"{base_uri}{fragment}"
    return f"{base_uri}#{fragment}"


@dataclass(frozen=True)
class SampleRow:
    """One output row in the sample TSV file."""

    uri: str
    code: str
    key: str
    value: Optional[str] = None

    def to_tsv(self) -> str:
        parts = [self.uri, self.code, self.key]
        if self.value is not None:
            parts.append(self.value)
        return "\t".join(parts)


@dataclass
class TerminologyConfig:
    """Small helper around the terminology metadata JSON.

    The metadata JSON is mainly written for the EVSRESTAPI loader.  The sampler
    also needs it so it can answer questions like "which property stores the
    code?" and "which properties are synonyms?".  Keeping those lookups here
    makes the XML parsing code easier to read.
    """

    path: Path
    data: dict[str, Any]
    terminology: str

    @classmethod
    def load(cls, path: Path, terminology: Optional[str] = None) -> "TerminologyConfig":
        with path.open("r", encoding="utf-8-sig") as config_file:
            data = json.load(config_file)
        return cls(path=path, data=data, terminology=terminology or path.stem)

    @property
    def code_property(self) -> Optional[str]:
        value = self.data.get("code")
        return value if value else None

    @cached_property
    def hierarchy_roles(self) -> set[str]:
        return {role for role in self.data.get("hierarchyRoles", []) if role}

    @cached_property
    def hierarchy_scaffold_locals(self) -> set[str]:
        return HIERARCHY_SCAFFOLD_LOCALS_BY_TERMINOLOGY.get(self.terminology, set())

    @property
    def allows_hierarchy_fallback_codes(self) -> bool:
        return self.terminology in HIERARCHY_FALLBACK_CODE_TERMINOLOGIES

    @property
    def allows_restriction_samples(self) -> bool:
        return self.terminology not in SKIP_RESTRICTION_SAMPLE_TERMINOLOGIES

    @property
    def allows_root_samples(self) -> bool:
        return self.terminology not in SKIP_ROOT_SAMPLE_TERMINOLOGIES

    def allows_parent_child_style(self, style: str) -> bool:
        return not (
            style == "style2"
            and self.terminology in SKIP_PARENT_STYLE2_SAMPLE_TERMINOLOGIES
        )

    @property
    def max_parent_count_sample(self) -> Optional[int]:
        return MAX_PARENT_COUNT_BY_TERMINOLOGY.get(self.terminology)

    def disabled_sample_families(self) -> list[dict[str, str]]:
        """Return row families intentionally left out for this terminology.

        This list is written to the optional JSON report.  It keeps policy
        choices visible so a reviewer can tell the difference between "the
        sampler forgot this row type" and "this row type is a known bad match
        for the Java API check in this terminology".
        """

        disabled: list[dict[str, str]] = []
        if not self.allows_restriction_samples:
            disabled.append(
                {
                    "family": "restrictions",
                    "reason": (
                        "The Java tests check restriction rows as API roles, "
                        "but this OWL uses restrictions for modeling or imports "
                        "that EVSRESTAPI does not expose as concept roles."
                    ),
                }
            )
        if not self.allows_root_samples:
            disabled.append(
                {
                    "family": "roots",
                    "reason": (
                        "Some local OWL roots gain parents after EVSRESTAPI "
                        "loads inferred or imported hierarchy."
                    ),
                }
            )
        if not self.allows_parent_child_style("style2"):
            disabled.append(
                {
                    "family": "parent-style2/child-style2",
                    "reason": (
                        "Equivalent-class hierarchy patterns do not map cleanly "
                        "to the Java tester's style2 parent/child check."
                    ),
                }
            )
        if self.max_parent_count_sample is not None:
            disabled.append(
                {
                    "family": f"parent-count>{self.max_parent_count_sample}",
                    "reason": (
                        "Higher parent-count rows are OWL modeling/import "
                        "counts that EVSRESTAPI does not expose as exact API "
                        "parent counts for this terminology."
                    ),
                }
            )
        skipped_keys = SKIP_DIRECT_PROPERTY_KEYS_BY_TERMINOLOGY.get(self.terminology)
        if skipped_keys:
            disabled.append(
                {
                    "family": "direct-properties",
                    "keys": ", ".join(sorted(skipped_keys)),
                    "reason": (
                        "These OWL keys are mapped or filtered by the loader "
                        "instead of being returned as plain Concept properties."
                    ),
                }
            )
        return disabled

    def class_has_sampleable_code(self, has_configured_code: bool) -> bool:
        """Return whether a class has a good enough code to sample.

        Most terminologies should only sample classes that have the configured
        code property.  HGNC and CTCAE5 are special because some real hierarchy
        concepts use the URI fragment as the API code.
        """

        return (
            not self.code_property
            or has_configured_code
            or self.allows_hierarchy_fallback_codes
        )

    @cached_property
    def unique_qualifier_properties(self) -> set[str]:
        """Qualifier properties where each different value needs a row."""

        keys = {
            self.data.get("synonymSource"),
            self.data.get("synonymTermType"),
            self.data.get("definitionSource"),
        }
        return {key for key in keys if key}

    @cached_property
    def preferred_sample_keys(self) -> list[str]:
        """Return property names using the spelling from metadata JSON."""

        keys: list[str] = []

        def add(value: Optional[str]) -> None:
            if value and value not in keys:
                keys.append(value)

        for key in SCALAR_METADATA_PROPERTY_KEYS:
            add(self.data.get(key))
        for list_key in LIST_METADATA_PROPERTY_KEYS:
            values = self.data.get(list_key)
            if isinstance(values, list):
                for value in values:
                    add(value)
        return keys

    @cached_property
    def preferred_key_by_local_part(self) -> dict[str, str]:
        """Map short property names back to the metadata spelling."""

        result: dict[str, str] = {}
        for key in self.preferred_sample_keys:
            local = _local_part(key)
            if local:
                result.setdefault(local, key)
        return result

    def matches(self, actual: str, configured: Optional[str]) -> bool:
        """Return true when two property names mean the same thing.

        OWL files are not consistent.  One file may say ``ncit:P108`` while
        metadata says ``P108``.  Exact matches are best, but matching the short
        local name keeps equivalent spellings working.
        """

        if not configured:
            return False
        return actual == configured or _local_part(actual) == _local_part(configured)

    def matches_any(self, actual: str, configured_values: Iterable[Optional[str]]) -> bool:
        return any(self.matches(actual, configured) for configured in configured_values)

    def matches_any_metadata_key(self, actual: str, metadata_keys: Iterable[str]) -> bool:
        return self.matches_any(actual, (self.data.get(key) for key in metadata_keys))

    def preferred_key(self, actual: str) -> str:
        """Prefer the metadata spelling when it names this property."""

        if actual in self.preferred_sample_keys:
            return actual
        local = _local_part(actual)
        return self.preferred_key_by_local_part.get(local or "", actual)

    def is_unique_qualifier_property(self, key: str) -> bool:
        return self.matches_any(key, self.unique_qualifier_properties)


@dataclass
class QNameResolver:
    """Convert XML names and URI resources into sample-file names.

    XML parsers expose names as ``{namespace}local``.  The sample files need
    friendlier names such as ``rdfs:label``, ``ncit:P108``, or ``IAO_0000115``.
    This class owns that translation.
    """

    namespaces: dict[Optional[str], str]
    base_uri: str = ""

    @classmethod
    def from_root(cls, root: ET._Element) -> "QNameResolver":
        namespaces = dict(root.nsmap or {})
        namespaces.setdefault("rdf", RDF_URL)
        namespaces.setdefault("rdfs", RDFS_URL)
        namespaces.setdefault("owl", OWL_URL)
        namespaces.setdefault("xml", XML_URL)
        namespaces.setdefault("xsd", XSD_URL)
        base_uri = root.get(XML_BASE) or namespaces.get(None, "")
        return cls(namespaces=namespaces, base_uri=base_uri)

    def local_name(self, tag: str) -> str:
        if tag.startswith("{"):
            return tag.split("}", 1)[1]
        return tag

    def tag_to_key(self, tag: str) -> str:
        """Convert an XML tag into the key written to the TSV."""

        if not tag.startswith("{"):
            return tag
        uri, local = tag[1:].split("}", 1)
        canonical_prefix = CANONICAL_NAMESPACE_PREFIXES.get(uri)
        if canonical_prefix:
            return f"{canonical_prefix}:{local}"
        prefix = self.prefix_for_uri(uri)
        if prefix is None:
            return local
        # Historical sample files omit the ``obo:`` prefix for OBO properties.
        if prefix == "obo" and uri.rstrip("/") == OBO_URL.rstrip("/"):
            return local
        return f"{prefix}:{local}"

    def prefix_for_uri(self, uri: str) -> Optional[str]:
        for prefix, namespace in self.namespaces.items():
            if namespace == uri:
                return prefix if prefix else None
        return None

    def canonicalize_resource(self, value: Optional[str]) -> Optional[str]:
        """Turn a short resource like ``#C123`` into a full URI."""

        if not value:
            return None
        if value.startswith("#"):
            return _append_fragment(self.base_uri, value[1:])
        return value

    def element_identifier(self, element: ET._Element) -> Optional[str]:
        """Return the URI or blank-node id for an OWL element."""

        about = element.get(RDF_ABOUT)
        if about:
            return self.canonicalize_resource(about)
        rdf_id = element.get(RDF_ID)
        if rdf_id:
            return _append_fragment(self.base_uri, rdf_id)
        node_id = element.get(RDF_NODE_ID)
        if node_id:
            return node_id
        return None

    def resource_to_key(self, value: str) -> str:
        """Convert a URI into a short code/key when we do not have an index."""

        value = self.canonicalize_resource(value) or value
        # Always use standard prefixes for RDF/RDFS/OWL/etc.  Source OWL files
        # can choose any prefix, but the sample tests expect names like
        # ``owl:deprecated``.
        for namespace, prefix in CANONICAL_NAMESPACE_PREFIXES.items():
            if value.startswith(namespace):
                return f"{prefix}:{value[len(namespace):]}"
        for prefix, namespace in self.namespaces.items():
            if not namespace or not value.startswith(namespace):
                continue
            local = value[len(namespace):]
            if local.startswith("#"):
                local = local[1:]
            if not local:
                continue
            if prefix in (None, "", "obo"):
                # OBO occasionally stores a property under a URI like
                # http://purl.obolibrary.org/obo/cl#lacks_part.  EVSRESTAPI
                # exposes that role by the final name, lacks_part.  Keeping
                # cl#lacks_part in the sample key makes the Java metadata URL
                # treat the text after # as a browser fragment, so the server
                # only receives /role/cl.
                if "#" in local:
                    return local.rsplit("#", 1)[-1]
                return local
            return f"{prefix}:{local}"
        return _local_part(value) or value

    def tag_matches(self, tag: str, configured: Optional[str]) -> bool:
        if not configured:
            return False
        key = self.tag_to_key(tag)
        return key == configured or _local_part(key) == _local_part(configured)


@dataclass
class ConceptNode:
    """The pieces we need after reading one top-level OWL class."""

    uri: str
    code: str
    sampleable: bool
    deprecated: bool


@dataclass
class PropertyRegistry:
    """Keep one sample row per property, except for known multi-value cases.

    Most properties only need one example.  NCIt concept status is different:
    the Java tests need examples for multiple status values.  ``multi_sample_keys``
    lists the keys where multiple values should be kept.
    """

    multi_sample_keys: set[str]
    rows: "OrderedDict[str, SampleRow]" = field(default_factory=OrderedDict)
    multi_rows: "OrderedDict[tuple[str, str], SampleRow]" = field(default_factory=OrderedDict)

    def is_multi_sample_key(self, key: str) -> bool:
        return key in self.multi_sample_keys or (_local_part(key) or key) in self.multi_sample_keys

    def add(self, row: SampleRow) -> None:
        if self.is_multi_sample_key(row.key) and row.value is not None:
            self.multi_rows.setdefault((row.key, row.value), row)
        else:
            self.rows.setdefault(row.key, row)

    def values(self) -> Iterable[SampleRow]:
        yield from self.rows.values()
        yield from self.multi_rows.values()


@dataclass
class SampleCollector:
    """Collect sample rows from one OWL file.

    This runs in two passes.  The first pass learns the code for every class
    and property URI.  The second pass writes sample rows using those codes.
    Both passes stream the XML so large OWL files do not have to fit fully in
    memory.
    """

    config: TerminologyConfig
    resolver: Optional[QNameResolver] = None
    uri_to_code: dict[str, str] = field(default_factory=dict)
    class_uris: "OrderedDict[str, None]" = field(default_factory=OrderedDict)
    sampleable_class_uris: "OrderedDict[str, None]" = field(default_factory=OrderedDict)
    # These sets store both full URIs and short codes.  Some checks see one
    # form, and some checks see the other.
    object_property_uris: set[str] = field(default_factory=set)
    annotation_property_uris: set[str] = field(default_factory=set)
    datatype_property_keys: set[str] = field(default_factory=set)
    deprecated_uris: set[str] = field(default_factory=set)
    parent_style1: Optional[tuple[str, str]] = None
    parent_style2: Optional[tuple[str, str]] = None
    all_parents: "OrderedDict[str, list[str]]" = field(default_factory=OrderedDict)
    all_children: "OrderedDict[str, list[str]]" = field(default_factory=OrderedDict)
    non_root_class_uris: set[str] = field(default_factory=set)
    axiom_rows: "OrderedDict[str, SampleRow]" = field(default_factory=OrderedDict)
    qualifier_assertions: set[tuple[str, ...]] = field(default_factory=set)
    role_assertions: set[tuple[str, str, str]] = field(default_factory=set)
    property_registry: PropertyRegistry = field(init=False)

    def __post_init__(self) -> None:
        # P310 is NCIt's concept status property.  Keep the short name because
        # NCIt files do not always use the same prefix.
        concept_status = self.config.data.get("conceptStatus") or ""
        multi_keys = {"P310"}
        if concept_status:
            multi_keys.add(concept_status)
            local = _local_part(concept_status)
            if local:
                multi_keys.add(local)
        self.property_registry = PropertyRegistry(multi_sample_keys=multi_keys)

    def generate(self, owl_path: Path) -> list[SampleRow]:
        """Generate all sample rows for one OWL file."""

        # This collector stores state while it runs, so use one collector per
        # OWL file.  ``generate_samples`` creates a new one each time.
        self.build_indexes(owl_path)
        self.collect_samples(owl_path)
        return self.ordered_rows()

    def build_indexes(self, owl_path: Path) -> None:
        """First pass: remember URI-to-code mappings needed later."""

        for event, element in self._iterparse(owl_path):
            if event == "start" and self.resolver is None:
                self.resolver = QNameResolver.from_root(element)
                continue
            if event != "end" or not self._is_top_level(element):
                continue

            tag = self._local_name(element)
            if tag == "Class":
                concept = self._concept_from_element(element)
                if concept:
                    self._remember_concept(concept)
            elif tag == "ObjectProperty":
                self._index_property(element, self.object_property_uris)
            elif tag == "AnnotationProperty":
                self._index_property(element, self.annotation_property_uris)
            elif tag == "DatatypeProperty":
                self._index_datatype_property(element)
            elif self._has_rdf_type(element, "owl:ObjectProperty"):
                # MGED has top-level owl:FunctionalProperty records that are
                # also object properties.  EVSRESTAPI exposes those roles by
                # their configured code, so they need to be in uri_to_code.
                self._index_property(element, self.object_property_uris)
            elif self._has_rdf_type(element, "owl:AnnotationProperty"):
                self._index_property(element, self.annotation_property_uris)
            elif self._has_rdf_type(element, "owl:DatatypeProperty"):
                self._index_datatype_property(element)

            self._clear_top_level(element)

    def collect_samples(self, owl_path: Path) -> None:
        """Second pass: collect rows now that codes are known."""

        for event, element in self._iterparse(owl_path):
            if event == "start" and self.resolver is None:
                self.resolver = QNameResolver.from_root(element)
                continue
            if event != "end" or not self._is_top_level(element):
                continue

            tag = self._local_name(element)
            if tag == "Class":
                self._collect_class_samples(element)
            elif tag == "Axiom":
                self._collect_axiom_sample(element)

            self._clear_top_level(element)

    def ordered_rows(self) -> list[SampleRow]:
        """Return rows in the order used by the sample files."""

        rows = list(self.property_registry.values())
        rows.extend(self.axiom_rows.values())
        rows.extend(self._hierarchy_rows())
        rows.extend(self._root_rows())
        return rows

    def report(self, rows: list[SampleRow]) -> dict[str, Any]:
        return {
            "terminology": self.config.terminology,
            "disabledSampleFamilies": self.config.disabled_sample_families(),
            "sampleRows": len(rows),
            "classes": len(self.class_uris),
            "sampleableClasses": len(self.sampleable_class_uris),
            "objectProperties": len(self.object_property_uris),
            "annotationProperties": len(self.annotation_property_uris),
            "datatypeProperties": len(self.datatype_property_keys),
            "deprecatedClasses": len(self.deprecated_uris),
            "parentRelationships": sum(len(parents) for parents in self.all_parents.values()),
            "axiomSamples": len(self.axiom_rows),
        }

    def _remember_concept(self, concept: ConceptNode) -> None:
        """Add one concept to the indexes used by both passes."""

        self.class_uris.setdefault(concept.uri, None)
        if concept.sampleable:
            self.sampleable_class_uris.setdefault(concept.uri, None)
        self.uri_to_code[concept.uri] = concept.code

    def _iterparse(self, owl_path: Path):
        # Release OWL files should be valid XML.  If a file is broken, it is
        # better to fail here than to quietly write a partial sample file.
        return ET.iterparse(str(owl_path), events=("start", "end"), recover=False, huge_tree=True)

    def _local_name(self, element: ET._Element) -> str:
        assert self.resolver is not None
        return self.resolver.local_name(element.tag)

    def _is_top_level(self, element: ET._Element) -> bool:
        parent = element.getparent()
        if parent is None:
            return False
        assert self.resolver is not None
        return self.resolver.local_name(parent.tag) == "RDF"

    def _clear_top_level(self, element: ET._Element) -> None:
        # Clear finished top-level XML elements so memory stays low while
        # reading large OWL files.
        parent = element.getparent()
        element.clear()
        if parent is not None:
            while element.getprevious() is not None:
                del parent[0]

    def _element_text(self, element: ET._Element) -> str:
        # ``method="text"`` gets all text inside the element and decodes XML
        # entities.  ``_clean_text`` then makes it safe for one TSV row.
        return _clean_text(ET.tostring(element, method="text", encoding="unicode"))

    def _element_value(self, element: ET._Element) -> tuple[Optional[str], bool]:
        assert self.resolver is not None
        resource = self._resource_from_element(element)
        if resource:
            return resource, True
        text = self._element_text(element)
        return (text or None), False

    def _resource_from_element(self, element: ET._Element) -> Optional[str]:
        assert self.resolver is not None
        # Most OWL links use rdf:resource.  Some files use rdf:about, rdf:ID,
        # or a nested child instead, so handle those forms here.
        resource = element.get(RDF_RESOURCE) or element.get(RDF_ABOUT)
        if resource:
            return self.resolver.canonicalize_resource(resource)
        rdf_id = element.get(RDF_ID)
        if rdf_id:
            return _append_fragment(self.resolver.base_uri, rdf_id)
        for child in element:
            nested = self.resolver.element_identifier(child)
            if nested:
                return nested
        return None

    def _configured_code(self, element: ET._Element) -> tuple[Optional[str], bool]:
        assert self.resolver is not None
        configured = self.config.code_property
        if not configured:
            return None, False
        # Some metadata configs say the code comes from an RDF attribute instead
        # of a child element.
        if configured == "rdf:ID":
            value = element.get(RDF_ID)
            return (value or None, bool(value))
        if configured == "rdf:about":
            value = element.get(RDF_ABOUT)
            local = _local_part(value)
            return (local, bool(local))
        for child in element:
            if self.resolver.tag_matches(child.tag, configured):
                value = self._element_text(child)
                return (value or None, bool(value))
        return None, False

    def _concept_from_element(self, element: ET._Element) -> Optional[ConceptNode]:
        assert self.resolver is not None
        uri = self.resolver.element_identifier(element)
        if not uri or uri.endswith("#"):
            return None
        configured_code, has_configured_code = self._configured_code(element)
        fallback_code = self._code_from_uri(uri)
        code = configured_code or fallback_code
        has_code_for_sampling = self.config.class_has_sampleable_code(has_configured_code)
        sampleable = (
            bool(code)
            and uri not in OWL_BUILTIN_CLASS_URIS
            and has_code_for_sampling
        )
        deprecated = self._is_deprecated(element)
        if deprecated:
            self.deprecated_uris.add(uri)
        return ConceptNode(
            uri=uri,
            code=code,
            sampleable=sampleable,
            deprecated=deprecated,
        )

    def _code_from_uri(self, uri: str) -> str:
        assert self.resolver is not None
        key = self.resolver.resource_to_key(uri)
        return _local_part(key) or key

    def _index_property(self, element: ET._Element, target_set: set[str]) -> None:
        assert self.resolver is not None
        uri = self.resolver.element_identifier(element)
        if not uri:
            return
        configured_code, _ = self._configured_code(element)
        code = configured_code or self.resolver.resource_to_key(uri)
        self.uri_to_code[uri] = code
        # Store both shapes.  OWL links usually use full URIs, while metadata
        # comparisons often use short codes.
        target_set.add(uri)
        target_set.add(code)

    def _index_datatype_property(self, element: ET._Element) -> None:
        assert self.resolver is not None
        uri = self.resolver.element_identifier(element)
        if not uri:
            return
        key = self.resolver.resource_to_key(uri)
        self.datatype_property_keys.add(uri)
        self.datatype_property_keys.add(key)
        local = _local_part(key)
        if local:
            self.datatype_property_keys.add(local)

    def _has_rdf_type(self, element: ET._Element, type_key: str) -> bool:
        """Return true when an element has the requested rdf:type.

        Some OWL files do not use the exact top-level tag we expect.  For
        example, MGED stores a few roles as owl:FunctionalProperty with an
        rdf:type child saying they are also owl:ObjectProperty.  Checking the
        rdf:type lets us index those records the same way EVSRESTAPI loads
        them.
        """

        assert self.resolver is not None
        for child in element:
            if self.resolver.tag_to_key(child.tag) != "rdf:type":
                continue
            resource = self._resource_from_element(child)
            if resource and self.resolver.resource_to_key(resource) == type_key:
                return True
        return False

    def _is_deprecated(self, element: ET._Element) -> bool:
        assert self.resolver is not None
        for child in element:
            key = self.resolver.tag_to_key(child.tag)
            if key != "owl:deprecated":
                continue
            return self._element_text(child).lower() == "true"
        return False

    def _collect_class_samples(self, element: ET._Element) -> None:
        concept = self._concept_from_element(element)
        if not concept:
            return
        self._remember_concept(concept)
        if not concept.sampleable:
            return

        self._collect_direct_properties(element, concept)
        self._collect_restrictions(element, concept)
        self._collect_parent_relationships(element, concept)

    def _collect_direct_properties(self, element: ET._Element, concept: ConceptNode) -> None:
        assert self.resolver is not None
        for child in element:
            key = self.resolver.tag_to_key(child.tag)
            key = self.config.preferred_key(key)
            # These are handled by hierarchy/restriction code, not as normal
            # properties.  The code property is already used in column 2.
            if key in STRUCTURAL_DIRECT_PROPERTIES:
                continue
            if self.config.matches(key, self.config.code_property):
                continue
            value, is_resource = self._element_value(child)
            if value is None:
                continue
            # Only ``owl:deprecated true`` is useful for the tests.
            if key == "owl:deprecated" and value.lower() == "false":
                continue
            if is_resource:
                value = self._code_for_resource(value)
            if self._skip_direct_property_sample(key, value):
                continue
            self.property_registry.add(SampleRow(concept.uri, concept.code, key, value))

    def _skip_direct_property_sample(self, key: str, value: str) -> bool:
        """Return true when a direct property row is known to be noisy."""

        # For code-less OBO-family configs, the API code comes from the URI.
        # Some imported classes have owl:deprecated=true in the source OWL but
        # are still active in the loaded terminology.  Without a configured code
        # property, those rows are more likely to be imported-ontology noise.
        if key == "owl:deprecated" and not self.config.code_property:
            return True
        skipped_keys = SKIP_DIRECT_PROPERTY_KEYS_BY_TERMINOLOGY.get(
            self.config.terminology, set()
        )
        if key in skipped_keys:
            return True
        if key == "rdfs:comment" and value.startswith(COMMENT_VALUES_LOADED_AS_DEFINITIONS):
            return True
        return False

    def _collect_restrictions(self, element: ET._Element, concept: ConceptNode) -> None:
        if not self.config.allows_restriction_samples:
            return
        for restriction in element.iterdescendants():
            row = self._restriction_row(restriction, concept)
            if row:
                self.property_registry.add(row)

    def _restriction_row(
        self, restriction: ET._Element, concept: ConceptNode
    ) -> Optional[SampleRow]:
        """Build a sample row for one class restriction, or ``None`` to skip it."""

        path = self._restriction_path(restriction)
        if path is None:
            return None

        parts = self._restriction_role_and_target(restriction)
        if parts is None:
            return None
        role_resource, role_key, target_resource = parts

        # Datatype restrictions point to literal values, not concept targets.
        # The Java tests only check object roles here.
        if self._is_datatype_property(role_resource, role_key):
            return None
        # Hierarchy roles are parent/child links, not normal roles.
        if role_key in self.config.hierarchy_roles:
            return None

        target_code = self._code_for_resource(target_resource)
        assertion = (concept.code, role_key, target_code)
        if assertion in self.role_assertions:
            return None
        self.role_assertions.add(assertion)
        return SampleRow(concept.uri, concept.code, f"{path}~{role_key}", target_code)

    def _restriction_role_and_target(
        self, restriction: ET._Element
    ) -> Optional[tuple[str, str, str]]:
        """Return the role resource, role key, and target resource for a restriction."""

        if self._local_name(restriction) != "Restriction":
            return None
        role_resource = self._restriction_child_resource(restriction, "onProperty")
        target_resource = (
            self._restriction_child_resource(restriction, "someValuesFrom")
            or self._restriction_child_resource(restriction, "allValuesFrom")
        )
        if not role_resource or not target_resource:
            return None
        return role_resource, self._code_for_resource(role_resource), target_resource

    def _restriction_path(self, restriction: ET._Element) -> Optional[str]:
        """Return the row-key prefix for this restriction."""

        for ancestor in restriction.iterancestors():
            ancestor_key = self._key_for_element(ancestor)
            if ancestor_key == "rdfs:subClassOf":
                return "rdfs:subClassOf/owl:Restriction"
            if ancestor_key == "owl:equivalentClass":
                return "owl:equivalentClass/owl:Restriction"
            if ancestor_key == "owl:Class" and self._is_top_level(ancestor):
                return None
        return None

    def _restriction_child_resource(self, restriction: ET._Element, child_name: str) -> Optional[str]:
        for child in restriction:
            if self._local_name(child) == child_name:
                return self._resource_from_element(child)
        return None

    def _is_datatype_property(self, resource: str, key: str) -> bool:
        local = _local_part(key)
        return (
            resource in self.datatype_property_keys
            or key in self.datatype_property_keys
            or (local is not None and local in self.datatype_property_keys)
        )

    def _collect_parent_relationships(self, element: ET._Element, concept: ConceptNode) -> None:
        for child in element:
            child_key = self._key_for_element(child)
            if child_key == "rdfs:subClassOf":
                parents, direct_parent = self._subclass_parent_resources(child)
                for parent in parents:
                    if self._record_hierarchy_parent(concept.uri, parent):
                        if (
                            direct_parent
                            and parent in self.sampleable_class_uris
                            and self.parent_style1 is None
                        ):
                            self.parent_style1 = (concept.uri, parent)

            elif child_key == "owl:equivalentClass":
                # Some OWLs express a parent inside an equivalentClass block.
                # Keep this old behavior because the Java tests check this
                # hierarchy style separately from direct rdfs:subClassOf.
                for parent in self._class_expression_parent_resources(child):
                    if self._record_hierarchy_parent(concept.uri, parent):
                        if (
                            parent in self.sampleable_class_uris
                            and self.parent_style2 is None
                        ):
                            self.parent_style2 = (concept.uri, parent)

    def _subclass_is_restriction(self, subclass_element: ET._Element) -> bool:
        return any(self._local_name(child) == "Restriction" for child in subclass_element)

    def _hierarchy_restriction_parent_resource(
        self, subclass_element: ET._Element
    ) -> Optional[str]:
        """Return a parent encoded as a configured hierarchy-role restriction.

        OBO-style OWLs sometimes use a restriction like "part_of some X" as a
        hierarchy edge.  The metadata JSON tells us which roles are hierarchy
        roles.  Those restrictions should not become role samples, but they do
        matter for roots, parent counts, child counts, and paths.
        """

        for restriction in subclass_element.iterdescendants():
            parts = self._restriction_role_and_target(restriction)
            if parts is None:
                continue
            role_resource, role_key, target_resource = parts
            if self._is_datatype_property(role_resource, role_key):
                continue
            if role_key in self.config.hierarchy_roles:
                return target_resource
        return None

    def _subclass_parent_resources(
        self, subclass_element: ET._Element
    ) -> tuple[list[str], bool]:
        """Return parent resources for direct subclass hierarchy."""

        parent = self._direct_resource(subclass_element)
        if parent:
            return [parent], True
        if self._subclass_is_restriction(subclass_element):
            hierarchy_parent = self._hierarchy_restriction_parent_resource(subclass_element)
            return ([hierarchy_parent] if hierarchy_parent else []), False
        return self._class_expression_parent_resources(subclass_element), True

    def _class_expression_parent_resources(self, element: ET._Element) -> list[str]:
        """Return named parents from the top level of a class expression.

        OWL class expressions can nest restrictions inside restrictions.  Only
        the named class at the top of the expression is hierarchy evidence.
        Deeper named classes are role targets or logical details, not parents.
        """

        direct = self._direct_resource(element)
        if direct:
            return [direct]

        parents: list[str] = []
        for child in element:
            child_key = self._key_for_element(child)
            if child_key in {"owl:Class", "rdf:Description"}:
                self._append_parent_resource(parents, self._direct_resource(child))
                self._append_top_level_collection_parents(parents, child)
        return parents

    def _append_top_level_collection_parents(
        self, parents: list[str], class_expression: ET._Element
    ) -> None:
        for child in class_expression:
            child_key = self._key_for_element(child)
            if child_key not in {"owl:intersectionOf", "owl:unionOf"}:
                continue
            for member in child:
                member_key = self._key_for_element(member)
                if member_key in {"owl:Class", "rdf:Description"}:
                    self._append_parent_resource(parents, self._direct_resource(member))

    def _append_parent_resource(
        self, parents: list[str], parent: Optional[str]
    ) -> None:
        if parent and parent not in parents:
            parents.append(parent)

    def _direct_resource(self, element: ET._Element) -> Optional[str]:
        assert self.resolver is not None
        resource = element.get(RDF_RESOURCE) or element.get(RDF_ABOUT)
        if resource:
            return self.resolver.canonicalize_resource(resource)
        rdf_id = element.get(RDF_ID)
        if rdf_id:
            return _append_fragment(self.resolver.base_uri, rdf_id)
        return None

    def _record_hierarchy_parent(self, child_uri: str, parent_uri: str) -> bool:
        """Record a parent edge if it is useful for Java sample testing.

        Imported parents may not have a full class record in the release OWL.
        They still matter for root and parent-count checks, because EVSRESTAPI
        can load those parents from imports.  Exact child-count checks are more
        conservative and only count children under parents that are sampleable
        from this OWL file.

        Configured scaffold parents are even narrower.  They are helper classes
        we do not want as sample rows, but their children are still not roots.
        Those edges only suppress root rows.
        """

        if self._is_hierarchy_scaffold_uri(child_uri):
            return False
        if self._is_hierarchy_scaffold_uri(parent_uri):
            self.non_root_class_uris.add(child_uri)
            return False
        self._add_parent(
            child_uri,
            parent_uri,
            count_child=parent_uri in self.sampleable_class_uris,
        )
        return True

    def _add_parent(self, child_uri: str, parent_uri: str, count_child: bool = True) -> None:
        parents = self.all_parents.setdefault(child_uri, [])
        if parent_uri not in parents:
            parents.append(parent_uri)
        if not count_child:
            return
        children = self.all_children.setdefault(parent_uri, [])
        if child_uri not in children:
            children.append(child_uri)

    def _is_hierarchy_scaffold_uri(self, uri: str) -> bool:
        local = _local_part(uri)
        return bool(local and local in self.config.hierarchy_scaffold_locals)

    def _collect_axiom_sample(self, element: ET._Element) -> None:
        assert self.resolver is not None
        source_uri: Optional[str] = None
        source_property: Optional[str] = None
        target_value: Optional[str] = None
        target_is_complex = False
        qualifiers: list[tuple[str, str]] = []

        for child in element:
            key = self.resolver.tag_to_key(child.tag)
            if key == "owl:annotatedSource":
                source_uri = self._resource_from_element(child)
            elif key == "owl:annotatedProperty":
                resource = self._resource_from_element(child)
                if resource:
                    source_property = self._code_for_annotated_property(resource)
            elif key == "owl:annotatedTarget":
                # Complex targets are nested OWL structures.  The Java tests
                # need simple values they can look up on a concept.
                if len(child):
                    target_is_complex = True
                else:
                    value, is_resource = self._element_value(child)
                    if value:
                        target_value = self._code_for_resource(value) if is_resource else value
            elif not key.startswith("owl:annotated"):
                value, is_resource = self._element_value(child)
                if value:
                    qualifier_key = self.config.preferred_key(key)
                    value = self._qualifier_value(qualifier_key, value, is_resource)
                    qualifiers.append((qualifier_key, value))

        if (
            target_is_complex
            or not source_uri
            or not source_property
            or target_value is None
            or source_uri not in self.sampleable_class_uris
        ):
            return

        source_code = self.uri_to_code[source_uri]
        for qualifier_key, qualifier_value in qualifiers:
            if self._is_java_fragile_definition_source_row(
                source_property, qualifier_key, target_value
            ):
                continue
            # Different TSV rows can still test the same thing in Java.  Track
            # the Java-visible shape so we do not keep duplicate samples.
            assertion = self._qualifier_assertion(
                source_code, source_property, qualifier_key, target_value, qualifier_value
            )
            if assertion in self.qualifier_assertions:
                continue
            self.qualifier_assertions.add(assertion)
            sample_key = f"qualifier-{source_property}~{qualifier_key}"
            unique_key = sample_key
            if self.config.is_unique_qualifier_property(qualifier_key):
                sample_key = f"{sample_key}~{qualifier_value}"
                unique_key = sample_key
            self.axiom_rows.setdefault(
                unique_key,
                SampleRow(source_uri, source_code, sample_key, f"{target_value}~{qualifier_value}"),
            )

    def _is_java_fragile_definition_source_row(
        self, source_property: str, qualifier_key: str, target_value: str
    ) -> bool:
        """Return True when the Java sample test would turn a good row bad.

        ``ConceptSampleTester`` standardizes sample values before it checks
        them.  That is usually helpful, but definition-source qualifier checks
        compare the standardized sample text to the raw definition text from
        EVSRESTAPI.  If the OWL definition intentionally has repeated spaces,
        the sample row cannot pass that exact comparison even though the
        sampler preserved the source text correctly.  Skipping just those rows
        avoids noisy false negatives while still sampling ordinary definitions
        and ordinary definition-source qualifiers.
        """

        definition_keys = self.config.data.get("definition") or []
        definition_source_key = self.config.data.get("definitionSource")
        if not definition_source_key:
            return False
        return (
            self.config.matches_any(source_property, definition_keys)
            and self.config.matches(qualifier_key, definition_source_key)
            and re.search(r"\s{2,}", target_value) is not None
        )

    def _qualifier_assertion(
        self,
        source_code: str,
        source_property: str,
        qualifier_key: str,
        target_value: str,
        qualifier_value: str,
    ) -> tuple[str, ...]:
        """Return the qualifier shape that the Java tester checks."""

        synonym_keys = self.config.data.get("synonym") or []
        if self.config.matches_any(source_property, synonym_keys):
            if self.config.matches_any_metadata_key(qualifier_key, SYNONYM_METADATA_KEYS):
                return (
                    "synonym-metadata",
                    source_code,
                    self.config.preferred_key(qualifier_key),
                    target_value,
                    qualifier_value,
                )

        definition_keys = self.config.data.get("definition") or []
        if self.config.matches_any(source_property, definition_keys):
            if self.config.matches(qualifier_key, self.config.data.get("definitionSource")):
                return (
                    "definition-metadata",
                    source_code,
                    self.config.preferred_key(qualifier_key),
                    target_value,
                    qualifier_value,
                )

        map_key = self.config.data.get("map")
        if map_key and self.config.matches(source_property, map_key):
            if self.config.matches_any_metadata_key(qualifier_key, MAP_METADATA_KEYS):
                return (
                    "map-metadata",
                    source_code,
                    self.config.preferred_key(qualifier_key),
                    target_value,
                    qualifier_value,
                )

        return (
            "qualified-property",
            source_code,
            source_property,
            qualifier_key,
            target_value,
            qualifier_value,
        )

    def _code_for_annotated_property(self, resource: str) -> str:
        # Qualifier rows need the API-facing property code in the part after
        # "qualifier-".  If the property was indexed in pass one, use that code
        # instead of the XML prefix spelling such as "ncit:P90".
        return self._code_for_resource(resource)

    def _qualifier_value(self, qualifier_key: str, value: str, is_resource: bool) -> str:
        """Return the value shape EVSRESTAPI exposes for an axiom qualifier."""

        if not is_resource:
            return value
        canonical = self.resolver.canonicalize_resource(value) if self.resolver else value
        # EVSRESTAPI keeps hasDbXref values as-is, but most other qualifier
        # resources are converted to their final URI piece.  ChEBI synonym
        # term types are the important example: the OWL value is
        # ``.../chebi/IUPAC_NAME`` and the API value is ``IUPAC_NAME``.
        if self.config.matches(qualifier_key, "oboInOwl:hasDbXref"):
            return canonical or value
        return _local_part(canonical or value) or value

    def _code_for_resource(self, resource: str) -> str:
        assert self.resolver is not None
        canonical = self.resolver.canonicalize_resource(resource) or resource
        return self.uri_to_code.get(canonical) or self.resolver.resource_to_key(canonical)

    def _key_for_element(self, element: ET._Element) -> str:
        assert self.resolver is not None
        return self.resolver.tag_to_key(element.tag)

    def _hierarchy_rows(self) -> list[SampleRow]:
        rows: list[SampleRow] = []
        rows.extend(self._parent_child_style_rows(self.parent_style1, "style1"))
        rows.extend(self._parent_child_style_rows(self.parent_style2, "style2"))
        max_children_row = self._max_children_row()
        if max_children_row:
            rows.append(max_children_row)
        rows.extend(self._parent_count_rows())
        return rows

    def _parent_child_style_rows(
        self, pair: Optional[tuple[str, str]], style: str
    ) -> list[SampleRow]:
        """Return parent-style/child-style rows for one hierarchy shape."""

        if not pair or not self.config.allows_parent_child_style(style):
            return []
        child_uri, parent_uri = pair
        # This row looks odd on purpose: column 1 is the child URI, but column 2
        # is the parent code.  The Java tester queries the parent and then checks
        # that the child appears under it.
        return [
            SampleRow(
                child_uri,
                self._code_for_resource(child_uri),
                f"parent-{style}",
                self._code_for_resource(parent_uri),
            ),
            SampleRow(
                child_uri,
                self._code_for_resource(parent_uri),
                f"child-{style}",
                self._code_for_resource(child_uri),
            ),
        ]

    def _max_children_row(self) -> Optional[SampleRow]:
        """Return the parent with the largest number of children."""

        max_children_parent = ""
        max_children_count = 0
        for parent_uri, children in self.all_children.items():
            if self._is_hierarchy_scaffold_uri(parent_uri):
                continue
            active_children = [
                child
                for child in children
                if child in self.sampleable_class_uris and child not in self.deprecated_uris
            ]
            if len(active_children) > max_children_count:
                max_children_parent = parent_uri
                max_children_count = len(active_children)
        if max_children_parent and max_children_count > 0:
            return SampleRow(
                max_children_parent,
                self._code_for_resource(max_children_parent),
                "max-children",
                str(max_children_count),
            )
        return None

    def _parent_count_rows(self) -> list[SampleRow]:
        """Return one example for each parent count we see."""

        rows: list[SampleRow] = []
        parent_count: dict[int, str] = {}
        for child_uri, parents in self.all_parents.items():
            if child_uri in self.sampleable_class_uris and not self._is_hierarchy_scaffold_uri(
                child_uri
            ):
                parent_count.setdefault(len(parents), child_uri)
        for count in sorted(parent_count):
            if (
                self.config.max_parent_count_sample is not None
                and count > self.config.max_parent_count_sample
            ):
                continue
            child_uri = parent_count[count]
            rows.append(
                SampleRow(child_uri, self._code_for_resource(child_uri), f"parent-count{count}")
            )
        return rows

    def _root_rows(self) -> list[SampleRow]:
        """Return sampleable concepts with no recorded parents."""

        if not self.config.allows_root_samples:
            return []
        rows: list[SampleRow] = []
        excluded = self.deprecated_uris | self.object_property_uris | self.annotation_property_uris
        for uri in self.sampleable_class_uris.keys():
            if (
                uri not in self.all_parents
                and uri not in self.non_root_class_uris
                and uri not in excluded
                and not self._is_hierarchy_scaffold_uri(uri)
            ):
                rows.append(SampleRow(uri, self._code_for_resource(uri), "root"))
        return rows


def write_samples(rows: Iterable[SampleRow], output_path: Path) -> None:
    """Write the UTF-8 TSV file with no header row."""

    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        for row in rows:
            output_file.write(row.to_tsv())
            output_file.write("\n")


def generate_samples(
    owl_path: Path,
    config_path: Path,
    output_path: Optional[Path] = None,
    terminology: Optional[str] = None,
    report_path: Optional[Path] = None,
) -> list[SampleRow]:
    """Generate a sample file and, if requested, a JSON report."""

    config = TerminologyConfig.load(config_path, terminology=terminology)
    output = output_path or Path(f"{config.terminology}-samples.txt")
    collector = SampleCollector(config)
    rows = collector.generate(owl_path)
    write_samples(rows, output)
    if report_path:
        with report_path.open("w", encoding="utf-8") as report_file:
            json.dump(collector.report(rows), report_file, indent=2, sort_keys=True)
            report_file.write("\n")
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate EVSRESTAPI concept sample rows from an OWL/RDF XML terminology."
    )
    parser.add_argument("owl_path", help="Terminology OWL file path")
    parser.add_argument("config_path", help="Terminology metadata JSON path")
    parser.add_argument("--output", help="Output sample TSV path")
    parser.add_argument("--terminology", help="Terminology name used for default output naming")
    parser.add_argument("--report", help="Optional JSON report path")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Command-line entrypoint for the content QA script."""

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    owl_path = Path(args.owl_path)
    config_path = Path(args.config_path)
    if not owl_path.is_file() or owl_path.suffix.lower() != ".owl":
        parser.error("terminology owl file path is invalid")
    if not config_path.is_file() or config_path.suffix.lower() != ".json":
        parser.error("terminology json path is invalid")

    print("--------------------------------------------------")
    print("Starting..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")

    generate_samples(
        owl_path=owl_path,
        config_path=config_path,
        output_path=Path(args.output) if args.output else None,
        terminology=args.terminology,
        report_path=Path(args.report) if args.report else None,
    )

    print("")
    print("--------------------------------------------------")
    print("Ending..." + datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    print("--------------------------------------------------")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
