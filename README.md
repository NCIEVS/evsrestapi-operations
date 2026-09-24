# EVSRESTAPI Operations

Information on the operations processes for the EVSRESTAPI project

### Prerequisites

* Curl, jq, git
* Clone the project - [https://github.com/NCIEVS/evsrestapi-operations](https://github.com/NCIEVS/evsrestapi-operations)

### Steps for Deploying Locally

* Choose a workspace directory, e.g. c:/workspace
* cd c:/workspace
* git clone https://github.com/NCIEVS/evsrestapi-operations
* cd evsrestapi-operations
* cp setenv.sh_orig setenv.sh
* Edit setenv.sh for local environment (and optionally for dev/qa environments)

### Steps for Deploying on Servers

* cd /local/content
* git clone https://github.com/NCIEVS/evsrestapi-operations
* cd evsrestapi-operations
* cp setenv.sh_orig setenv.sh
* Edit setenv.sh for local environment

### Building scripts

* Use ```make clean build``` to create a zip of all the scripts in the bin directory
* This command would create a build directory if it does not exist and creates the zip file in that directory

### Running tests

The project uses Poetry to manage the Python test environment. From the repository root:

```
poetry install
PYTHONPATH=.:src poetry run pytest
```

To run a specific test file:

```
PYTHONPATH=.:src poetry run pytest test/stardog_qa_test.py
```

### Generating OWL samples for EVSRESTAPI content QA

`bin/owl_sampling.py` generates TSV sample files from terminology OWL release
files.  The EVSRESTAPI test project uses these files to check that a loaded
terminology can be read back through the REST API.

The script does not export every concept.  It picks useful examples.  Each row
is a small test case that says, "after this terminology is loaded, EVSRESTAPI
should be able to return this thing."

The generated rows test examples of:

* concept properties, such as preferred names, labels, definitions, synonyms,
  subset links, maps, and status values
* deprecated concept flags and NCIt concept status values
* role/restriction targets that should load as concept relationships
* qualifier metadata on synonyms, definitions, maps, and other properties
* hierarchy behavior, such as parents, children, roots, parent counts, and the
  parent with the most children, when those rows are stable for that terminology

For hierarchy rows, the sampler tries to match what EVSRESTAPI can answer after
loading the terminology.  It keeps explicit imported-parent references so those
classes do not become false roots, but it only writes exact child-count samples
for parents that are sampleable concepts in the OWL file.

Basic usage:

```
python bin/owl_sampling.py <terminology owl file path> <terminology json path>
```

The output contract is a no-header UTF-8 TSV file:

```
uri<TAB>code<TAB>key[<TAB>value]
```

Use `--output` to choose the generated file path, `--terminology` when the
terminology name should not come from the metadata JSON filename, and
`--report` to write a JSON summary of sampled counts.  The report also names
any sample families intentionally skipped for that terminology, such as
restriction rows or a hierarchy style that does not map cleanly to the
EVSRESTAPI Java sample checks.

For step-by-step details, see `docs/owl_sampling_tutorial.md`.

### Versioning
* The version of the scripts are maintained in the ```Makefile```

### Loading UMLS Semantic Network
The UMLS Semantic Network is loaded using a python script. This script requires Python 3.7+. The script can be invoked as follows

```python src/converter/umls_sem_net.py -d "/Users/squareroot/Documents/wci/loading-terminologies/UmlsSemNet/SRDEF" -r "/Users/squareroot/Documents/wci/loading-terminologies/UmlsSemNet/SRSTRE1" -o "/Users/squareroot/temp"```

Input for the script:

-d UMLS Sematic Net definition file<br/>
-r UMLS Sematic Net relationship file<br/>
-o Directory where the output files will be generated

### Managing config info and mapping data

The evsrestapi indexing process relies on configuration files and data files
in this repository.  To support the ability for dev/qa to have in access
to development features, we require a branching strategy to support development
and testing as well as production deployment.  This can be managed with the
following environment var setting.  Use this "develop" url in local/dev/qa
contexts.

```
export CONFIG_BASE_URI=https://raw.githubusercontent.com/NCIEVS/evsrestapi-operations/develop/config/metadata
```

### Updating monthly mappings

New mapping versions arrive roughly monthly (for example a new NCIt-to-HGNC
extract).  The `update-monthly-mappings` agent skill automates ingesting a raw
drop file, normalizing it into the canonical `data/mappings` file, updating the
mapset metadata and HTML, and publishing the change to the `develop`, `stage`,
and `main` tier branches.

The skill is available to both Claude Code (`.claude/skills/update-monthly-mappings`)
and Codex (`.codex/skills/update-monthly-mappings`); the two directories hold
identical copies of the same skill.

**Example — publishing a new NCIt-to-HGNC monthly map**

1. The new mapping is delivered by email (typically as an attachment named
   something like `Aug2026NCItHGNCmap.txt`).  Download the attachment and place
   it, unchanged, into the mappings folder:

   ```
   cp ~/Downloads/Aug2026NCItHGNCmap.txt \
      /local/content/evsrestapi-operations/data/mappings/
   ```

   The incoming file has no header row and uses Windows (`\r\n`) line endings —
   leave it as-is; the skill normalizes it.

2. Make sure your checkout is on `develop` and up to date, then invoke the skill:

   * In Claude Code: `/update-monthly-mappings` (or ask "update the monthly
     mappings").
   * In Codex: `/skills` and choose `update-monthly-mappings`.

3. The skill walks the process and pauses to ask you to confirm the things it
   cannot determine on its own. It can roll back changes when requested.  Upon completion, relevant changes will have been made to all files across 
   `develop`, `stage`, and `main` branches.
