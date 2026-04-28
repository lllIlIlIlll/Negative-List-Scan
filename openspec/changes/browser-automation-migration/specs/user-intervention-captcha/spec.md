## ADDED Requirements

### Requirement: reCAPTCHA detection in headed mode
The system SHALL detect when Google presents a reCAPTCHA or "sorry" page and wait for user manual resolution.

#### Scenario: Sorry page detection
- **WHEN** page URL contains "/sorry/"
- **THEN** system identifies this as a blocked state

#### Scenario: CAPTCHA form detection
- **WHEN** page contains a form element with id "captcha-form"
- **THEN** system identifies this as a blocked state

#### Scenario: Wait for manual resolution
- **WHEN** blocked state is detected in headed mode
- **THEN** system displays warning message to user
- **AND** system polls every 2 seconds for unblock (up to 120 seconds)
- **AND** if user resolves within timeout, execution continues

#### Scenario: Timeout on user inaction
- **WHEN** user does not resolve blocked state within 120 seconds
- **THEN** system marks the template run as failed with error message
- **AND** system continues to next template (if any)

### Requirement: reCAPTCHA handling in headless mode
The system SHALL fail immediately when blocked in headless mode since manual intervention is not possible.

#### Scenario: Headless blocked behavior
- **WHEN** blocked state is detected in headless mode
- **THEN** system immediately marks template run as failed
- **AND** system does not wait for user action
- **AND** system displays error message suggesting to remove --headless flag

### Requirement: Blocked page URL detection
The system SHALL detect blocked state by examining the page URL.

#### Scenario: Sorry page URL check
- **WHEN** page URL contains "/sorry/"
- **THEN** system treats this as a blocked/captcha page
