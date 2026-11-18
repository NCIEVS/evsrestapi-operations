VERSION=2.5.0
BUILD_DIR=./build

build:
	@echo "Creating ${BUILD_DIR} directory if it does not exist"
	@mkdir -p ${BUILD_DIR}
	@echo "Creating zip file. Version: ${VERSION}"
	@zip -r -FS ${BUILD_DIR}/evsrestapi-operations-${VERSION}.zip ./bin ./config ./lib ./src ./poetry.lock ./pyproject.toml ./Makefile -x ".gitignore" "bin/work_*" "bin/work_*/*" "*/__pycache__" "*/__pycache__/*" "*/.pytest_cache" "*/.pytest_cache/*" "config/setenv.sh" "*.log"

clean:
	@echo "Cleaning ${BUILD_DIR} directory if it exists"
	@if [ -d ${BUILD_DIR} ] && [ -z "$(ls -A ${BUILD_DIR})" ]; then rm -f ${BUILD_DIR}/*.zip; fi

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
