## ADDED Requirements

### Requirement: Profile directory management
The system SHALL manage browser profile data in a dedicated directory that persists across sessions.

#### Scenario: Default profile path on macOS
- **WHEN** no profile path is explicitly configured
- **THEN** system uses `~/Library/Application Support/google_search/profile`

#### Scenario: Default profile path on Linux
- **WHEN** no profile path is explicitly configured on Linux
- **THEN** system uses `~/.local/share/google_search/profile`

#### Scenario: Profile path override
- **WHEN** user provides `--profile /custom/path` or `GOOGLE_SEARCH_PROFILE` environment variable
- **THEN** system uses the specified path instead of default

### Requirement: First-time login flow
The system SHALL guide users through initial Google login when no profile exists.

#### Scenario: Profile does not exist
- **WHEN** user runs `google-search search` and profile directory does not exist
- **THEN** system exits with error message suggesting to run `google-search login` first

#### Scenario: Login command execution
- **WHEN** user runs `google-search login`
- **THEN** system launches headed Chrome with the profile directory
- **AND** system displays instructions for user to log into Google
- **AND** system waits for user to press Enter before closing

#### Scenario: Post-login profile persistence
- **WHEN** user completes Google login and presses Enter
- **THEN** system closes Chrome and persists all cookies and login state to profile directory
- **AND** subsequent runs will reuse the saved login state

### Requirement: Profile security
The system SHALL protect profile data from unauthorized access.

#### Scenario: Profile directory permissions
- **WHEN** profile directory is created on Unix-like systems
- **THEN** system sets directory permissions to `0700` (read/write/execute for owner only)

### Requirement: Profile status check
The system SHALL provide a command to check profile status.

#### Scenario: Profile status with existing profile
- **WHEN** user runs `google-search profile-status` with an existing profile
- **THEN** system displays profile path and disk space usage

#### Scenario: Profile status with non-existent profile
- **WHEN** user runs `google-search profile-status` and profile does not exist
- **THEN** system displays message that profile does not exist

### Requirement: Profile locking
The system SHALL handle cases where the profile is locked by another Chrome instance.

#### Scenario: Profile locked by another instance
- **WHEN** another Chrome instance is using the same profile
- **THEN** system exits with `FatalError` indicating profile is locked
- **AND** system exits with code 2
