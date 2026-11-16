import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_bulk_load_streams_child_output_and_reports_failure(tmp_path):
    source = Path(__file__).resolve().parents[1]
    home = tmp_path / "operations with spaces"
    scripts = home / "bin"
    scripts.mkdir(parents=True)
    for name in ("bulk_load.sh", "ops-common.sh", "process_supervisor.py", "process_exec.sh"):
        shutil.copy2(source / "bin" / name, scripts / name)
    child = scripts / "stardog_load.sh"
    child.write_text("#!/bin/bash\necho 'fake child progress'\nexit 7\n", encoding="utf-8", newline="\n")
    child.chmod(0o755)
    env = dict(os.environ, EVS_OPS_HOME=str(home), OPS_PYTHON=sys.executable, OPS_STATE_DIR=str(home / "var"))
    result = subprocess.run([os.environ.get("OPS_BASH", "bash"), str(scripts / "bulk_load.sh"), "--noconfig"], cwd=home, env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "fake child progress" in result.stdout
    assert "ERROR loading" in result.stdout
