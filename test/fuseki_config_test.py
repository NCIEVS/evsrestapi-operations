from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bin" / "install_fuseki_config.sh"


def run_installer(base, *args):
    return subprocess.run(
        [str(INSTALLER), "--base", str(base), *args],
        capture_output=True,
        text=True,
    )


def make_version(parent, name):
    run = parent / name / "run"
    for dataset in ("NCIT2", "CTRP"):
        (run / "databases" / dataset).mkdir(parents=True)
    return run


def test_install_detects_drift_and_repairs_it(tmp_path):
    base = make_version(tmp_path, "apache-jena-fuseki-5.3.0")
    assert run_installer(base).returncode == 0
    assert run_installer(base, "--check").returncode == 0
    manifest = (base / "configuration" / "evsrestapi-operations-fuseki.txt").read_text()
    assert "apache-jena-fuseki-5.3.0" in manifest
    assert "NCIT2.ttl sha256=" in manifest
    assert "CTRP.ttl sha256=" in manifest
    assert "already current" in run_installer(base).stdout

    ncit = base / "configuration" / "NCIT2.ttl"
    ncit.write_text(ncit.read_text().replace("ja:cxtValue false", "ja:cxtValue true"))
    assert run_installer(base, "--check").returncode != 0
    assert run_installer(base).returncode == 0
    assert run_installer(base, "--check").returncode == 0


def test_new_current_version_requires_install_before_start(tmp_path):
    old = make_version(tmp_path, "apache-jena-fuseki-5.3.0")
    new = make_version(tmp_path, "apache-jena-fuseki-5.4.0")
    current = tmp_path / "current"
    current.symlink_to(old.parent)
    assert run_installer(current / "run").returncode == 0
    current.unlink()
    current.symlink_to(new.parent)
    assert run_installer(current / "run", "--check").returncode != 0
    assert run_installer(current / "run").returncode == 0
    assert run_installer(current / "run", "--check").returncode == 0
    assert "apache-jena-fuseki-5.4.0" in (
        new / "configuration" / "evsrestapi-operations-fuseki.txt"
    ).read_text()


def test_unmanaged_dataset_blocks_install_and_check(tmp_path):
    base = make_version(tmp_path, "apache-jena-fuseki-5.3.0")
    assert run_installer(base).returncode == 0
    (base / "configuration" / "OTHER.ttl").write_text(
        ':service fuseki:name "OTHER" .\n'
    )
    assert "unmanaged active dataset" in run_installer(base).stderr
    assert "unmanaged active dataset" in run_installer(base, "--check").stderr


def test_source_without_service_denial_is_rejected(tmp_path):
    base = make_version(tmp_path, "apache-jena-fuseki-5.3.0")
    source = tmp_path / "source"
    source.mkdir()
    for dataset in ("NCIT2", "CTRP"):
        text = (ROOT / "config" / "fuseki" / f"{dataset}.ttl").read_text()
        (source / f"{dataset}.ttl").write_text(text)
    ncit = source / "NCIT2.ttl"
    ncit.write_text(ncit.read_text().replace("ja:cxtValue false", "ja:cxtValue true"))
    result = run_installer(base, "--source", str(source))
    assert result.returncode != 0
    assert "lacks the dataset SERVICE denial" in result.stderr
