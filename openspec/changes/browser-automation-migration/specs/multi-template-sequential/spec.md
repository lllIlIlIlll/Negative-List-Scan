## ADDED Requirements

### Requirement: Separate URL per template
The system SHALL construct a separate Google search URL for each template, not concatenate templates with OR.

#### Scenario: Individual query construction
- **WHEN** entity "三鹿集团" with entity_type "company" has 2 templates configured
- **THEN** system generates 2 separate Google URLs
- **AND** each URL contains only that template's search query

#### Scenario: No query string concatenation
- **WHEN** building queries for execution
- **THEN** system SHALL NOT concatenate multiple templates with OR operator
- **AND** system SHALL NOT create a single query containing all template conditions

### Requirement: Independent PDF per template
The system SHALL generate a separate PDF file for each template execution.

#### Scenario: Multiple PDFs for multiple templates
- **WHEN** entity type has N templates configured
- **THEN** system generates N separate PDF files
- **AND** each PDF contains search results for exactly one template

### Requirement: Query object structure
The system SHALL return a list of Query objects from the template builder.

#### Scenario: Query object fields
- **WHEN** queries are built
- **THEN** each Query object contains: template_id, query_text, google_url

#### Scenario: Custom template single query
- **WHEN** user provides custom template via `--template`
- **THEN** system returns only one Query with template_id "custom"
