# Operations Java applications

Use Java 25 and the same Spring Boot, Spotless/google-java-format, and SpotBugs
baseline as the paired evsrestapi migration branch. Preserve existing package names,
comments, service patterns, and signatures in moved loader code. Do not copy core
source: consume `evsrestapi-core` through the configured Gradle composite build.

`operations.admin` hosts only the private API and process registry. It must start
without graph/OpenSearch or FHIR beans. `operations.loader` starts a non-web loader
context in a child JVM. Application/resource configuration must stay separated.

Run `./gradlew test` for backend-independent tests, `./gradlew integrationTest`
for configured backend tests, and `./gradlew bootJar loaderJar` for executables.
Backend-mutating verification requires disposable data. Follow the parent bin and
config instructions for shell/config changes and preserve transform stdout contracts.
