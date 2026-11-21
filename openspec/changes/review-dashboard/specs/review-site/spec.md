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
