## ADDED Requirements

### Requirement: Headed browser as default mode
The system SHALL launch Chrome in headed mode (visible window) by default.

#### Scenario: Default launch in headed mode
- **WHEN** user runs `google-search search "三鹿集团" company` without `--headless`
- **THEN** system launches Chrome with visible window

#### Scenario: Explicit headless flag
- **WHEN** user runs `google-search search "三鹿集团" company --headless`
- **THEN** system launches Chrome in headless mode

### Requirement: Browser channel selection
The system SHALL support using the user's system Chrome installation.

#### Scenario: Chrome channel on macOS/Linux
- **WHEN** `browser.channel: chrome` in config
- **THEN** system uses the system-installed Google Chrome via Playwright's Chrome channel

#### Scenario: Chromium fallback
- **WHEN** `browser.channel: chromium` in config
- **THEN** system uses Playwright's bundled Chromium

### Requirement: Viewport configuration
The system SHALL configure browser viewport as specified in config.

#### Scenario: Custom viewport
- **WHEN** `browser.viewport.width: 1280` and `browser.viewport.height: 900` in config
- **THEN** system launches Chrome with 1280x900 viewport
