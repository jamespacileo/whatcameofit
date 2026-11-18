# extension-test-corpus Specification

## Purpose
Keeps the browser extension's test corpus (its address checks and recorded lookup responses) in a cache outside every worktree, so that removing a worktree loses no paid lookup and worktrees working at once keep each other's results.

## Requirements

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

### Requirement: Separate trial and knowledge-card evidence
Each audited corpus row SHALL record its trial outcome and knowledge-card identity separately, with UTC time, released build and reading method. A positive trial candidate SHALL NOT make an unrelated card correct. Negative controls, ambiguous claims and inaccessible content SHALL retain truthful outcomes. The native Sheet SHALL preserve unrelated values, formulas, validation and formatting.

#### Scenario: Correct trial with the wrong card
- **WHEN** a released lookup finds the intended trial and links a card about another condition
- **THEN** the row records the card failure and does not receive an overall pass

#### Scenario: Caption and video differ in coverage
- **WHEN** verification reads only a caption or a single frame
- **THEN** the evidence states that limitation rather than claiming full-video verification

### Requirement: Corpus verification reuses proven work
The full-corpus audit SHALL check exact published address mappings before paid lookup, reuse current eligible evidence, and record measured fresh/reused timing and request counts where available. Model or source failures SHALL not be retained as successful empty results. Audit artifacts SHALL contain no copied article text or screenshots.

#### Scenario: Published article already mapped
- **WHEN** an address maps exactly to published claims
- **THEN** its card identity can be checked without another reading-model request
