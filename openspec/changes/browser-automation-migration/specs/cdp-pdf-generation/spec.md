## ADDED Requirements

### Requirement: PDF generation via CDP
The system SHALL generate PDF files using Chrome DevTools Protocol's `Page.printToPDF` command.

#### Scenario: PDF generation with background
- **WHEN** page is loaded and ready
- **THEN** system calls CDP `Page.printToPDF` with `printBackground: true` to capture background colors and images

#### Scenario: A4 paper size
- **WHEN** PDF is generated
- **THEN** system uses A4 dimensions: 8.27 inches width, 11.69 inches height

#### Scenario: No margins
- **WHEN** PDF is generated
- **THEN** system uses zero margins (top: 0, bottom: 0, left: 0, right: 0)

#### Scenario: PDF saved to output directory
- **WHEN** PDF is successfully generated
- **THEN** system saves it to configured output directory with correct filename

### Requirement: Page ready wait strategy
The system SHALL wait for page to be fully loaded before generating PDF.

#### Scenario: Network idle wait
- **WHEN** page has finished initial navigation
- **THEN** system waits for `networkidle` state (up to 30 seconds)
- **AND** adds additional 2 seconds for JS rendering stabilization

#### Scenario: Fallback wait on timeout
- **WHEN** `networkidle` wait times out
- **THEN** system falls back to `domcontentloaded` state
- **AND** waits additional 3 seconds
