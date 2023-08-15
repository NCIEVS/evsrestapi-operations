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
