## ADDED Requirements

### Requirement: PDF SHA-256 calculation
The system SHALL calculate SHA-256 hash of generated PDF files for tamper evidence.

#### Scenario: SHA-256 computed on save
- **WHEN** PDF file is written to disk
- **THEN** system immediately calculates SHA-256 hash of the file
- **AND** stores the hash in the corresponding JSON metadata file

### Requirement: UTC timestamp in filenames
The system SHALL use UTC ISO 8601 compact format timestamps in all output filenames.

#### Scenario: Filename timestamp format
- **WHEN** generating evidence files for entity "三鹿集团" with template "company_default_1" at 2026-04-28 07:30:00 UTC
- **THEN** filename uses format `三鹿集团_company_default_1_20260428T073000Z.pdf`
- **AND** timestamp is always in UTC, never local time

### Requirement: JSON metadata structure
The system SHALL generate a JSON metadata file for each template execution.

#### Scenario: Metadata file completeness
- **WHEN** template execution completes (success or failure)
- **THEN** system generates JSON with fields: entity, entity_type, template_id, search_template, search_url, searched_at_utc, searched_at_local, browser info, evidence paths and hashes, results, results_parse_status, page_load_ms, had_user_interaction, error

#### Scenario: UTC as authoritative time
- **WHEN** timestamps are recorded
- **THEN** `searched_at_utc` uses `datetime.now(timezone.utc)` as authoritative time
- **AND** `searched_at_local` is provided for display only

### Requirement: Results parse status
The system SHALL record the success level of DOM parsing in metadata.

#### Scenario: Successful parse
- **WHEN** DOM parsing extracts 3 or more results
- **THEN** JSON contains `results_parse_status: "success"`

#### Scenario: Partial parse
- **WHEN** DOM parsing extracts fewer than 3 results
- **THEN** JSON contains `results_parse_status: "partial"`

#### Scenario: Parse failure
- **WHEN** DOM parsing fails completely
- **THEN** JSON contains `results_parse_status: "failed"`

#### Scenario: PDF delivery independent of parse
- **WHEN** DOM parsing fails
- **THEN** PDF file is still generated and saved normally
- **AND** metadata reflects parse failure in `results_parse_status` field only

### Requirement: User interaction tracking
The system SHALL track whether manual user intervention occurred during execution.

#### Scenario: User interaction flag
- **WHEN** user manually completes a reCAPTCHA or login during execution
- **THEN** JSON contains `had_user_interaction: true`

#### Scenario: No user interaction
- **WHEN** execution completes without any manual intervention
- **THEN** JSON contains `had_user_interaction: false`
