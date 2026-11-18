VERSION=2.6.0
BUILD_DIR=./build
GRADLEW ?= ./gradlew
PYTHON ?= python3

build: java
	$(PYTHON) bin/package_distribution.py $(VERSION)

java:
	cd web && $(GRADLEW) spotlessCheck build

test:
	cd web && $(GRADLEW) test
	poetry run pytest

# Report HIGH and CRITICAL vulnerabilities in the Java dependencies (needs Trivy), as CI does.
# The generated lockfile is always removed.
scan:
	@set -e; \
	trap 'rm -rf "$(CURDIR)/web/gradle/dependency-locks" "$(CURDIR)/web/gradle.lockfile"' EXIT; \
	cd web && $(GRADLEW) dependencies --write-locks > /dev/null; \
	trivy fs gradle.lockfile --scanners vuln --severity HIGH,CRITICAL --format table

clean:
	cd web && $(GRADLEW) clean
	rm -f $(BUILD_DIR)/evsrestapi-operations-*.zip

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

.PHONY: build java test scan clean
