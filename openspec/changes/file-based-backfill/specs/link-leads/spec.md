# Spec Delta

## MODIFIED Requirements

### Requirement: Loading from a file
The load stage of a run SHALL read one or more bulk files of one platform from the operator's disk and write, to the run's files, a share for each post that links to an address on a listed outlet. It SHALL send no request to any platform or outlet and SHALL write to no database. It SHALL finish by reporting how many posts were read, how many shares were written, how many distinct addresses those are, and how many posts were skipped for each reason, the reason "outlet not listed" among them.

#### Scenario: A file of stories
- **WHEN** the operator loads a file of 10,000 Hacker News stories of which 7,000 link to an address and 800 of those are on listed outlets
- **THEN** 800 shares are written to the run, 6,200 are counted as outlet not listed, the report gives the counts, and no request is sent

#### Scenario: Stopped part way
- **WHEN** a load is stopped and started again on the same files
- **THEN** the run holds every post that links to a listed outlet once

#### Scenario: A platform with no reader
- **WHEN** the operator names a platform the pipeline has no reader for
- **THEN** the command fails, lists the platforms it can read, and writes nothing

#### Scenario: A domain is added to the list
- **WHEN** a domain is added to the outlet list and a new run is started over the same files
- **THEN** the run holds the posts on that domain, and its later stages pay for none of the leads an earlier run pushed

### Requirement: Link lead record
A link lead SHALL be kept once per article address, in a run's files and in the truth store alike. It SHALL carry the address, the outlet's domain, the outlet kind, the title the article was first shared under, and each share of it: the platform, the community, the time shared and the score. A share SHALL be kept once.

#### Scenario: One article shared in two places
- **WHEN** the same article address is shared on Hacker News and in a Reddit community, in two runs that are both pushed
- **THEN** the truth store holds one link lead with two shares

#### Scenario: The same file in two runs
- **WHEN** two runs over the same file are both pushed
- **THEN** the truth store holds no lead and no share twice

## ADDED Requirements

### Requirement: Unlisted domains are tallied, not kept
A load SHALL write a tally in the run giving, for each unlisted domain, the platform, the number of link posts and the number whose title names a topic word. The tally SHALL hold no title, no address beyond the domain, and nothing about who shared. No link on an unlisted outlet SHALL appear in any other file of the run or be pushed.

#### Scenario: A code repository's domain
- **WHEN** a file holds 5,000 posts that link to one unlisted domain
- **THEN** the tally gives that domain 5,000 for the platform, and the run's other files hold none of them

### Requirement: A row that fails is set aside, within a budget
A row that cannot be read into a post SHALL be recorded in the run's quarantine with the bulk file's name, the row's position and the kind of error, and nothing of the row's content. The load SHALL go on. It SHALL stop with an error when such rows exceed `LOAD_ERROR_BUDGET` as a share of the rows read, and SHALL refuse to start while that setting is empty.

#### Scenario: One malformed line
- **WHEN** one line in a file of 10,000 is not valid JSON
- **THEN** the load writes the rest, and the quarantine has one entry with the file name, the line number and the error's kind

#### Scenario: A file in an unexpected shape
- **WHEN** more rows fail than the budget allows
- **THEN** the load stops and says how many failed of how many read

### Requirement: A file is checked before it is loaded
Before writing anything, a load SHALL check that each file has the fields its reader takes. A file without them SHALL be refused with the missing fields named.

#### Scenario: A column is missing
- **WHEN** a Hacker News file has no `url` column
- **THEN** the load writes nothing and names the column

### Requirement: Dry run
A load run with `--dry-run` SHALL read the files and print the report a load would give, and SHALL write nothing but the tally.

#### Scenario: A dry run before a load
- **WHEN** the operator dry-runs a load and then runs it
- **THEN** the dry run's count of shares on listed outlets equals the load's

### Requirement: A run can be narrowed to a period
Scoring and reading SHALL each take an optional first day, set by the operator (`LEAD_TRIAGE_SINCE`, `LEAD_READ_SINCE`). With a first day set, a lead first shared before it SHALL NOT be scored, or read, and SHALL NOT count as due; it SHALL keep its place and be due again once the day is moved back or unset. Screening is not narrowed: it costs nothing per lead.

The operator MAY set an inclusive UTC window for scoring and reading with `LEAD_BACKFILL_WINDOW`. The reader SHALL check the actual publication date before asking the model. A page published outside the window SHALL make no claim or source article. Its reason SHALL be recorded as `outside_publication_window`, so it can be requeued when the window is widened.

#### Scenario: An archived article is indexed during the window
- **WHEN** a lead first shared inside the window gives a page with a publication date older than the window
- **THEN** the reader records the date and window in its outcome and makes no model request

#### Scenario: A daily batch picks up an article published earlier in the backfill
- **WHEN** `LEAD_BATCH_DAY` is set and a lead was first shared that day
- **THEN** screening, triage and reading can take the lead, the reader checks the publisher date against the full backfill window, and leads first shared on other days stay outside the batch

#### Scenario: A backfill of two years
- **WHEN** the first day for scoring and for reading is 1 January 2025 and leads go back to 2014
- **THEN** only leads first shared from that day on are scored and read, and the older ones are neither sent to a model nor asked of an outlet

#### Scenario: The period is widened later
- **WHEN** the first day is unset after such a run
- **THEN** the older leads are due as if the period had never been set

### Requirement: A link read can hand verified research to claim preparation
With a local trial snapshot configured, the link reader SHALL match eligible articles using Luna, the local registry, PubMed and Decisions on the body it already has. It SHALL keep only verified identifiers at the 0.80 exact threshold and preserve publisher citations separately. Claim preparation SHALL apply its existing evidence checks and review rules.

#### Scenario: A paper is matched by its research
- **WHEN** a publisher article names no DOI and the verifier confirms the exact paper in PubMed
- **THEN** the article retains the PMID and any DOI PubMed gives for that paper, separately from the publisher's citations

#### Scenario: The verified paper has a PMID and no DOI
- **WHEN** claim preparation hands the PMID to the literature index
- **THEN** the index must return that exact PMID before its canonical work can enter ordinary claim matching

#### Scenario: The literature index stops a batch
- **WHEN** the configured literature index cannot finish the article's evidence check
- **THEN** the run stops with the article still due, its recorded model spend retained, and no new claim or source article from that read
