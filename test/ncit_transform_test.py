import os
import subprocess
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "bin" / "transforms" / "ncit.sh"


def write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def test_ncit_transform_runs_master_ctrp_pipeline(tmp_path: Path) -> None:
    work_directory = tmp_path / "work"
    input_directory = work_directory / "input"
    output_directory = work_directory / "output"
    tool_directory = tmp_path / "tools"
    disjoint_directory = tool_directory / "disjoint"
    input_directory.mkdir(parents=True)
    output_directory.mkdir()
    disjoint_directory.mkdir(parents=True)

    input_file = input_directory / "f123.Thesaurus-260908-26.09a.owl"
    input_file.write_text(
        '<term-group rdf:datatype="test">PT</term-group>\n'
        '<term-source rdf:datatype="test">NCI</term-source>\n'
        '<P378 rdf:datatype="http://www.w3.org/2001/XMLSchema#string">NCI</P378>\n'
        '<P385 rdf:datatype="http://www.w3.org/2001/XMLSchema#string"></P385>\n'
        '<rdf:Description rdf:about="term-group">\n'
    )
    inference_jar = tool_directory / "inference.jar"
    scrubber_jar = tool_directory / "scrubber.jar"
    scrubber_properties = tool_directory / "scrubber.properties"
    by_code_script = ROOT / "legacy" / "OWLScrubber" / "scripts" / "Sed_Command_Script_byCode.sh"
    inference_jar.write_text("mock\n")
    scrubber_jar.write_text("mock\n")
    scrubber_properties.write_text("mock\n")
    java_command = tool_directory / "java"
    write_executable(
        java_command,
        """#!/bin/bash
set -e
if [[ $* == *inference.jar* ]]; then
  input=${!#}
  input=${input#file://}
  output=${input/Thesaurus/ThesaurusInf}
  cp "$input" "$output"
elif [[ $* == *scrubber.jar* ]]; then
  while [[ $# -gt 0 ]]; do
    case $1 in
      -N) input=$2; shift 2 ;;
      -O) output=$2; shift 2 ;;
      *) shift ;;
    esac
  done
  input=${input#file://}
  output=${output#file://}
  cp "$input" "$output"
else
  input=${!#}
  output=${input%.owl}_disjoint.owl
  cp "$input" "$output"
  echo disjoint >>"$output"
fi
""",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "JAVA_COMMAND": str(java_command),
            "NCIT_WORK_DIRECTORY": str(work_directory),
            "NCIT_INFERENCE_JAR": str(inference_jar),
            "NCIT_SCRUBBER_DIRECTORY": str(tool_directory),
            "NCIT_SCRUBBER_JAR": str(scrubber_jar),
            "NCIT_SCRUBBER_PROPERTIES": str(scrubber_properties),
            "NCIT_BY_CODE_SCRIPT": str(by_code_script),
            "NCIT_DISJOINT_DIRECTORY": str(disjoint_directory),
        }
    )

    result = subprocess.run(
        [str(TRANSFORM), str(input_file), "123"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    final_owl = output_directory / "ThesaurusInferred_forTS.owl"
    assert result.stdout.splitlines()[-1] == str(final_owl)
    final_content = final_owl.read_text()
    assert '<P383 rdf:datatype="test">PT</P383>' in final_content
    assert '<P384 rdf:datatype="test">NCI</P384>' in final_content
    assert '<P378>NCI</P378>' in final_content
    assert '<rdf:Description rdf:about="P383">' in final_content
    assert '<P385' not in final_content
    assert final_content.endswith("disjoint\n")
    ftp_zip = output_directory / "ThesaurusInferred_forTS.zip"
    assert ftp_zip.is_file()
    with ZipFile(ftp_zip) as archive:
        assert archive.namelist() == ["ThesaurusInferred_forTS.owl"]
    assert not (output_directory / "ThesaurusInferred_forTS.rdf").exists()
    assert not (output_directory / "ThesaurusInf-26.09a.STARDOG.zip").exists()
    assert not (output_directory / "ThesaurusInf_26.09a.CTRP.zip").exists()
    assert not (output_directory / "ThesaurusInferred_forTS.both.zip").exists()
