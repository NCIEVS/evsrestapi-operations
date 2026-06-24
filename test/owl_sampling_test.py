import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


def _load_owl_sampling_script():
    script_path = Path(__file__).resolve().parents[1] / "bin" / "owl_sampling.py"
    spec = importlib.util.spec_from_file_location("owl_sampling", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generate_samples = _load_owl_sampling_script().generate_samples


SAMPLE_FILES_DIR = Path(__file__).parent / "sample_test_files"
SYNTHETIC_OWL = (SAMPLE_FILES_DIR / "synthetic.owl").read_text(encoding="utf-8")
SYNTHETIC_CONFIG = json.loads((SAMPLE_FILES_DIR / "synthetic.json").read_text(encoding="utf-8"))


def test_generate_samples_from_synthetic_owl(tmp_path):
    owl_path = tmp_path / "sample.owl"
    config_path = tmp_path / "synthetic.json"
    output_path = tmp_path / "synthetic-samples.txt"
    report_path = tmp_path / "report.json"
    owl_path.write_text(SYNTHETIC_OWL, encoding="utf-8")
    config_path.write_text(json.dumps(SYNTHETIC_CONFIG), encoding="utf-8")

    rows = generate_samples(owl_path, config_path, output_path=output_path, report_path=report_path)

    expected_samples = (SAMPLE_FILES_DIR / "synthetic_expected.txt").read_text(encoding="utf-8").splitlines()
    assert [row.to_tsv() for row in rows] == expected_samples
    assert output_path.read_text(encoding="utf-8").splitlines() == [row.to_tsv() for row in rows]

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["sampleRows"] == 23
    assert report["classes"] == 10
    assert report["sampleableClasses"] == 9
    assert report["datatypeProperties"] == 2
    assert report["disabledSampleFamilies"] == []


def test_report_lists_disabled_sample_families(tmp_path):
    owl_path = tmp_path / "sample.owl"
    config_path = tmp_path / "synthetic.json"
    output_path = tmp_path / "mged-samples.txt"
    report_path = tmp_path / "mged-report.json"
    owl_path.write_text(SYNTHETIC_OWL, encoding="utf-8")
    config_path.write_text(json.dumps(SYNTHETIC_CONFIG), encoding="utf-8")

    generate_samples(
        owl_path,
        config_path,
        output_path=output_path,
        terminology="mged",
        report_path=report_path,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    disabled = {item["family"]: item for item in report["disabledSampleFamilies"]}
    assert "restrictions" in disabled
    assert "roots" not in disabled
    assert disabled["direct-properties"]["keys"] == "synonym"


def test_generate_samples_accepts_bom_metadata_json(tmp_path):
    owl_path = tmp_path / "sample.owl"
    config_path = tmp_path / "synthetic.json"
    output_path = tmp_path / "synthetic-samples.txt"
    owl_path.write_text(SYNTHETIC_OWL, encoding="utf-8")
    config_path.write_text("\ufeff" + json.dumps(SYNTHETIC_CONFIG), encoding="utf-8")

    generate_samples(owl_path, config_path, output_path=output_path)

    assert output_path.exists()


def test_generate_samples_skips_owl_builtin_classes_with_uri_code_fallback(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "fallback.owl"
    config_path = SAMPLE_FILES_DIR / "fallback.json"
    output_path = tmp_path / "fallback-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    assert [row.to_tsv() for row in rows] == [
        "http://example.org/fallback#Root\tRoot\trdfs:label\tFallback Root",
        "http://example.org/fallback#Root\tRoot\troot",
    ]


def test_generate_samples_canonicalizes_builtin_namespace_prefixes(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "prefix.owl"
    config_path = SAMPLE_FILES_DIR / "prefix.json"
    output_path = tmp_path / "synthetic-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    assert [row.to_tsv() for row in rows] == [
        "http://example.org/prefix#Deprecated\tC1\towl:deprecated\ttrue",
    ]


def test_generate_samples_indexes_object_property_rdf_type_records(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "roles.owl"
    config_path = SAMPLE_FILES_DIR / "roles.json"
    output_path = tmp_path / "synthetic-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    keys = [row.key for row in rows]
    assert "rdfs:subClassOf/owl:Restriction~MO_278" in keys
    assert not any("has_owner" in key for key in keys)


def test_generate_samples_shortens_obo_hash_role_uris_to_api_role_name(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "obo_hash.owl"
    config_path = SAMPLE_FILES_DIR / "obo_hash.json"
    output_path = tmp_path / "synthetic-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    keys = [row.key for row in rows]
    assert "rdfs:subClassOf/owl:Restriction~lacks_part" in keys
    assert not any("cl#lacks_part" in key for key in keys)


def test_equivalent_class_uses_only_top_level_named_parent(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "equivalent.owl"
    config_path = SAMPLE_FILES_DIR / "equivalent.json"
    output_path = tmp_path / "synthetic-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)
    row_text = [row.to_tsv() for row in rows]

    assert "http://example.org/equivalent#Child\tCHILD\tparent-style2\tPARENT" in row_text
    assert "http://example.org/equivalent#Child\tPARENT\tchild-style2\tCHILD" in row_text
    assert "http://example.org/equivalent#Parent\tPARENT\tmax-children\t1" in row_text
    assert "http://example.org/equivalent#Child\tCHILD\tparent-count2" in row_text
    assert not any("\tparent-style2\tNESTED" in row for row in row_text)
    assert not any("\tparent-count3" in row for row in row_text)


def test_subclass_intersection_uses_top_level_named_parent(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "subclass_expression.owl"
    config_path = SAMPLE_FILES_DIR / "subclass_expression.json"
    output_path = tmp_path / "synthetic-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)
    row_text = [row.to_tsv() for row in rows]

    assert "http://example.org/subclass-expression#Child\tCHILD\tparent-style1\tPARENT" in row_text
    assert "http://example.org/subclass-expression#Child\tPARENT\tchild-style1\tCHILD" in row_text
    assert "http://example.org/subclass-expression#Parent\tPARENT\tmax-children\t1" in row_text
    assert "http://example.org/subclass-expression#Child\tCHILD\tparent-count2" in row_text
    assert not any("\tparent-style1\tNESTED" in row for row in row_text)
    assert not any("\tparent-count3" in row for row in row_text)


def test_hierarchy_role_restrictions_count_as_hierarchy_not_roles(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "hierarchy_role.owl"
    config_path = SAMPLE_FILES_DIR / "hierarchy_role.json"
    output_path = tmp_path / "synthetic-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    assert [row.to_tsv() for row in rows] == [
        "http://example.org/hierarchy-role#Parent\tPARENT\tmax-children\t2",
        "http://example.org/hierarchy-role#ChildOne\tCHILD1\tparent-count1",
        "http://example.org/hierarchy-role#Parent\tPARENT\troot",
    ]


def test_scaffold_parents_suppress_roots_without_becoming_samples(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "mged.owl"
    config_path = SAMPLE_FILES_DIR / "mged.json"
    output_path = tmp_path / "mged-samples.txt"

    rows = generate_samples(
        owl_path,
        config_path,
        output_path=output_path,
        terminology="mged",
    )

    assert [row.to_tsv() for row in rows] == [
        "http://example.org/mged#BioMaterialPackage\tMO_182\trdfs:label\tBioMaterialPackage",
    ]


def test_generate_samples_skips_blank_configured_code_values(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "blank_code.owl"
    config_path = SAMPLE_FILES_DIR / "blank_code.json"
    output_path = tmp_path / "synthetic-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    assert rows == []


def test_generate_samples_allows_configured_hierarchy_fallback_terminologies(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "hgnc.owl"
    config_path = SAMPLE_FILES_DIR / "hgnc.json"
    output_path = tmp_path / "hgnc-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path, terminology="hgnc")

    assert [row.to_tsv() for row in rows] == [
        "http://example.org/hgnc#gene_with_protein_product\tgene_with_protein_product\trdfs:label\tgene with protein product",
        "http://example.org/hgnc#HGNC_1\tHGNC:1\tparent-style1\tgene_with_protein_product",
        "http://example.org/hgnc#HGNC_1\tgene_with_protein_product\tchild-style1\tHGNC:1",
        "http://example.org/hgnc#gene_with_protein_product\tgene_with_protein_product\tmax-children\t1",
        "http://example.org/hgnc#HGNC_1\tHGNC:1\tparent-count1",
        "http://example.org/hgnc#gene_with_protein_product\tgene_with_protein_product\troot",
    ]


def test_resource_qualifier_values_match_loader_label_shape(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "chebi_like.owl"
    config_path = SAMPLE_FILES_DIR / "chebi_like.json"
    output_path = tmp_path / "chebi-like-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    assert (
        "http://example.org/chebi-like#CHEBI_1\tCHEBI:1\tqualifier-oboInOwl:hasRelatedSynonym~oboInOwl:hasSynonymType~BRAND_NAME\tExample brand~BRAND_NAME"
        in [row.to_tsv() for row in rows]
    )


def test_text_values_keep_repeated_spaces_but_skip_fragile_definition_source_qualifier(
    tmp_path,
):
    owl_path = SAMPLE_FILES_DIR / "ncit_like_1.owl"
    config_path = SAMPLE_FILES_DIR / "ncit_like_1.json"
    output_path = tmp_path / "ncit-like-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    row_text = [row.to_tsv() for row in rows]
    assert (
        "http://example.org/ncit-like#C1\tC1\tP325\tSentence one.  Sentence two keeps one row."
        in row_text
    )
    assert not any("\tqualifier-P325~P378" in row for row in row_text)


def test_definition_source_qualifier_without_repeated_spaces_is_sampled(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "ncit_like_2.owl"
    config_path = SAMPLE_FILES_DIR / "ncit_like_2.json"
    output_path = tmp_path / "ncit-like-samples.txt"

    rows = generate_samples(owl_path, config_path, output_path=output_path)

    row_text = [row.to_tsv() for row in rows]
    assert (
        "http://example.org/ncit-like#C1\tC1\tqualifier-P325~P378~TEST\tSentence one keeps one row.~TEST"
        in row_text
    )


def test_equivalent_class_hierarchy_is_skipped_for_known_logical_definition_owls(tmp_path):
    owl_path = SAMPLE_FILES_DIR / "parent_count_limit.owl"
    config_path = SAMPLE_FILES_DIR / "parent_count_limit.json"
    output_path = tmp_path / "synthetic-samples.txt"

    ordinary_rows = generate_samples(
        owl_path, config_path, output_path=output_path, terminology="synthetic"
    )
    assert any(row.key == "parent-count5" for row in ordinary_rows)

    npo_rows = generate_samples(owl_path, config_path, output_path=output_path, terminology="npo")
    npo_row_text = [row.to_tsv() for row in npo_rows]

    assert (
        "http://example.org/equivalent-hierarchy-policy#LogicalA\tLOGICAL_A\tmax-children\t3"
        in npo_row_text
    )
    assert any(row.key == "parent-count2" for row in npo_rows)
    assert not any(row.key == "parent-count5" for row in npo_rows)


@pytest.mark.parametrize(
    "name,owl_rel_path,config_name,required_keys",
    [
        (
            "go",
            "GO/GO.20250601.owl",
            "go.json",
            {"rdfs:label", "root", "parent-count1"},
        ),
        (
            "canmed",
            "CanMed/CANMED.202506.owl",
            "canmed.json",
            {"Preferred_Name", "root", "parent-count1"},
        ),
        (
            "mged",
            "MGED/MGED.20070209.owl",
            "mged.json",
            {"class_source", "parent-count1"},
        ),
        (
            "ctcae6",
            "CTCAE/ctcae6.owl",
            "ctcae6.json",
            {"ncit:P108", "parent-count1"},
        ),
        (
            "ncit",
            "NCIT/ThesaurusInferred_monthly.owl",
            "ncit.json",
            {"P108", "P310", "root", "parent-count1"},
        ),
    ],
)
def test_real_owl_smoke_samples(tmp_path, name, owl_rel_path, config_name, required_keys):
    if os.environ.get("EVS_RUN_LOCAL_OWL_SMOKE") != "1":
        pytest.skip("set EVS_RUN_LOCAL_OWL_SMOKE=1 to run local UnitTestData smoke tests")
        
    unit_test_data_dir = os.environ.get("UNIT_TEST_DATA_DIR")
    if not unit_test_data_dir:
        pytest.skip("set UNIT_TEST_DATA_DIR to the path containing external test data to run local smoke tests")
        
    owl_path = Path(unit_test_data_dir) / owl_rel_path
    config_path = Path(__file__).resolve().parents[1] / "config" / "metadata" / config_name

    if not owl_path.exists() or not config_path.exists():
        pytest.skip(f"local smoke fixture for {name} is not available")

    output_path = tmp_path / f"{name}-samples.txt"
    rows = generate_samples(
        owl_path,
        config_path,
        output_path=output_path,
        terminology=name,
    )
    keys = {row.key for row in rows}

    assert output_path.exists()
    assert len(rows) > 0
    assert not any("\t" in row.value for row in rows if row.value is not None)
    assert required_keys.issubset(keys)
