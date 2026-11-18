"""Backend-free regressions for spaced paths and script failure propagation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest


REPO = Path(__file__).resolve().parents[1]
OWL = '''<rdf:RDF xmlns="http://example.test/demo.owl#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#">
<owl:Ontology rdf:about="http://example.test/demo.owl"><owl:versionInfo>202610</owl:versionInfo></owl:Ontology>
</rdf:RDF>'''


def installation(tmp_path):
    root = tmp_path / "operations with spaces"
    (root / "bin/transforms").mkdir(parents=True)
    for name in ("ops-common.sh", "process_supervisor.py", "process_exec.sh", "stardog_load.sh", "cdisc_form_update.sh"):
        shutil.copyfile(REPO / "bin" / name, root / "bin" / name)
    env = dict(os.environ, EVS_OPS_HOME=str(root), OPS_STATE_DIR=str(tmp_path / "state"),
               APP_HOME=str(tmp_path / "no config"), OPS_PYTHON=sys.executable,
               OPS_BASH=os.environ.get("OPS_BASH", "bash"), PYTHONUTF8="1")
    env.pop("EVS_OPS_LOCK_TOKEN", None)
    return root, env


def run(root, env, script, args):
    return subprocess.run([env["OPS_BASH"], str(root / "bin" / script), *map(str, args)],
                          env=env, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30)


@pytest.mark.parametrize("archive", [False, True])
def test_loader_stages_spaced_paths_without_backend_writes(tmp_path, archive):
    if not shutil.which("jq"):
        pytest.skip("jq is required by the loader")
    root, env = installation(tmp_path)
    tools = root / "tools"
    tools.mkdir()
    curl = tools / "curl"
    response = {"hits": {"hits": [{"_source": {"name": "CTRP", "weekly": True}},
                                  {"_source": {"name": "NCIT2", "weekly": False}}]}}
    curl.write_text("#!/bin/bash\nprintf '%s\\n' '" + json.dumps(response) + "'\n", encoding="utf-8", newline="\n")
    curl.chmod(0o755)
    startup = root / "startup.sh"
    startup.write_text('export PATH="$EVS_OPS_HOME/tools:$PATH"\n', encoding="utf-8", newline="\n")
    env.update(BASH_ENV=str(startup), GRAPH_DB_TYPE="stardog", GRAPH_DB_HOME=str(root / "no graph tools"),
               GRAPH_DB_USERNAME="test", GRAPH_DB_PASSWORD="test", ES_SCHEME="http", ES_HOST="not-used.invalid", ES_PORT="1",
               LOCAL_MOUNT_DIR="does-not-match-any-mount")
    source = root / ("input with spaces.zip" if archive else "input with spaces.owl")
    if archive:
        with zipfile.ZipFile(source, "w") as zipped:
            zipped.writestr("demo ontology.owl", OWL)
            zipped.writestr("extra ontology.owl", OWL)
    else:
        source.write_text(OWL, encoding="utf-8")
    result = run(root, env, "stardog_load.sh", ["--noconfig", "--transform-only", source])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Transform complete, exiting" in result.stdout
    files = list((root / "bin").glob("work_*/input/*.owl"))
    assert len(files) == (2 if archive else 1)
    assert all(p.read_text(encoding="utf-8") == OWL for p in files)


def test_cdisc_update_works_from_api_directory_and_reports_failure(tmp_path):
    if not shutil.which("jq"):
        pytest.skip("jq is required by CDISC form update")
    root, env = installation(tmp_path)
    config = root / "config/metadata/cdisc-form.json"
    config.parent.mkdir(parents=True)
    shutil.copyfile(REPO / "config/metadata/cdisc-form.json", config)
    source = root / "codes with spaces.txt"
    source.write_text("TEST-CODE1; TEST-CODE2\n", encoding="utf-8")
    result = run(root, env, "cdisc_form_update.sh", [source])
    assert result.returncode == 0, result.stderr
    doc = json.loads(config.read_text(encoding="utf-8"))
    fields = {f["name"]: f.get("options") for section in doc["sections"] for f in section["fields"]}
    assert fields["subset"] == ["TEST"]
    assert fields["codelist"] == ["TEST-CODE1", "TEST-CODE2"]
    assert not list((root / "bin/temp").glob("cdisc.*"))
    original = config.read_bytes()
    result = run(root, env, "cdisc_form_update.sh", [root / "missing.txt"])
    assert result.returncode != 0
    assert config.read_bytes() == original


@pytest.mark.parametrize("terminology", ["hgnc", "canmed", "medrt", "umlssemnet"])
def test_transform_stops_when_environment_creation_fails(tmp_path, terminology):
    root, env = installation(tmp_path)
    shutil.copyfile(REPO / f"bin/transforms/{terminology}.sh", root / f"bin/transforms/{terminology}.sh")
    work = root / "bin/work_12345"
    (work / "input").mkdir(parents=True)
    (work / "output").mkdir()
    # A real venv creation fails because its target is a file, without any package downloads.
    (work / "venv").write_text("blocked", encoding="utf-8")
    result = run(root, env, f"transforms/{terminology}.sh", [work / "input/source.txt", "12345"])
    assert result.returncode != 0
    assert "generating " not in result.stdout
    assert not list(root.glob("*.owl"))
