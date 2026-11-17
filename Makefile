VERSION=2.5.0
BUILD_DIR=./build
NCIT_DISJOINT_SOURCE=src/main/java/gov/nih/nci/evs/OWLDisjointWithProcessor.java
NCIT_DISJOINT_CLASSES=${BUILD_DIR}/package/src/main/resources/ncit/disjoint/classes

build:
	@echo "Creating ${BUILD_DIR} directory if it does not exist"
	@mkdir -p ${NCIT_DISJOINT_CLASSES}
	@echo "Compiling NCIt disjoint processor"
	@javac -d ${NCIT_DISJOINT_CLASSES} ${NCIT_DISJOINT_SOURCE}
	@echo "Creating zip file. Version: ${VERSION}"
	@rm -f ${BUILD_DIR}/evsrestapi-operations-${VERSION}.zip
	@zip -r ${BUILD_DIR}/evsrestapi-operations-${VERSION}.zip ./bin ./config ./lib ./src ./poetry.lock ./pyproject.toml ./Makefile -x ".gitignore"
	@cd ${BUILD_DIR}/package && zip -r ../evsrestapi-operations-${VERSION}.zip ./src/main/resources/ncit/disjoint/classes

clean:
	@echo "Cleaning ${BUILD_DIR} package files"
	@rm -f ${BUILD_DIR}/evsrestapi-operations-${VERSION}.zip

tag:
	git tag -a "v`/bin/date +%Y-%m-%d`-${VERSION}.RELEASE" -m "Release `/bin/date +%Y-%m-%d`"
	git push origin "v`/bin/date +%Y-%m-%d`-${VERSION}.RELEASE"

releasetag:
	git tag -a "${VERSION}-RC-`/bin/date +%Y-%m-%d`" -m "Release ${VERSION}-RC-`/bin/date +%Y-%m-%d`"
	git push origin "${VERSION}-RC-`/bin/date +%Y-%m-%d`"

rmreleasetag:
	git tag -d "${VERSION}-RC-`/bin/date +%Y-%m-%d`"
	git push origin --delete "${VERSION}-RC-`/bin/date +%Y-%m-%d`"

rmtag:
	git tag -d "v`/bin/date +%Y-%m-%d`-${VERSION}.RELEASE"
	git push origin --delete "v`/bin/date +%Y-%m-%d`-${VERSION}.RELEASE"

.PHONY: build
