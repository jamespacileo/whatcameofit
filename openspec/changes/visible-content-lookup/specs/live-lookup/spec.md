## ADDED Requirements

### Requirement: Bounded visual reading
The service SHALL accept one inline PNG/JPEG at most 750KB, 1600px maximum side and 1MP. It SHALL validate dimensions and request size before paid calls. It SHALL treat all pixels and text as untrusted report content, never instructions or proof. Identification failure SHALL be worded as insufficient identification, not absence of a treatment claim.

#### Scenario: Image-only claim
- **WHEN** a valid screenshot accompanies a short caption
- **THEN** both reach one model reading call and candidate scoring remains unchanged

### Requirement: Shared on-demand results
The service MAY retain structured automatic findings from independently public reports for 24h and reuse them across clients by a hashed cleaned URL. It SHALL retain no copied report text, screenshots or reader identity. Shared answers SHALL remain unreviewed and dated. Browser-only or selected content SHALL NOT populate shared storage.

#### Scenario: Previously processed public report
- **WHEN** a fresh shared result exists for the requested source
- **THEN** the service returns it with its original checked-at time and no model call

#### Scenario: Public access cannot be verified
- **WHEN** the service cannot independently read a report publicly
- **THEN** visual lookup may proceed but its result remains in the reader's local cache only

### Requirement: Bounded source retrieval
Article retrieval SHALL have a total deadline covering robots checks, response headers and response bodies. Independent public verification of browser-supplied text SHALL have a shorter deadline; if it expires, lookup SHALL continue with the supplied text without sharing that result. Paper and trial-registry requests SHALL have deadlines through body consumption. A registry timeout SHALL be reported as failure, never as evidence that no trial exists.

#### Scenario: A publisher stalls during public verification
- **WHEN** a browser supplies usable text but the anonymous publisher request exceeds three seconds
- **THEN** lookup continues from browser text and does not publish its result to shared storage

#### Scenario: A non-treatment report links to a stalled paper service
- **WHEN** identification finds no specific treatment and a linked-paper or stated-record request is still pending
- **THEN** the identification result returns without waiting for those requests

#### Scenario: Response headers arrive but the body stalls
- **WHEN** a publisher, paper or trial-registry response body fails to complete before its deadline
- **THEN** the request is aborted and follows the same failure behavior as a header timeout

### Requirement: A linked paper not looked up is said
Failed or timed-out linked papers SHALL be counted as not looked up, with no guessed registry numbers. When that count exceeds zero, the site and extension SHALL show an unfolded notice beside the records explaining that a linked paper could not be looked up and a trial it reports may be missing.

#### Scenario: Linked paper not answered in time
- **WHEN** the page links to two papers, the first paper's host does not answer within the deadline, and the second paper's abstract gives a ClinicalTrials.gov number
- **THEN** the second paper's trial is among the candidates, and the answer says one linked paper was not looked up

#### Scenario: Reader is told a linked paper was not looked up
- **WHEN** an answer says one linked paper was not looked up
- **THEN** the reader sees, beside the list, that a linked paper could not be looked up just now and a trial it reports may be missing
- **AND** the answer is not saved for reuse

### Requirement: Incomplete paper results are retried
An answer with a paper not looked up SHALL NOT be kept in the shared results library or the extension's saved results.

#### Scenario: Opening an incompletely checked report again
- **WHEN** the previous answer had a linked paper not looked up
- **THEN** the next lookup asks again instead of reusing that incomplete answer

### Requirement: Stop irrelevant source work
When identification finds no specific treatment, the paper request in flight SHALL be ended and no further paper or stated record SHALL be asked for.

#### Scenario: Identification finishes before a linked-paper request
- **WHEN** identification reports no specific treatment while paper retrieval is pending
- **THEN** the request is cancelled and further source requests are skipped


### Requirement: Overlapped bounded source work
Once a treatment is identified, independent registry-name search and optional enrichment SHALL start without waiting for all linked papers. A single lookup SHALL spend at most five seconds waiting for its linked papers together, with at most three paper requests and starts at least 500 ms apart. Every unanswered paper SHALL be counted; exact cited record priority, matching semantics and unchecked-paper cache exclusions SHALL remain intact.

#### Scenario: The first paper stalls
- **WHEN** the first paper does not answer but a later paper can supply a registry number within the aggregate allowance
- **THEN** that later request can run and its trial is included, and all unanswered papers are reported

### Requirement: Progressive result compatibility
An opt-in streaming lookup SHALL emit a completed core result before optional research enrichment and emit a final complete result afterwards. Ordinary JSON clients SHALL retain their existing complete response. A failure before core completion SHALL be explicit and never an empty successful search.

#### Scenario: Related-paper search is pending
- **WHEN** clinical searching and scoring finish while enrichment remains pending
- **THEN** an opted-in client receives the completed core result without another model invocation

### Requirement: Bounded structured source reuse
Successful DOI/PubMed-to-trial mappings and public registry query results MAY be reused for at most 24h. Cache operations SHALL be bounded, with origin fallback on cache failure. Abstracts, copied report text, images, credentials and reader identifiers SHALL NOT be retained. Errors and timeouts SHALL NOT be cached as empty answers. Independently public completed non-treatment outcomes MAY enter the dated shared-result library; provisional and incomplete outcomes SHALL NOT.

#### Scenario: A paper service fails
- **WHEN** a paper metadata request fails or times out
- **THEN** no successful empty mapping is stored and a later lookup can ask again
