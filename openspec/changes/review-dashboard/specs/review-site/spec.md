## ADDED Requirements

### Requirement: Only a signed-in operator reads the review site

The review site SHALL answer a request only when it carries a Cloudflare Access token that verifies against the team's key set, names the team domain as issuer and the application's AUD tag as audience, carries an expiry that has not passed, and carries an email on the operator allowlist. Pages, files and the API SHALL be guarded alike. Every other request SHALL get 403. When any Access setting is missing the site SHALL answer 503 to every request.

#### Scenario: No token
- **WHEN** a request reaches the review Worker without `Cf-Access-Jwt-Assertion`
- **THEN** it gets 403, whatever its path

#### Scenario: Token for another application or reader
- **WHEN** the token's audience, issuer, key or expiry does not match, or its email is not on the allowlist
- **THEN** the request gets 403

#### Scenario: Operator signed in
- **WHEN** an allowlisted operator's valid token arrives
- **THEN** pages and the API answer, marked `Cache-Control: private, no-store` and `X-Robots-Tag: noindex, nofollow`

### Requirement: The review site never writes to a pair store

The review site SHALL send a pair store only statements from its listed set, each a single SELECT, and SHALL answer 405 to any API method but GET.

#### Scenario: A statement that is not listed
- **WHEN** code asks to read with any other SQL text
- **THEN** the read is refused before the store is asked

### Requirement: The staging overview shows what staging reads

The overview SHALL name the bundle staging's D1 store marks current and, apart from it, the bundle and revision the staging site says it was published with (`/bundle-version.txt`, `/build-revision.txt`), since a bundle can be loaded before it is published. It SHALL also show when the current bundle was loaded, the rows it holds by table, the versions still loaded, and the rows of each pair table. A store without the pair tables SHALL be shown as holding none, not as an error.

#### Scenario: Staging holds a bundle
- **WHEN** the operator opens the overview
- **THEN** it shows the current version and the loader's counts for it

### Requirement: Every model has a coverage entry in every environment

The model inventory SHALL list every table the store's migrations leave and every page model of the lab's bundle export, each under a readable name, and for each environment SHALL show it as present (with its records), absent (with the migration or bundle that would hold it), or not readable yet. A table the store holds that the catalogue does not list SHALL be shown. The details view SHALL show the exact table or page model, the record key, where the model is defined, and for page records the bundle version, its load time and the manifest's provenance. Columns that hold article text, raw payloads or bytes SHALL never be sent to the browser.

#### Scenario: A store of the pair tables alone
- **WHEN** staging's store has only migration 0011
- **THEN** each legacy and operational table is shown absent, naming its migration (for example `trial_paper`, 0006)

#### Scenario: A migration adds a table
- **WHEN** a migration makes a table the catalogue does not list
- **THEN** the catalogue test fails until it is listed
