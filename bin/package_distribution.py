#!/usr/bin/env python3
"""Create a self-contained operations distribution without local state or credentials."""
from pathlib import Path
import json
import os
import subprocess
import sys
import zipfile


def revision(directory):
    return subprocess.check_output(["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()


def main():
    root = Path(__file__).resolve().parents[1]
    source = Path(os.environ.get("EVSRESTAPI_SOURCE", str(root.parent / "evsrestapi"))).resolve()
    output = root / "build"
    output.mkdir(exist_ok=True)
    version = sys.argv[1]
    jars = [root / "web/build/libs" / name for name in ("evsrestapi-operations.jar", "evsrestapi-loader.jar")]
    for jar in jars:
        if not jar.is_file():
            raise SystemExit(f"Missing {jar}; build the Java applications first")
    destination = output / f"evsrestapi-operations-{version}.zip"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in ("bin", "config", "lib", "src", "data", "docs"):
            for path in (root / folder).rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(root)
                if any(part in ("__pycache__", ".pytest_cache", ".git", ".gradle", ".venv", "temp", "var",
                                "audit_reports", "NCIT_HISTORY", "fhir_transforms")
                       or part.startswith("work_") or part.endswith(".egg-info") for part in relative.parts):
                    continue
                # Ship only the setenv templates, never a local copy holding credentials.
                if path.name.startswith("setenv") and not path.name.endswith("_orig"):
                    continue
                if path.name in (".DS_Store", "DownloadSuccessfull.lck") or path.name.startswith("._") or path.suffix in (".log", ".pyc", ".pyo", ".hprof"):
                    continue
                info = zipfile.ZipInfo(relative.as_posix())
                info.create_system = 3  # Unix permissions must survive Windows-built ZIPs.
                info.external_attr = ((0o100755 if folder == "bin" else 0o100644) << 16)
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        for name in ("README.md", "poetry.lock", "pyproject.toml"):
            archive.write(root / name, name)
        for jar in jars:
            archive.write(jar, "lib/" + jar.name)
        archive.writestr("build-info.json", json.dumps({"version": version, "evsrestapi": revision(source), "operations": revision(root),
            "evsrestapiDirty": bool(subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip()),
            "operationsDirty": bool(subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], text=True).strip())}, indent=2))
    print(destination)


if __name__ == "__main__":
    main()
