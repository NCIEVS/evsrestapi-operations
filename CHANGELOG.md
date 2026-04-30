# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [2.4.0.RELEASE] - 2026-04-01
### Added
- Handle compaction tasks through stardog_load.sh and maintenance operations
- Create a script to load all terminologies (EVSRESTAPI-704)
- Add a "qa" feature to stardog_load.sh for MED-RT that verifies the version in the DTS XML file matches the version in the filename (EVSRESTAPI-705)
- Reading databases from Elasticsearch (EVSRESTAPI-574)
- Updated forms template download links to work with different tiers/environments (RDFBROWSER-593)
- SPARQL prefix documentation (EVSRESTAPI-671)
- Term form attachment form improvements (RDFBROWSER-591)

### Changed
- Python error logging improvements (EVSRESTAPI-669)
- Handle --force flag correctly for NCIT monthly (EVSRESTAPI-675)
- Update CDISC and NCIt form configurations
- Fix for GO terminology by following redirects properly
- Fixes for longer names of some terminologies
- JSON handling to properly deal with prefixes and property values (EVSRESTAPI-696)
- Manage version as lowercase, remove extraneous umlssemnet logic (EVSRESTAPI-700)

### Fixed
- Fix for Chebi issues and GO redirects
- Fail stardog_load if disc space is >60% (EVSRESTAPI-695)
- Update CDISC form (EVSRESTAPI-685)
- Use cleanup function instead of direct exit in scripts
- NPO prefix handling

## [2.3.0.RELEASE] - 2025-10-15
### Changed
- Additional capability to perform maintenance operations through stardog_load.sh (and therefore Jenkins)
- Improve handling of "weekly" and "monthly" databases to allow them to be config-driven
- Add a dedicated --help flag to the run_command.sh script

## [prior releases] - TBD
