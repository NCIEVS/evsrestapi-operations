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
