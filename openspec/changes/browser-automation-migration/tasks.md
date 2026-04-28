## 1. Delete v1 Deprecated Files

- [x] 1.1 Delete `src/google_search/proxy.py`
- [x] 1.2 Delete `src/google_search/ua_pool.py`
- [x] 1.3 Delete `tests/test_proxy.py`
- [x] 1.4 Delete `tests/test_ua_pool.py`

## 2. Update Data Models

- [x] 2.1 Add `EvidenceMetadata` dataclass (pdf_path, pdf_sha256, pdf_bytes, html_path, html_sha256, screenshot_path)
- [x] 2.2 Add `SearchResult` dataclass (rank, title, url, snippet, source, date)
- [x] 2.3 Add `TemplateRunResult` dataclass (template_id, search_template, search_url, searched_at_utc, searched_at_local, evidence, results, results_parse_status, page_load_ms, had_user_interaction, error)
- [x] 2.4 Add `SearchTaskResult` dataclass with success_count/total_count properties
- [x] 2.5 Add `Query` dataclass (template_id, query_text, google_url)

## 3. Refactor Config Module

- [x] 3.1 Remove module-level `config = Config()` singleton
- [x] 3.2 Add `BrowserConfig` dataclass (channel, headless, viewport_width, viewport_height)
- [x] 3.3 Add `SearchConfig` dataclass (hl, gl, inter_query_delay_seconds, page_load_timeout_seconds, network_idle_timeout_seconds, captcha_wait_seconds)
- [x] 3.4 Add `OutputConfig` dataclass (directory, save_html, save_screenshot)
- [x] 3.5 Add `Config.load()` classmethod that reads YAML and applies environment variable overrides
- [x] 3.6 Fix `inter_query_delay_seconds` list → tuple normalization

## 4. Update Templates Module

- [x] 4.1 Rename `build_search_query()` to `build_queries()`
- [x] 4.2 Change return type from single string to `list[Query]`
- [x] 4.3 Support custom_template parameter (returns single Query with id="custom")
- [x] 4.4 Each Query includes template_id, query_text, google_url
- [x] 4.5 `build_google_url()` helper uses urllib.parse.quote_plus

## 5. Simplify Exceptions

- [x] 5.1 Define `GoogleSearchError` base class
- [x] 5.2 Define `UserActionRequired` for manual intervention needed
- [x] 5.3 Define `RecoverableError` for temporary failures
- [x] 5.4 Define `FatalError` for unrecoverable errors (profile lock, Chrome missing, config error)
- [x] 5.5 Remove v1细分异常 types (CaptchaError, ForbiddenError, ProxyAuthError, etc.)

## 6. Rewrite Browser Module

- [x] 6.1 Create `PersistentBrowser` class with `__init__(profile_path, browser_config)`
- [x] 6.2 Implement `session()` context manager with `launch_persistent_context`
- [x] 6.3 Use `channel=self.config.channel` to launch user's system Chrome
- [x] 6.4 Create profile directory with `mkdir(parents=True, exist_ok=True)`
- [x] 6.5 Set profile directory permissions to `0o700` (Unix)
- [x] 6.6 Handle `ProcessSingleton` / lock file errors → raise `FatalError`
- [x] 6.7 Implement `new_page()` method on context
- [x] 6.8 Clean up playwright and context in finally block

## 7. Rewrite PDF Module

- [x] 7.1 Implement `save_pdf(page, output_path)` using CDP `Page.printToPDF`
- [x] 7.2 Configure printBackground=True, A4 paper, zero margins
- [x] 7.3 Return (path, sha256, bytes) tuple
- [x] 7.4 Implement `save_html_snapshot(page, output_path)` returning (path, sha256)
- [x] 7.5 Implement `save_screenshot(page, output_path)` returning path
- [x] 7.6 Implement `wait_for_page_ready()` with networkidle + fallback strategy
- [x] 7.7 Calculate SHA-256 using hashlib.sha256

## 8. Create Parser Module

- [x] 8.1 Create `parse_search_results(page)` returning (list[SearchResult], status)
- [x] 8.2 Define multiple selector strategies in priority order (div.g, div.MjjYud, etc.)
- [x] 8.3 Implement fallback through selector list
- [x] 8.4 Parse title from h3, URL from a[href], snippet from div[data-sncf]/div.VwiC3b
- [x] 8.5 Return status "success"/"partial"/"failed" based on result count
- [x] 8.6 All exceptions caught silently (best-effort design)

## 9. Rewrite Searcher Module

- [x] 9.1 Accept `Config` via constructor dependency injection
- [x] 9.2 Implement `search(entity, entity_type, custom_template)` → SearchTaskResult
- [x] 9.3 Call `build_queries()` to get list of queries
- [x] 9.4 Loop through queries with `browser.session()` context
- [x] 9.5 Add random delay between templates using `inter_query_delay_seconds`
- [x] 9.6 Implement `_run_one_query()` creating new page per query
- [x] 9.7 Implement `_execute()` with full flow: goto → block check → wait → save PDF → save HTML/screenshot → parse → write JSON
- [x] 9.8 Implement `_is_blocked()` detection (sorry page, captcha form)
- [x] 9.9 Implement `_wait_for_unblock()` polling for headed mode
- [x] 9.10 Handle reCAPTCHA: headless → fail fast, headed → wait 120s
- [x] 9.11 Implement `_error_run()` for error cases
- [x] 9.12 Implement `_sanitize_filename()` for safe filenames
- [x] 9.13 Implement `_write_json()` with complete metadata

## 10. Rewrite CLI Module

- [x] 10.1 Create Click Group with `-c/--config` option
- [x] 10.2 Store config in `ctx.obj["config"]`
- [x] 10.3 Implement `search` command with arguments: entity, entity_type
- [x] 10.4 Add options: --template, --headless/--no-headless, --profile, --output-dir, --no-html, --no-screenshot
- [x] 10.5 CLI option overrides config values
- [x] 10.6 Check profile exists before search, show helpful error if missing
- [x] 10.7 Implement `login` command launching headed Chrome for user login
- [x] 10.8 Implement `profile-status` command showing path and disk usage
- [x] 10.9 Implement `_print_summary()` with color output
- [x] 10.10 Set exit codes: 0 (all success), 1 (partial), 2 (fatal)
- [x] 10.11 Fix v1 bug: do NOT shadow config with local variable

## 11. Update Configuration File

- [x] 11.1 Remove `proxy.*` section from config.yaml
- [x] 11.2 Remove `user_agents` section from config.yaml
- [x] 11.3 Add `profile.path` section with default paths by OS
- [x] 11.4 Add `browser` section (channel, headless, viewport)
- [x] 11.5 Add `search.inter_query_delay_seconds`, `captcha_wait_seconds`
- [x] 11.6 Keep `search.hl`, `search.gl` for language/region
- [x] 11.7 Keep `search_templates` structure
- [x] 11.8 Keep `output.directory`, `save_html`, `save_screenshot`

## 12. Update Project Metadata

- [x] 12.1 Update pyproject.toml version to 0.2.0
- [x] 12.2 Remove playwright from dependencies if only used for chromium
- [x] 12.3 Ensure click, pyyaml, playwright>=1.44.0 are in dependencies
- [x] 12.4 Update entry point if needed

## 13. Verification

- [x] 13.1 Run `pip install -e ".[dev]"` successfully
- [x] 13.2 Run `google-search profile-status` (should show profile not found)
- [ ] 13.3 Run `google-search login` and complete browser login flow
- [ ] 13.4 Run `google-search profile-status` (should show profile exists)
- [ ] 13.5 Run `google-search search "测试公司" company`
- [ ] 13.6 Verify PDF, HTML, PNG, JSON files are created in output/
- [ ] 13.7 Verify JSON contains pdf_sha256, UTC timestamps
- [x] 13.8 Run `ruff check src/` and fix any issues
- [x] 13.9 Run `pytest tests/` and ensure all tests pass
