## ADDED Requirements

### Requirement: Corpus cache survives worktree cleanup

The corpus tools SHALL store URL checks and full lookup responses outside the worktree, in a user-data directory configurable through `CORPUS_CACHE_DIR`.

#### Scenario: Rebuild after cleanup

- **GIVEN** a corpus URL has a cached check and lookup response
- **WHEN** the worktree is deleted and a fresh checkout runs the ordinary sync
- **THEN** the worksheet reuses the cached data without new paid lookups

### Requirement: Preserve cache identity and updates

The corpus tools SHALL associate responses with the page URL and reading mode, import existing legacy cache files without replacing newer durable entries, and merge concurrent updates atomically.

#### Scenario: A row ID is reused

- **GIVEN** one URL has a cached response under a legacy row ID
- **WHEN** another worktree assigns that ID to a different URL
- **THEN** the response remains associated only with the original URL

#### Scenario: Concurrent updates

- **WHEN** separate processes save responses for different URLs
- **THEN** both responses survive in the durable cache
