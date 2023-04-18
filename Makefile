VERSION=1.0.0
BUILD_DIR=./build

build:
	@echo "Creating ${BUILD_DIR} directory if it does not exist"
	@mkdir -p ${BUILD_DIR}
	@echo "Creating zip file. Version: ${VERSION}"
	@zip -r ${BUILD_DIR}/evsrestapi-operations-${VERSION}.zip ./bin ./config ./lib -x ".gitignore"

clean:
	@echo "Cleaning ${BUILD_DIR} directory if it exists"
	@if [ -d ${BUILD_DIR} ] && [ -z "$(ls -A ${BUILD_DIR})" ]; then rm -f ${BUILD_DIR}/*.zip; fi

tag:
	git tag -a "v`/bin/date +%Y-%m-%d`-${VERSION}.RELEASE" -m "Release `/bin/date +%Y-%m-%d`"
	git push origin "v`/bin/date +%Y-%m-%d`-${VERSION}.RELEASE"

rmtag:
	git tag -d "v`/bin/date +%Y-%m-%d`-${VERSION}.RELEASE"
	git push origin --delete "v`/bin/date +%Y-%m-%d`-${VERSION}.RELEASE"

.PHONY: build
