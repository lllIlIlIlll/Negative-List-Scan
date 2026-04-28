## ADDED Requirements

### Requirement: Single entity search execution
The system SHALL allow users to execute a negative news search for a single entity by providing the entity name and type (company or person).

#### Scenario: Company search
- **WHEN** user runs `google-search search "三鹿集团" company`
- **THEN** system executes search using company templates and generates PDF evidence files

#### Scenario: Person search
- **WHEN** user runs `google-search search "张三" person`
- **THEN** system executes search using person templates and generates PDF evidence files

#### Scenario: Custom template override
- **WHEN** user provides `--template '"{name}" AND (欺诈 OR 投诉)'`
- **THEN** system uses the custom template instead of default templates for this search

### Requirement: Multi-template sequential execution
The system SHALL execute each template independently, saving a separate PDF for each template, with random delay between queries.

#### Scenario: Two template execution
- **WHEN** user searches with default company templates (2 templates configured)
- **THEN** system executes template 1, waits random 5-15 seconds, then executes template 2
- **AND** system generates 2 separate PDF files

#### Scenario: Random delay between queries
- **WHEN** multiple templates are configured for the entity type
- **THEN** system SHALL wait a random duration between 5 and 15 seconds between each template execution

### Requirement: Evidence file output
The system SHALL generate evidence files in the output directory for each template execution.

#### Scenario: PDF file naming
- **WHEN** template `company_default_1` executes at 2026-04-28 07:30:00 UTC for entity "三鹿集团"
- **THEN** system generates file named `三鹿集团_company_default_1_20260428T073000Z.pdf`

#### Scenario: JSON metadata file
- **WHEN** template execution completes
- **THEN** system generates a corresponding JSON file with forensics metadata

#### Scenario: Optional HTML snapshot
- **WHEN** `save_html: true` in config
- **THEN** system saves the page DOM as `.html` file with SHA-256 in JSON metadata

#### Scenario: Optional screenshot
- **WHEN** `save_screenshot: true` in config
- **THEN** system saves full-page screenshot as `.png` file

### Requirement: CLI exit codes
The system SHALL return appropriate exit codes based on execution results.

#### Scenario: All templates succeeded
- **WHEN** all template executions complete without errors
- **THEN** system exits with code 0

#### Scenario: Partial failure
- **WHEN** some template executions fail but PDFs were still generated
- **THEN** system exits with code 1

#### Scenario: Complete failure
- **WHEN** no PDFs were generated due to fatal errors
- **THEN** system exits with code 2
