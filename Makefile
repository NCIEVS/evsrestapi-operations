VERSION="1.0.0"
BUILD_DIR="./build"
SCRIPTS_HOME="bin"

build:
	@echo "Creating ${BUILD_DIR} directory if it does not exist"
	@mkdir -p ${BUILD_DIR}
	@echo "Creating zip file. Version: ${VERSION}"
	@zip ${BUILD_DIR}/evsrestapi-operation-${VERSION}.zip ${SCRIPTS_HOME}

clean:
	@echo "Cleaning ${BUILD_DIR} directory if it exists"
	@if [ -d ${BUILD_DIR} ] && [ -z "$(ls -A ${BUILD_DIR})" ]; then rm ${BUILD_DIR}/*.zip; fi

.PHONY: build